"""개조식 준수도 메트릭 테스트."""
import pytest

pytest.importorskip("kiwipiepy")

from gaejo.score import score_text


def test_all_gaejo():
    rep = score_text("노이즈 강건성 확보\n성능 개선함\nattention 가중치 시각화")
    assert rep.n_lines == 3
    assert rep.korean_gaejo_ratio == 1.0
    assert rep.full_sentence_count == 0
    assert rep.warnings == []


def test_full_sentence_flagged():
    rep = score_text("우리는 정확도를 개선했습니다\n노이즈 강건성 확보")
    assert rep.full_sentence_count == 1
    assert rep.korean_gaejo_ratio == 0.5
    assert any("완전문장" in w for w in rep.warnings)


def test_bullet_markers_stripped():
    rep = score_text("- 성능 향상\n• 메모리 사용량 감소\n1. 학습 안정화")
    assert rep.n_lines == 3
    assert rep.korean_gaejo_ratio == 1.0


def test_english_lines_excluded_from_korean_ratio():
    rep = score_text("Experimental Results\n성능 향상")
    # 영문 줄은 한글 비율 분모에서 제외 → 한글 1줄이 개조식이므로 1.0
    assert rep.korean_gaejo_ratio == 1.0
    assert rep.ending_dist["영문"] == 1


def test_empty():
    rep = score_text("")
    assert rep.n_lines == 0
    assert rep.korean_gaejo_ratio == 0.0
