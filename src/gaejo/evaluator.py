"""개조식 변환 평가기 (3축).

TST 평가는 (1) 스타일 변환 정확도 (2) 내용 보존 (3) 자연스러움의 다차원이며,
BLEU/ROUGE는 인간 판단과 상관이 낮다 → 규칙 메트릭 + LLM 판정을 결합한다.

축 분담:
  - 스타일(객관): score.py의 개조식 종결 비율·길이 규칙(Kiwi). 빠른 게이트.
  - 의미보존·자연스러움(주관): LLM 판정(가능하면 앙상블). 본 모듈은 API 백엔드를 제공하고,
    키가 없으면 judge_prompt()로 판정 프롬프트만 노출한다(외부 LLM/워크플로 에이전트용).
"""
from __future__ import annotations

import json
import os

from .retention import content_retention
from .score import score_text

JUDGE_AXES = {
    "style_accuracy": "0~1, 개조식 문체(명사/명사형 종결, 압축, 라벨형)에 얼마나 부합하는가",
    "content_preservation": "0~1, 원문의 의미·수치·인과·고유명사·뉘앙스를 보존했는가",
    "naturalness": "0~1, 한국 연구 발표 슬라이드로서 자연스럽고 비문이 없는가",
}

_JUDGE_MODEL = "claude-opus-4-8"


def objective(original: str, output: str, max_words: int = 12) -> dict:
    """객관 메트릭 = 스타일 축(출력) + 의미 보존 축(원문↔출력).

    - 반환 dict는 ``score_text(output)``의 필드(스타일)에 ``retention`` 키(의미 보존)를 더한다.
    - 의미 보존은 수치·전문용어·헤지어 보존을 규칙으로 측정한다(LLM 불필요). 자연스러움 축과
      더 정밀한 의미 판정은 ``llm_judge``의 몫.
    """
    d = score_text(output, max_words=max_words).as_dict()
    d["retention"] = content_retention(original, output)
    return d


def judge_prompt(original: str, output: str) -> str:
    """LLM 판정자에게 줄 프롬프트(워크플로 에이전트/API 공용)."""
    axes = "\n".join(f"- {k}: {v}" for k, v in JUDGE_AXES.items())
    return (
        "다음은 한국어 슬라이드 텍스트를 개조식으로 변환한 결과다. 3축으로 평가하라.\n\n"
        f"[원문]\n{original}\n\n[개조식 변환]\n{output}\n\n"
        f"평가 축:\n{axes}\n"
        "각 0~1 실수로, comment는 한 줄로(문제점 위주). JSON만 출력."
    )


def llm_judge(original: str, output: str, model: str = _JUDGE_MODEL,
              max_tokens: int = 1024) -> dict:
    """API 기반 단일 판정. 앙상블은 호출측에서 여러 model/seed로 반복."""
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic SDK 미설치: `pip install anthropic`") from exc
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise RuntimeError("ANTHROPIC_API_KEY(또는 ANTHROPIC_AUTH_TOKEN) 미설정")
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": judge_prompt(original, output)}],
    )
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("판정 응답이 max_tokens에서 잘림 — max_tokens 상향 필요")
    txt = next((b.text for b in resp.content if b.type == "text"), "") or ""
    start = txt.find("{")
    if start == -1:
        raise RuntimeError(f"판정 응답에 JSON 없음: {txt[:120]!r}")
    try:
        obj, _ = json.JSONDecoder().raw_decode(txt, start)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"판정 응답 파싱 실패: {txt[:120]!r}") from exc
    return obj
