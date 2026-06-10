"""개조식 준수도 메트릭 (객관 축).

평가 3축(스타일·의미보존·자연스러움) 중 **스타일(개조식 변환 정확도)**의 객관 측정.
의미보존·자연스러움은 LLM 판정(evaluator.py)이 담당하며, 본 모듈은 BLEU/ROUGE에
의존하지 않고 형태소 규칙으로 빠르게 계산 가능한 게이트 메트릭을 제공한다.

길이 기준점(한국 연구 발표 코퍼스 분석): 한 줄 공백 어절 중앙값 ≈ 7, 상한 ≈ 25토큰.
영어권 도구의 "불릿당 10단어" 기준은 한·영 혼용 특성상 단순 적용이 어렵다(docs/methodology.md).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field

from .detector import ENDING_TYPES, classify_ending

# 글머리표/번호 머리 기호
_BULLET = re.compile(r"^\s*(?:[-•▪◦*·]|\d+[.)]|[①-⑳]|[ㄱ-ㅎ][.)])\s*")


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
    korean_gaejo_ratio: float          # 한글 줄만 분모로 한 개조식 종결 비율
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
        return ComplianceReport(0, 0.0, 0.0, 0.0, 0.0, 0, {e: 0 for e in ENDING_TYPES})

    gaejo_ratio = sum(s.is_gaejo for s in scored) / n
    ko_lines = [s for s in scored if s.ending != "영문"]
    ko_n = len(ko_lines) or 1
    ko_ratio = sum(s.is_gaejo for s in ko_lines) / ko_n
    avg_words = sum(s.n_words for s in scored) / n
    over = sum(s.n_words > max_words for s in scored) / n
    full_sent = sum(s.ending == "완전문장" for s in scored)
    dist = Counter(s.ending for s in scored)
    ending_dist = {e: dist.get(e, 0) for e in ENDING_TYPES}

    warns = []
    if full_sent:
        warns.append(f"완전문장 종결 {full_sent}줄 — 개조식으로 변환 필요")
    n_long = sum(s.n_words > max_words for s in scored)
    if n_long:
        warns.append(f"{n_long}줄이 {max_words}어절 초과 — 압축 검토")
    n_other = sum(s.ending == "기타" for s in scored)
    if n_other:
        warns.append(f"종결 불명확 {n_other}줄(조사 종결/용언 노출 등)")

    return ComplianceReport(
        n_lines=n,
        gaejo_ending_ratio=round(gaejo_ratio, 3),
        korean_gaejo_ratio=round(ko_ratio, 3),
        avg_words_per_line=round(avg_words, 2),
        over_limit_ratio=round(over, 3),
        full_sentence_count=full_sent,
        ending_dist=ending_dist,
        lines=[asdict(s) for s in scored],
        warnings=warns,
    )
