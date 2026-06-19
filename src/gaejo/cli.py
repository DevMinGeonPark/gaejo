"""GAEJO 커맨드라인 인터페이스.

    gaejo detect    "성능 개선함"          # 종결 양식 판별(여러 줄이면 줄별 배열)
    gaejo score     "...여러 줄..."          # 개조식 준수도 메트릭(객관)
    gaejo transform "...구어체..."           # 개조식 변환(ANTHROPIC_API_KEY 필요)
    gaejo prompt    "...구어체..."           # 변환 프롬프트만 출력(키 불필요)

표준입력(`-`)도 지원: `echo "..." | gaejo transform -`
"""
from __future__ import annotations

import argparse
import json
import sys


def _read(arg: str) -> str:
    if arg == "-":
        return sys.stdin.read().strip()
    return arg


def _cmd_detect(args) -> int:
    from .detector import classify_ending

    text = _read(args.text)
    try:
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if len(lines) > 1:
            results = [classify_ending(ln).__dict__ | {"text": ln.strip()} for ln in lines]
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(classify_ending(text).__dict__, ensure_ascii=False, indent=2))
    except RuntimeError as exc:  # kiwipiepy 미설치
        print(f"[판별 불가] {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_score(args) -> int:
    from .score import score_text

    try:
        rep = score_text(_read(args.text), max_words=args.max_words)
    except RuntimeError as exc:  # kiwipiepy 미설치
        print(f"[채점 불가] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(rep.as_dict(), ensure_ascii=False, indent=2))
    return 0


def _cmd_prompt(args) -> int:
    from .transform import messages_for

    msg = messages_for(_read(args.text), unit=args.unit)
    if args.json:
        print(json.dumps(msg, ensure_ascii=False, indent=2))
    else:
        print("=== SYSTEM ===\n" + msg["system"] + "\n\n=== USER ===\n" + msg["user"])
    return 0


def _cmd_transform(args) -> int:
    from .transform import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, transform

    try:
        from anthropic import APIError  # type: ignore[import-not-found]
    except ImportError:
        APIError = ()  # anthropic 미설치 시 RuntimeError 경로로 처리됨

    try:
        print(transform(
            _read(args.text),
            unit=args.unit,
            model=args.model or DEFAULT_MODEL,
            max_tokens=args.max_tokens or DEFAULT_MAX_TOKENS,
        ))
    except RuntimeError as exc:
        print(f"[변환 불가] {exc}\n프롬프트만 보려면 `gaejo prompt`를 사용하세요.", file=sys.stderr)
        return 1
    except APIError as exc:
        print(f"[API 오류] {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_review(args) -> int:
    """HIL 검토 루프: 후보를 사람이 승인/수정/기각하고 gold(JSONL)로 적재."""
    from .evaluator import objective
    from .hil import append_gold, gold_stats, judge_agreement, load_gold, make_record

    cases = [json.loads(ln) for ln in open(args.cases, encoding="utf-8") if ln.strip()]
    n = 0
    for c in cases:
        original, unit = c["original"], c.get("unit", "bullet")
        candidate = c.get("candidate")
        if candidate is None:
            from .transform import DEFAULT_MODEL, transform
            try:
                candidate = transform(original, unit=unit, model=args.model or DEFAULT_MODEL)
            except RuntimeError as exc:
                print(f"[후보 생성 불가] {exc}\n  cases에 'candidate'를 넣거나 키를 설정하세요.",
                      file=sys.stderr)
                return 1

        obj = None
        try:
            obj = objective(original, candidate)
        except RuntimeError:
            pass  # kiwipiepy 미설치 시 메트릭 생략

        print("\n" + "─" * 60)
        print(f"[{c.get('id', n)}] ({unit})")
        print(f"  원문: {original}")
        print(f"  후보: {candidate}")
        if obj:
            r = obj.get("retention") or {}
            print(f"  객관: 개조식={obj['korean_gaejo_ratio']} 완문={obj['full_sentence_count']}"
                  f" 의미보존={r.get('content_retention')}")
        try:
            choice = input("  [a]ccept [e]dit [r]eject [s]kip [q]uit > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()  # 입력 종료(Ctrl-D)/중단(Ctrl-C) → quit으로 처리
            break
        if choice in ("q", "quit"):
            break
        if choice in ("s", "skip", ""):
            continue
        edited = None
        if choice in ("e", "edit"):
            decision = "edit"
            print("  수정본 입력(빈 줄로 종료):")
            lines = []
            while True:
                try:
                    ln = input()
                except EOFError:
                    break
                if ln == "":
                    break
                lines.append(ln)
            edited = "\n".join(lines)
        elif choice in ("r", "reject"):
            decision = "reject"
        else:
            decision = "accept"
        rec = make_record(original, unit, candidate, decision, edited=edited,
                          objective=obj, judge=c.get("judge"), reviewer=args.reviewer)
        append_gold(args.out, rec)
        n += 1

    print(f"\n검토 {n}건 → {args.out}")
    if n:
        recs = load_gold(args.out)
        print("gold 분포:", gold_stats(recs)["decisions"])
        agr = judge_agreement(recs)
        if agr.get("n"):
            print(f"judge 교정(n={agr['n']}): pearson={agr['pearson_r']} "
                  f"accept정확도={agr['accept_accuracy']} κ={agr['cohen_kappa']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gaejo", description="한국식 연구 발표 개조식 어휘 다듬기")
    p.add_argument("--version", action="store_true", help="버전 출력")
    sub = p.add_subparsers(dest="cmd")

    d = sub.add_parser("detect", help="종결 양식 판별")
    d.add_argument("text", help="문장(또는 -로 표준입력). 여러 줄이면 줄별 결과 배열")
    d.set_defaults(func=_cmd_detect)

    s = sub.add_parser("score", help="개조식 준수도 메트릭")
    s.add_argument("text", help="텍스트(또는 -로 표준입력)")
    s.add_argument("--max-words", dest="max_words", type=int, default=12)
    s.set_defaults(func=_cmd_score)

    pr = sub.add_parser("prompt", help="변환 프롬프트 출력(키 불필요)")
    pr.add_argument("text", help="구어체 텍스트(또는 -)")
    pr.add_argument("--unit", choices=["title", "bullet", "slide"], default="bullet")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=_cmd_prompt)

    t = sub.add_parser("transform", help="개조식 변환(ANTHROPIC_API_KEY 필요)")
    t.add_argument("text", help="구어체 텍스트(또는 -)")
    t.add_argument("--unit", choices=["title", "bullet", "slide"], default="bullet")
    t.add_argument("--model", default=None, help="모델 ID(기본: transform.DEFAULT_MODEL)")
    t.add_argument("--max-tokens", dest="max_tokens", type=int, default=None,
                   help="출력 토큰 상한(기본: transform.DEFAULT_MAX_TOKENS)")
    t.set_defaults(func=_cmd_transform)

    rv = sub.add_parser("review", help="HIL 검토: 후보를 승인/수정/기각해 gold로 적재")
    rv.add_argument("--cases", required=True,
                    help="JSONL: 줄마다 {original, unit?, candidate?, judge?}")
    rv.add_argument("--out", default="gold.jsonl", help="gold 적재 경로(append)")
    rv.add_argument("--model", default=None, help="후보 생성 모델(candidate 없을 때)")
    rv.add_argument("--reviewer", default=None, help="검토자 식별자(선택)")
    rv.set_defaults(func=_cmd_review)
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        from . import __version__

        print(f"gaejo {__version__}")
        return 0
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
