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
    assert rep.korean_gaejo_ratio is None  # 한글 줄 없음 → 평가 대상 아님


# ---- 감사 회귀 테스트 (불릿 정규식 / 한글 0줄 / '-기' 경고) ----

def test_decimal_and_year_not_stripped_as_bullet():
    from gaejo.score import _split_lines

    assert _split_lines("1.5배 성능 향상") == ["1.5배 성능 향상"]
    assert _split_lines("3.2 실험 설정") == ["3.2 실험 설정"]
    assert _split_lines("2024. 한국어 NLP 동향") == ["2024. 한국어 NLP 동향"]
    # 진짜 번호 마커는 여전히 제거
    assert _split_lines("1. 서론") == ["서론"]
    assert _split_lines("(1) 배경") == ["배경"]
    assert _split_lines("▶ 성능 향상") == ["성능 향상"]


def test_no_korean_lines_ratio_is_none():
    rep = score_text("Experimental Results\nSetup")
    assert rep.korean_gaejo_ratio is None
    assert any("한글 줄 없음" in w for w in rep.warnings)


def test_gi_ending_warned():
    rep = score_text("다양한 데이터셋 검증하기")
    assert rep.ending_dist["기"] == 1
    assert any("'-기' 종결" in w for w in rep.warnings)
