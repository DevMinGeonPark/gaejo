"""GAEJO 커맨드라인 인터페이스.

    gaejo detect    "성능 개선함"          # 종결 양식 판별
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

    r = classify_ending(_read(args.text))
    print(json.dumps(r.__dict__, ensure_ascii=False, indent=2))
    return 0


def _cmd_score(args) -> int:
    from .score import score_text

    rep = score_text(_read(args.text), max_words=args.max_words)
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
    from .transform import transform

    try:
        print(transform(_read(args.text), unit=args.unit, model=args.model))
    except RuntimeError as exc:
        print(f"[변환 불가] {exc}\n프롬프트만 보려면 `gaejo prompt`를 사용하세요.", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gaejo", description="한국식 연구 발표 개조식 어휘 다듬기")
    p.add_argument("--version", action="store_true", help="버전 출력")
    sub = p.add_subparsers(dest="cmd")

    d = sub.add_parser("detect", help="종결 양식 판별")
    d.add_argument("text", help="문장(또는 -로 표준입력)")
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
    t.add_argument("--model", default=None)
    t.set_defaults(func=_cmd_transform)
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
    if args.cmd == "transform" and args.model is None:
        from .transform import DEFAULT_MODEL

        args.model = DEFAULT_MODEL
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
