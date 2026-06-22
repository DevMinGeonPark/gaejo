"""의미 보존 객관 메트릭 — 수치·전문용어·헤지어 보존 검사.

TST 평가 3축 중 **의미 보존**을 LLM 없이 형태소 규칙으로 정량화한다. 평가에서 측정된
주된 손실(수치 누락, 영어 전문용어 손실, 근사·강조 뉘앙스 탈락)을 직접 잡는다.
LLM 판정(evaluator.llm_judge)을 대체하지 않고, 값싼 객관 게이트로 보완한다.

검사 대상(원문 → 출력 보존 여부):
  - 수치: 아라비아 숫자(SN) + 한국어 수사(NR, '두'→2 등). 값이 출력에 남았는가.
  - 전문용어: 라틴 문자 토큰(SL, 2자 이상; 'LoRA','baseline' 등). 강제 번역 금지 규칙의 검증.
  - 헤지어: 근사/역접/강조/가능성 4범주. 범주 단위로 보존 판정('정도'→'약'은 둘 다 근사 → 보존).
"""
from __future__ import annotations

from collections import Counter

from .detector import _kiwi, _preprocess

# 한국어 수사 → 아라비아(형태소 NR/MM로 분리되므로 부분문자열 오탐 없음).
# '한'·'하나'는 제외 — 관형사 '한 번/한 가지/하나의'(= a/one)가 슬라이드에서 압도적으로 많아
# 숫자 1로 오인식하면 오탐이 잦다('단일/일괄'로 의미 보존되는데도 수치 누락으로 잡힘).
# 실데이터(현대차 강의덱) 검증에서 9건 오탐 → 제거.
_KO_NUM = {
    "두": "2", "둘": "2", "세": "3", "셋": "3",
    "네": "4", "넷": "4", "다섯": "5", "여섯": "6", "일곱": "7",
    "여덟": "8", "아홉": "9", "열": "10",
}

# 헤지어 범주(형태소 form 정확 매칭 — '약'(MAG)과 '요약'(NNG)을 구분)
_HEDGE = {
    "근사": {"약", "정도", "가량", "거의", "대략", "안팎", "남짓", "대체로", "쯤"},
    "역접": {"그러나", "하지만", "반면", "다만", "오히려", "그렇지만", "반대로"},
    "강조": {"반드시", "꼭", "굉장히", "매우", "아주", "특히", "상당히", "훨씬", "크게"},
    "가능성": {"가능", "추정", "예상", "가능성", "잠재"},
}

# 의미 보존 가중치(수치가 가장 치명적)
_WEIGHTS = {"numbers": 0.5, "terms": 0.3, "hedges": 0.2}


def _analyze(text: str):
    """텍스트에서 (수치 Counter, 라틴용어 Counter, 헤지범주 set)를 추출."""
    toks = _kiwi().tokenize(_preprocess(text))
    numbers: Counter = Counter()
    terms: Counter = Counter()
    forms = set()
    for t in toks:
        forms.add(t.form)
        if t.tag == "SN":
            numbers[t.form] += 1
        elif t.tag in ("NR", "MM") and t.form in _KO_NUM:
            # '두 배','세 가지'의 '두/세'는 Kiwi가 관형사(MM)로 태깅 — 수사 집합일 때만 매핑
            numbers[_KO_NUM[t.form]] += 1
        elif t.tag == "SL" and len(t.form) >= 2:
            terms[t.form.lower()] += 1
    hedges = {cat for cat, words in _HEDGE.items() if forms & words}
    return numbers, terms, hedges


def _coverage(orig: Counter, out: Counter):
    """원문 멀티셋이 출력에 얼마나 남았는가. (비율|None, 누락 리스트)."""
    total = sum(orig.values())
    if total == 0:
        return None, []
    retained = sum(min(c, out.get(k, 0)) for k, c in orig.items())
    missing = [k for k, c in orig.items() if out.get(k, 0) < c]
    return round(retained / total, 3), missing


def content_retention(original: str, output: str) -> dict:
    """원문 대비 출력의 의미 보존도를 객관 측정한다.

    각 하위 비율은 원문에 해당 요소가 없으면 None. ``content_retention``은 존재하는
    하위 축들의 가중 평균이며, 검사할 것이 전혀 없으면 None.
    """
    o_num, o_term, o_hed = _analyze(original)
    t_num, t_term, t_hed = _analyze(output)

    num_r, num_miss = _coverage(o_num, t_num)
    term_r, term_miss = _coverage(o_term, t_term)
    hed_r = round(len(o_hed & t_hed) / len(o_hed), 3) if o_hed else None
    hed_miss = sorted(o_hed - t_hed)

    comps = [(_WEIGHTS["numbers"], num_r), (_WEIGHTS["terms"], term_r),
             (_WEIGHTS["hedges"], hed_r)]
    present = [(w, r) for w, r in comps if r is not None]
    overall = (round(sum(w * r for w, r in present) / sum(w for w, _ in present), 3)
               if present else None)

    return {
        "content_retention": overall,
        "numbers": {"ratio": num_r, "missing": num_miss},
        "terms": {"ratio": term_r, "missing": term_miss},
        "hedges": {"ratio": hed_r, "missing_categories": hed_miss},
    }
