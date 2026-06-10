"""개조식 변환 실행기.

prompt.build_messages()로 만든 (system, user)를 LLM에 보내 개조식 결과를 받는다.
파인튜닝 없는 프롬프트-온리 하네스(augmented zero-shot + few-shot).
Anthropic API를 기본 백엔드로 쓰되, 키가 없으면 messages_for()로
메시지만 얻어 외부 LLM에 넘길 수 있다.
"""
from __future__ import annotations

import os

from .prompt import build_messages

DEFAULT_MODEL = "claude-sonnet-4-6"  # 변환은 sonnet으로 충분, 필요시 opus로 상향


def messages_for(text: str, unit: str = "bullet", n_per_type: int = 5) -> dict:
    """API 키 없이 외부 LLM(또는 워크플로 에이전트)에 넘길 수 있도록 메시지만 반환."""
    system, user = build_messages(text, unit, n_per_type)
    return {"system": system, "user": user, "model": DEFAULT_MODEL}


def transform(
    text: str,
    unit: str = "bullet",
    model: str = DEFAULT_MODEL,
    n_per_type: int = 5,
    max_tokens: int = 1024,
) -> str:
    """텍스트를 개조식으로 변환한다. ANTHROPIC_API_KEY 필요."""
    system, user = build_messages(text, unit, n_per_type)
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic SDK 미설치: `pip install gaejo[anthropic]`") from exc
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY 미설정")
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text.strip()
