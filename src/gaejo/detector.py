"""개조식 종결 판별기 (Kiwi 기반).

음슴체 '-ㅁ'은 어간 품사·문장부호에 따라 Kiwi가 EF/ETN 양쪽으로 태깅한다.

  개선함   -> 개선/NNG 하/XSV ᆷ/EF      (EF)
  강건함   -> 강건/XR  하/XSA ᆷ/ETN     (ETN)
  수집함.  -> 수집/NNG 하/XSV ᆷ/ETN .   (ETN, 마침표 있을 때)
  검증하기 -> 하/XSV 기/ETN             (ETN)

따라서 품사 태그(ETN/EF)만으로 분기하면 음슴체를 놓친다. 본 모듈은 **태그 + 어미 형태(form)**를
함께 보고 종결 양식을 분류한다. 검출/평가의 단일 진실 공급원.

입력은 NFC로 정규화한다 — macOS 클립보드/파일시스템에서 흔한 NFD(분해형) 한글은
정규화 없이는 [가-힣] 매칭과 Kiwi 형태소 분석이 모두 무너진다.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

# 음슴체(명사형 -ㅁ/-음) 종결로 인정하는 어미 형태. Kiwi는 받침 ㅁ을 'ᆷ'(U+11B7)으로 출력.
_NOMINAL_M = {"ᆷ", "ㅁ", "음", "ᄆ"}
_NOMINAL_GI = {"기"}
# 순수 명사/체언성 종결로 인정하는 품사(체언·접미사·외국어·숫자·한자·URL류)
_NOUN_TAGS = {"NNG", "NNP", "NNB", "NR", "NP", "XSN", "SL", "SH", "SN", "XR",
              "W_URL", "W_EMAIL", "W_SERIAL"}
# 조사(이걸로 끝나면 미완성/비개조식)
_JOSA_TAGS = {"JKS", "JKC", "JKG", "JKO", "JKB", "JKV", "JKQ", "JX", "JC"}
# 무시할 후행 부호·이모지류
_TRAILING = {"SF", "SP", "SS", "SE", "SO", "SW", "SSO", "SSC",
             "W_EMOJI", "W_HASHTAG", "W_MENTION"}

ENDING_TYPES = ("명사", "ㅁ음", "기", "완전문장", "영문", "기타")
_HANGUL = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣ]")
# zero-width space/joiner, word-joiner, BOM 등 포맷 문자(Kiwi가 NNG로 오태깅하기도 함)
_FORMAT_CHARS = re.compile(r"[​‌‍⁠﻿]")


@lru_cache(maxsize=1)
def _kiwi():
    try:
        from kiwipiepy import Kiwi
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "kiwipiepy가 필요합니다. `pip install kiwipiepy` "
            "(소스 설치 시 `pip install -e '.[kiwi]'`)."
        ) from exc
    return Kiwi()


@dataclass
class EndingResult:
    ending: str          # ENDING_TYPES 중 하나
    is_gaejo: bool       # 명사/ㅁ음/기 = True
    final_form: str      # 마지막 유의 형태소 form
    final_tag: str       # 그 태그
    n_words: int         # 공백 기준 어절 수
    has_korean: bool = True   # 한글 포함 여부(영문 전용 헤더 구분용)


def _strip_trailing(tokens):
    """후행 문장부호 토큰 제거."""
    i = len(tokens) - 1
    while i >= 0 and tokens[i].tag in _TRAILING:
        i -= 1
    return tokens[: i + 1]


def _preprocess(line: str) -> str:
    """NFC 정규화 + 포맷 문자 제거 + 공백 정리."""
    return _FORMAT_CHARS.sub("", unicodedata.normalize("NFC", line)).strip()


def classify_ending(line: str) -> EndingResult:
    """한 줄(불릿/구)의 종결 양식을 분류한다."""
    text = _preprocess(line)
    n_words = len([w for w in re.split(r"\s+", text) if w])
    has_ko = bool(_HANGUL.search(text))

    # 0) 한글 없는 줄(영어 섹션 헤더/용어 나열/기호 전용 줄) → 개조식 변환 대상 아님
    if not has_ko:
        toks = _strip_trailing(_kiwi().tokenize(text)) if text else []
        last = toks[-1] if toks else None
        return EndingResult("영문", False,
                            last.form if last else "", last.tag if last else "",
                            n_words, has_ko)

    toks = _strip_trailing(_kiwi().tokenize(text))
    if not toks:
        return EndingResult("기타", False, "", "", n_words, has_ko)

    last = toks[-1]
    tag, form = last.tag, last.form

    # 1) 명사형 전성어미(ETN): 형태로 -ㅁ/-음 vs -기 구분
    if tag == "ETN":
        if form in _NOMINAL_GI:
            return EndingResult("기", True, form, tag, n_words, has_ko)
        return EndingResult("ㅁ음", True, form, tag, n_words, has_ko)

    # 2) 종결어미(EF): 음슴체가 EF로 태깅되는 경우를 형태로 구제
    if tag == "EF":
        if form in _NOMINAL_M:
            return EndingResult("ㅁ음", True, form, tag, n_words, has_ko)
        if form in _NOMINAL_GI:
            return EndingResult("기", True, form, tag, n_words, has_ko)
        return EndingResult("완전문장", False, form, tag, n_words, has_ko)

    # 3) 조사로 끝남 → 미완성/비개조식
    if tag in _JOSA_TAGS:
        return EndingResult("기타", False, form, tag, n_words, has_ko)

    # 4) 체언/외국어/숫자/한자로 끝남 → 순수 명사 종결
    if tag in _NOUN_TAGS:
        return EndingResult("명사", True, form, tag, n_words, has_ko)

    # 5) 그 외(용언 어간 노출, EP 등) → 기타
    return EndingResult("기타", False, form, tag, n_words, has_ko)


def is_gaejo(line: str) -> bool:
    """줄이 개조식 종결(명사/ㅁ음/기)이면 True."""
    return classify_ending(line).is_gaejo
