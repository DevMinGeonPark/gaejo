"""제안 테스트: cli.py 커버리지 0% 해소 (API 키 불필요)."""
import io
import json

import pytest

from gaejo.cli import build_parser, main


def test_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.startswith("gaejo ")


def test_no_args_prints_help(capsys):
    assert main([]) == 0
    assert "usage: gaejo" in capsys.readouterr().out


def test_build_parser_subcommands():
    p = build_parser()
    args = p.parse_args(["prompt", "텍스트", "--unit", "title", "--json"])
    assert args.cmd == "prompt" and args.unit == "title" and args.json is True


def test_detect_outputs_json(capsys):
    pytest.importorskip("kiwipiepy")
    assert main(["detect", "성능 개선함"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["ending"] == "ㅁ음" and d["is_gaejo"] is True


def test_score_outputs_json(capsys):
    pytest.importorskip("kiwipiepy")
    assert main(["score", "성능 향상\n우리는 개선했습니다", "--max-words", "5"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["n_lines"] == 2 and d["full_sentence_count"] == 1


def test_prompt_json_no_key(capsys):
    assert main(["prompt", "정확도를 개선했습니다", "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert "정확도를 개선했습니다" in d["user"] and d["system"]


def test_prompt_plain(capsys):
    assert main(["prompt", "정확도를 개선했습니다"]) == 0
    out = capsys.readouterr().out
    assert "=== SYSTEM ===" in out and "=== USER ===" in out


def test_stdin_dash(capsys, monkeypatch):
    pytest.importorskip("kiwipiepy")
    monkeypatch.setattr("sys.stdin", io.StringIO("성능 개선함\n"))
    assert main(["detect", "-"]) == 0
    assert json.loads(capsys.readouterr().out)["ending"] == "ㅁ음"


def test_transform_fails_cleanly_without_backend(capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert main(["transform", "정확도를 개선했습니다"]) == 1
    err = capsys.readouterr().err
    assert "변환 불가" in err and "gaejo prompt" in err


def test_detect_multiline_outputs_array(capsys):
    pytest.importorskip("kiwipiepy")
    assert main(["detect", "성능 개선함\n노이즈 강건성 확보"]) == 0
    arr = json.loads(capsys.readouterr().out)
    assert isinstance(arr, list) and len(arr) == 2
    assert [x["ending"] for x in arr] == ["ㅁ음", "명사"]
