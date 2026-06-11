"""개조식 준수도 메트릭 (객관 축).

평가 3축(스타일·의미보존·자연스러움) 중 **스타일(개조식 변환 정확도)**의 객관 측정.
의미보존·자연스러움은 LLM 판정(evaluator.py)이 담당하며, 본 모듈은 BLEU/ROUGE에
의존하지 않고 형태소 규칙으로 빠르게 계산 가능한 게이트 메트릭을 제공한다.

길이 기준점(한국 연구 발표 코퍼스 분석): 한 줄 공백 어절 중앙값 ≈ 7, 상한 ≈ 25토큰.
영어권 도구의 "불릿당 10단어" 기준은 한·영 혼용 특성상 단순 적용이 어렵다(docs/methodology.md).
경고 임계 기본값 max_words=12는 중앙값 7의 상회를 허용하되 상한 25토큰 이전에
압축을 유도하는 절충값이다.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field

from .detector import ENDING_TYPES, classify_ending

# 글머리표/번호 머리 기호.
# - 순수 글머리 글리프(•▶ 등)는 공백 없이도 마커로 인정
# - 수학/인용 기호와 겸용인 -, –, —, > 는 뒤 공백이 있을 때만 마커("-10%", ">50%" 보호)
# - 번호 마커(1. / 1) / (1) / ①, 가. / ㄱ.)는 소수·연도와의 충돌을 막기 위해
#   ① 숫자 1~3자리 한정 ② 뒤에 숫자가 오면 마커로 보지 않음(1.5배, 3.2절)
#   ③ 한글 열거는 관례 음절(가나다라…하)만, 뒤 공백 필수("끝) 요약" 같은 본문 보호)
#   한계: "(95) 신뢰구간"처럼 참조번호가 열거 형식과 동일하면 구분 불가(마커로 제거됨)
_BULLET = re.compile(
    r"^\s*(?:"
    r"[•▪◦*·‣▸▶■□○●※✓]\s*"
    r"|[-–—>]\s+"
    r"|\(\d{1,3}\)\s*"
    r"|\d{1,3}[.)](?!\d)\s*"
    r"|[①-⑳]\s*"
    r"|[가나다라마바사아자차카타파하ㄱ-ㅎ][.)]\s+"
    r")"
)


@dataclass
class LineScore:
    text: str
    ending: str
    is_gaejo: bool
    n_words: int


@dataclass
class ComplianceReport:
    n_lines: int
    gaejo_ending_ratio: float          # 개조식(명사/ㅁ음/기) 종결 비율 [0,1] (전체 줄 기준)
    korean_gaejo_ratio: float | None  # 한글 줄만 분모로 한 비율. 한글 줄이 없으면 None
    avg_words_per_line: float
    over_limit_ratio: float            # max_words 초과 줄 비율
    full_sentence_count: int           # 완전문장 종결(안티패턴) 줄 수
    ending_dist: dict                  # 종결 양식 분포
    lines: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def _split_lines(text: str) -> list:
    out = []
    for ln in re.split(r"[\n\r]+", text):
        s = _BULLET.sub("", ln).strip()
        if s:
            out.append(s)
    return out


def score_text(text: str, max_words: int = 12) -> ComplianceReport:
    """슬라이드/블록 텍스트의 개조식 준수도를 계산한다."""
    lines = _split_lines(text)
    scored = [
        LineScore(ln, r.ending, r.is_gaejo, r.n_words)
        for ln in lines
        for r in (classify_ending(ln),)
    ]

    n = len(scored)
    if n == 0:
        return ComplianceReport(
            0, 0.0, None, 0.0, 0.0, 0, {e: 0 for e in ENDING_TYPES},
            warnings=["평가할 줄 없음 — 개조식 평가 대상 아님"],
        )

    gaejo_ratio = sum(s.is_gaejo for s in scored) / n
    ko_lines = [s for s in scored if s.ending != "영문"]
    ko_ratio = round(sum(s.is_gaejo for s in ko_lines) / len(ko_lines), 3) if ko_lines else None
    avg_words = sum(s.n_words for s in scored) / n
    n_long = sum(s.n_words > max_words for s in scored)
    full_sent = sum(s.ending == "완전문장" for s in scored)
    dist = Counter(s.ending for s in scored)
    ending_dist = {e: dist.get(e, 0) for e in ENDING_TYPES}

    warns = []
    if full_sent:
        warns.append(f"완전문장 종결 {full_sent}줄 — 개조식으로 변환 필요")
    if n_long:
        warns.append(f"{n_long}줄이 {max_words}어절 초과 — 압축 검토")
    n_other = sum(s.ending == "기타" for s in scored)
    if n_other:
        warns.append(f"종결 불명확 {n_other}줄(조사 종결/용언 노출 등)")
    n_gi = ending_dist.get("기", 0)
    if n_gi:
        warns.append(f"'-기' 종결 {n_gi}줄 — 코퍼스 미사용 양식(명사/-ㅁ음 권장)")
    if ko_ratio is None:
        warns.append("한글 줄 없음 — 개조식 평가 대상 아님")

    return ComplianceReport(
        n_lines=n,
        gaejo_ending_ratio=round(gaejo_ratio, 3),
        korean_gaejo_ratio=ko_ratio,
        avg_words_per_line=round(avg_words, 2),
        over_limit_ratio=round(n_long / n, 3),
        full_sentence_count=full_sent,
        ending_dist=ending_dist,
        lines=[asdict(s) for s in scored],
        warnings=warns,
    )
