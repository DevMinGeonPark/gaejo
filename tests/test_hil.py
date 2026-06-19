"""HIL gold 적재·judge 교정 테스트(키 불필요)."""
import json

import pytest

from gaejo.hil import (
    gold_stats,
    judge_agreement,
    load_gold,
    make_record,
)


def test_make_record_accept():
    r = make_record("원문", "bullet", "성능 향상", "accept")
    assert r.final == "성능 향상" and r.decision == "accept"


def test_make_record_edit_requires_text():
    with pytest.raises(ValueError):
        make_record("원문", "bullet", "후보", "edit")
    r = make_record("원문", "bullet", "후보", "edit", edited="수정본")
    assert r.final == "수정본"


def test_make_record_reject_final_none():
    r = make_record("원문", "bullet", "후보", "reject")
    assert r.final is None


def test_make_record_invalid_decision():
    with pytest.raises(ValueError):
        make_record("원문", "bullet", "후보", "maybe")


def test_append_load_roundtrip(tmp_path):
    p = tmp_path / "gold.jsonl"
    from gaejo.hil import append_gold

    append_gold(str(p), make_record("a", "bullet", "A", "accept"))
    append_gold(str(p), make_record("b", "title", "B", "reject"))
    recs = load_gold(str(p))
    assert len(recs) == 2
    assert gold_stats(recs)["decisions"] == {"accept": 1, "edit": 0, "reject": 1}


def test_judge_agreement_perfect():
    # judge 높음↔사람 accept, judge 낮음↔reject → 완전 일치
    recs = [
        {"decision": "accept", "judge": {"style_accuracy": 0.95,
         "content_preservation": 0.95, "naturalness": 0.95}},
        {"decision": "reject", "judge": {"style_accuracy": 0.4,
         "content_preservation": 0.4, "naturalness": 0.4}},
        {"decision": "accept", "judge": {"style_accuracy": 0.9,
         "content_preservation": 0.9, "naturalness": 0.9}},
    ]
    agr = judge_agreement(recs, threshold=0.85)
    assert agr["n"] == 3
    assert agr["accept_accuracy"] == 1.0
    assert agr["pearson_r"] is not None and agr["pearson_r"] > 0.9


def test_judge_agreement_no_judge():
    recs = [{"decision": "accept"}, {"decision": "reject"}]
    assert judge_agreement(recs)["n"] == 0


def test_review_cli_simulated(tmp_path, monkeypatch, capsys):
    """review 루프를 candidate 사전제공 + 모의 키입력으로 구동(키 불필요)."""
    pytest.importorskip("kiwipiepy")
    import io

    from gaejo.cli import main

    cases = tmp_path / "cases.jsonl"
    cases.write_text(
        json.dumps({"id": 1, "unit": "bullet", "original": "정확도를 올렸습니다",
                    "candidate": "정확도 향상"}, ensure_ascii=False) + "\n"
        + json.dumps({"id": 2, "unit": "bullet", "original": "데이터가 필요합니다",
                      "candidate": "데이터 필요"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "gold.jsonl"
    # 1번 accept, 2번 edit→"데이터 필요함"
    monkeypatch.setattr("sys.stdin", io.StringIO("a\ne\n데이터 필요함\n\n"))
    rc = main(["review", "--cases", str(cases), "--out", str(out)])
    assert rc == 0
    recs = load_gold(str(out))
    assert len(recs) == 2
    assert recs[0]["decision"] == "accept" and recs[0]["final"] == "정확도 향상"
    assert recs[1]["decision"] == "edit" and recs[1]["final"] == "데이터 필요함"
    # 객관 메트릭이 후보 기준으로 붙었는지
    assert recs[0]["objective"]["korean_gaejo_ratio"] == 1.0
