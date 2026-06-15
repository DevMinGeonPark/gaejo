"""홀드아웃 평가 — 변환 품질을 객관 메트릭 + (선택) LLM 3축 판정으로 측정.

    python examples/evaluate.py            # 객관 메트릭만(키 불필요지만 변환엔 키 필요)
    ANTHROPIC_API_KEY=sk-... python examples/evaluate.py        # 변환 + 객관
    ANTHROPIC_API_KEY=sk-... python examples/evaluate.py --judge # + LLM 3축 판정

eval_cases.json은 합성 데이터다(특정 발표 전사본 아님, few-shot과도 미중복).
docs/evaluation.md에 방법론과 기준 결과가 정리돼 있다.
"""
import argparse
import json
import os
import statistics
from pathlib import Path

from gaejo.evaluator import llm_judge, objective
from gaejo.transform import transform

CASES = json.loads((Path(__file__).parent / "eval_cases.json").read_text("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", action="store_true", help="LLM 3축 판정 추가(비용 발생)")
    args = ap.parse_args()

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("ANTHROPIC_API_KEY(또는 ANTHROPIC_AUTH_TOKEN)가 필요합니다(변환 호출).")
        return 1

    ratios, judges = [], []
    for c in CASES:
        out = transform(c["original"], unit=c["unit"])
        obj = objective(c["original"], out)
        gr = obj["korean_gaejo_ratio"]
        ratios.append(gr if gr is not None else 1.0)
        line = f"[{c['id']}] 개조식={gr}  완문={obj['full_sentence_count']}  | {out[:50]}"
        if args.judge:
            v = llm_judge(c["original"], out)
            judges.append(v)
            line += (f"  | 스타일={v['style_accuracy']} 의미={v['content_preservation']}"
                     f" 자연={v['naturalness']}")
        print(line)

    print(f"\n개조식 종결 비율 평균: {statistics.mean(ratios):.2f}")
    if judges:
        for k in ("style_accuracy", "content_preservation", "naturalness"):
            print(f"  {k}: {statistics.mean(j[k] for j in judges):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
