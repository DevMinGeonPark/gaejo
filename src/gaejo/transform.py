"""개조식 변환 실행기.

prompt.build_messages()로 만든 (system, user)를 LLM에 보내 개조식 결과를 받는다.
파인튜닝 없는 프롬프트-온리 하네스(augmented zero-shot + few-shot).
Anthropic API를 기본 백엔드로 쓰되, 키가 없으면 messages_for()로
메시지만 얻어 외부 LLM에 넘길 수 있다.
"""
from __future__ import annotations

import os

from .prompt import build_messages

DEFAULT_MODEL = "claude-opus-4-8"  # 현행 권장 기본. 비용 우선이면 claude-sonnet-4-6 지정
# 출력 토큰은 실제 생성분만 과금되므로 상향에 비용 부담 없음(스트리밍이라 큰 값도 안전).
DEFAULT_MAX_TOKENS = 16000


def messages_for(text: str, unit: str = "bullet", n_per_type: int = 5) -> dict:
    """API 키 없이 외부 LLM(또는 워크플로 에이전트)에 넘길 수 있도록 메시지만 반환."""
    system, user = build_messages(text, unit, n_per_type)
    return {"system": system, "user": user, "model": DEFAULT_MODEL}


def transform(
    text: str,
    unit: str = "bullet",
    model: str = DEFAULT_MODEL,
    n_per_type: int = 5,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """텍스트를 개조식으로 변환한다. ANTHROPIC_API_KEY(또는 AUTH_TOKEN) 필요."""
    system, user = build_messages(text, unit, n_per_type)
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic SDK 미설치: `pip install anthropic`") from exc
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise RuntimeError("ANTHROPIC_API_KEY(또는 ANTHROPIC_AUTH_TOKEN) 미설정")
    client = anthropic.Anthropic()
    # 스트리밍 사용: 비스트리밍은 max_tokens가 크면(~21K+) SDK가 ValueError를 던진다(10분 가드).
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        resp = stream.get_final_message()
    if resp.stop_reason == "max_tokens":
        raise RuntimeError(
            f"출력이 max_tokens({max_tokens})에서 잘림 — "
            "max_tokens를 상향하거나 입력을 나눠 변환하세요"
        )
    out = next((b.text for b in resp.content if b.type == "text"), None)
    if out is None:
        raise RuntimeError(f"텍스트 응답 없음 (stop_reason={resp.stop_reason})")
    return out.strip()
