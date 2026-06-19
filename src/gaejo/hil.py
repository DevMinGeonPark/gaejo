"""Human-in-the-loop(HIL) — 변환 후보를 사람이 승인/수정하고 gold로 적재.

캐스케이드 평가의 마지막 단계: 객관 게이트·LLM 판정을 통과 못 한(또는 검수가 필요한)
변환 후보를 사람이 검토한다. 사람의 결정·수정본은 **gold 데이터**(JSONL)로 쌓이고, 이는
(1) production 품질 보증 (2) LLM 판정자를 검증할 정답(judge 교정) 두 목적에 쓰인다.

gold 레코드(한 줄 = 한 후보 검토):
  original   : 원문(구어체)
  unit       : title|bullet|slide
  candidate  : 기계 변환 후보
  decision   : accept | edit | reject
  final      : 사람 최종본(accept→candidate, edit→수정본, reject→None)
  objective  : 검토 시점의 객관 메트릭(candidate 기준)
  judge      : (선택) LLM 3축 판정(candidate 기준)
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass

DECISIONS = ("accept", "edit", "reject")
# 사람 결정 → 품질 라벨(judge 교정용): 수락=좋음, 수정=근접, 기각=나쁨
_DECISION_QUALITY = {"accept": 1.0, "edit": 0.5, "reject": 0.0}


@dataclass
class GoldRecord:
    original: str
    unit: str
    candidate: str
    decision: str
    final: str | None
    objective: dict | None = None
    judge: dict | None = None
    reviewer: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def make_record(original: str, unit: str, candidate: str, decision: str,
                edited: str | None = None, objective: dict | None = None,
                judge: dict | None = None, reviewer: str | None = None) -> GoldRecord:
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}, got {decision!r}")
    if decision == "accept":
        final = candidate
    elif decision == "edit":
        if not edited:
            raise ValueError("decision='edit'에는 edited(수정본)가 필요합니다")
        final = edited
    else:  # reject
        final = None
    return GoldRecord(original, unit, candidate, decision, final,
                      objective=objective, judge=judge, reviewer=reviewer)


def append_gold(path: str, record: GoldRecord) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record.as_dict(), ensure_ascii=False) + "\n")


def load_gold(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def gold_stats(records: list) -> dict:
    """gold 분포 요약."""
    dist = Counter(r["decision"] for r in records)
    return {"n": len(records), "decisions": {d: dist.get(d, 0) for d in DECISIONS}}


def _judge_score(judge: dict) -> float | None:
    """판정 dict에서 평균 점수(3축 평균). 없으면 None."""
    axes = ("style_accuracy", "content_preservation", "naturalness")
    vals = [judge[a] for a in axes if isinstance(judge.get(a), (int, float))]
    return sum(vals) / len(vals) if vals else None


def _pearson(xs: list, ys: list) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return round(sxy / (sxx * syy) ** 0.5, 3)


def _cohen_kappa(a: list, b: list) -> float | None:
    """이진 라벨 a,b(0/1)의 Cohen's κ."""
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa1, pb1 = sum(a) / n, sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if pe == 1:
        return None
    return round((po - pe) / (1 - pe), 3)


def judge_agreement(records: list, threshold: float = 0.85) -> dict:
    """LLM 판정 점수가 사람 결정과 얼마나 일치하는가(judge 교정).

    judge 점수가 있는 레코드만 대상으로:
      - pearson: judge 평균점수 ↔ 사람 품질라벨(accept 1/edit .5/reject 0) 상관
      - accuracy/kappa: judge가 threshold 이상이면 '수락 예측' vs 사람 실제 accept의 일치
    """
    rows = [(r, _judge_score(r.get("judge") or {})) for r in records]
    rows = [(r, s) for r, s in rows if s is not None]
    if not rows:
        return {"n": 0, "note": "judge 점수가 있는 레코드 없음 — --judge로 수집 필요"}

    judge_scores = [s for _, s in rows]
    human_quality = [_DECISION_QUALITY[r["decision"]] for r, _ in rows]
    judge_pred = [1 if s >= threshold else 0 for s in judge_scores]
    human_accept = [1 if r["decision"] == "accept" else 0 for r, _ in rows]

    acc = round(sum(p == h for p, h in zip(judge_pred, human_accept)) / len(rows), 3)
    return {
        "n": len(rows),
        "threshold": threshold,
        "pearson_r": _pearson(judge_scores, human_quality),
        "accept_accuracy": acc,
        "cohen_kappa": _cohen_kappa(judge_pred, human_accept),
        "human_accept_rate": round(sum(human_accept) / len(rows), 3),
    }
