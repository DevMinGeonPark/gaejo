"""MCP 서버 도구 테스트 — 서버를 띄우지 않고 도구 함수의 동작을 검증.

mcp SDK는 Python 3.10+가 필요하므로(서버 모듈 import 시점에 필요), 미설치/구버전 환경은 skip.
"""
import pytest

pytest.importorskip("kiwipiepy")
pytest.importorskip("mcp")

from gaejo import mcp_server as M


def _call(tool_name):
    """FastMCP에 등록된 도구의 원본 콜러블을 꺼낸다(데코레이터가 감싼 함수)."""
    fn = getattr(M, tool_name)
    return fn


def test_gaejo_rules_returns_ruleset():
    assert _call("gaejo_rules")().startswith("너는 한국 학술")


def test_detect_ending_tool():
    d = _call("detect_ending")("성능 개선함")
    assert d["ending"] == "ㅁ음" and d["is_gaejo"] is True


def test_score_tool():
    d = _call("score")("성능 향상\n우리는 개선했습니다")
    assert d["n_lines"] == 2 and d["full_sentence_count"] == 1


def test_check_pass():
    d = _call("check")("정확도를 4.7%p 정도 높였습니다", "정확도 약 4.7%p 향상")
    assert d["ok"] is True and d["issues"] == []
    assert d["gaejo_ending_ratio"] == 1.0


def test_check_flags_full_sentence_and_number_loss():
    # 완전문장 + 수치 누락 둘 다 잡아야 한다
    d = _call("check")("정확도를 4.7%p 개선했습니다", "정확도를 개선했습니다")
    assert d["ok"] is False
    assert any("완전문장" in i for i in d["issues"])
    assert any("수치 누락" in i and "4.7" in i for i in d["issues"])


def test_check_flags_hedge_loss():
    d = _call("check")("모델 경량화가 반드시 필요합니다", "모델 경량화 필요함")
    assert d["ok"] is False
    assert any("강조" in i for i in d["issues"])


def test_server_registers_four_tools():
    # FastMCP 인스턴스에 도구 4개가 등록됐는지(비동기 list_tools)
    import asyncio

    tools = asyncio.run(M.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"gaejo_rules", "detect_ending", "score", "check"} <= names
