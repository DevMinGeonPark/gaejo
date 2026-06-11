"""transform 모듈 테스트 — API 키 없이 가능한 경로 + anthropic 스텁 경로."""
import sys
import types

import pytest

from gaejo.transform import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, messages_for, transform


def test_messages_for_shape():
    msg = messages_for("정확도를 끌어올렸습니다", unit="bullet")
    assert set(msg) == {"system", "user", "model"}
    assert msg["model"] == DEFAULT_MODEL
    assert "정확도를 끌어올렸습니다" in msg["user"]
    assert "[예시]" in msg["user"] and "개조식" in msg["system"]


def test_messages_for_unit_propagates():
    title = messages_for("방법론을 설명합니다", unit="title")
    assert "라벨형" in title["user"]


def test_transform_raises_without_credentials(monkeypatch):
    pytest.importorskip("anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="미설정"):
        transform("정확도를 개선했습니다")


class _Block:
    def __init__(self, type_, text=""):
        self.type = type_
        self.text = text


class _Resp:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


def _stub_anthropic(monkeypatch, resp):
    """sys.modules에 가짜 anthropic을 주입해 네트워크 없이 transform 본체를 검증."""
    fake = types.ModuleType("anthropic")

    class _Stream:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get_final_message(self):
            return resp

    class _Messages:
        def stream(self, **kwargs):
            return _Stream()

    class _Client:
        def __init__(self):
            self.messages = _Messages()

    fake.Anthropic = _Client
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")


def test_transform_returns_text(monkeypatch):
    _stub_anthropic(monkeypatch, _Resp("end_turn", [_Block("text", " 성능 향상 ")]))
    assert transform("성능이 좋아졌습니다") == "성능 향상"


def test_transform_raises_on_max_tokens_truncation(monkeypatch):
    _stub_anthropic(monkeypatch, _Resp("max_tokens", [_Block("text", "잘린 출")]))
    with pytest.raises(RuntimeError, match="잘림"):
        transform("긴 입력", max_tokens=DEFAULT_MAX_TOKENS)


def test_transform_raises_on_empty_content(monkeypatch):
    _stub_anthropic(monkeypatch, _Resp("refusal", []))
    with pytest.raises(RuntimeError, match="텍스트 응답 없음"):
        transform("입력")
