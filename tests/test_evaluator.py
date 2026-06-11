"""evaluator 모듈 테스트 — judge_prompt/objective(키 불필요) + llm_judge 스텁."""
import sys
import types

import pytest

from gaejo.evaluator import JUDGE_AXES, judge_prompt, llm_judge, objective


def test_judge_prompt_contains_axes_and_texts():
    p = judge_prompt("원문입니다", "변환 결과")
    assert "원문입니다" in p and "변환 결과" in p
    for axis in JUDGE_AXES:
        assert axis in p


def test_objective_scores_output_only():
    pytest.importorskip("kiwipiepy")
    # original은 인터페이스 대칭용 — 출력 기준으로만 채점된다
    d = objective("우리는 크게 개선했습니다", "성능 향상")
    assert d["korean_gaejo_ratio"] == 1.0
    assert d["full_sentence_count"] == 0


class _Block:
    def __init__(self, type_, text=""):
        self.type = type_
        self.text = text


class _Resp:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


def _stub_anthropic(monkeypatch, resp):
    fake = types.ModuleType("anthropic")

    class _Messages:
        def create(self, **kwargs):
            return resp

    class _Client:
        def __init__(self):
            self.messages = _Messages()

    fake.Anthropic = _Client
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")


def test_llm_judge_parses_wrapped_json(monkeypatch):
    txt = (
        '평가 결과는 다음과 같습니다.\n```json\n'
        '{"style_accuracy": 0.9, "content_preservation": 0.8,'
        ' "naturalness": 0.95, "comment": "양호"}\n```\n추가 해설 } 텍스트'
    )
    _stub_anthropic(monkeypatch, _Resp("end_turn", [_Block("text", txt)]))
    d = llm_judge("원문", "출력")
    assert d["style_accuracy"] == 0.9 and d["comment"] == "양호"


def test_llm_judge_raises_on_truncation(monkeypatch):
    _stub_anthropic(monkeypatch, _Resp("max_tokens", [_Block("text", '{"style')]))
    with pytest.raises(RuntimeError, match="잘림"):
        llm_judge("원문", "출력")


def test_llm_judge_raises_on_no_json(monkeypatch):
    _stub_anthropic(monkeypatch, _Resp("end_turn", [_Block("text", "JSON이 아닌 응답")]))
    with pytest.raises(RuntimeError, match="JSON 없음"):
        llm_judge("원문", "출력")
