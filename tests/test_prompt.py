"""프롬프트 빌더·few-shot 데이터 테스트 (kiwipiepy 불필요)."""
from gaejo.prompt import RULESET, build_messages, load_pairs, select_fewshot


def test_pairs_load_and_shape():
    pairs = load_pairs()
    assert len(pairs) >= 12
    for p in pairs:
        assert set(p) >= {"source", "target", "ending", "rules"}
        assert p["ending"] in {"명사", "ㅁ음", "기"}


def test_select_fewshot_covers_both_endings():
    chosen = select_fewshot(3)
    endings = {p["ending"] for p in chosen}
    assert "명사" in endings and "ㅁ음" in endings
    assert len(chosen) <= 6


def test_build_messages_contains_rules_and_input():
    system, user = build_messages("정확도를 끌어올렸습니다", unit="bullet")
    assert system == RULESET
    assert "정확도를 끌어올렸습니다" in user
    assert "[예시]" in user and "입력:" in user


def test_unit_variants():
    _, user_title = build_messages("방법론을 설명합니다", unit="title")
    assert "라벨형" in user_title
    _, user_slide = build_messages("...", unit="slide")
    assert "슬라이드 전체" in user_slide


def test_synthetic_only_no_attribution_markers():
    # 합성 데이터에 특정 발표/논문 식별자가 섞이지 않았는지 가벼운 가드
    blob = " ".join(p["source"] + p["target"] for p in load_pairs())
    assert "DSBA" not in blob
