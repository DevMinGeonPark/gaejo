"""의미 보존 객관 메트릭 테스트."""
import pytest

pytest.importorskip("kiwipiepy")

from gaejo.retention import content_retention


def test_numbers_preserved_arabic_and_korean():
    # "두 배" → "2배" 도 보존으로 인정(수사 정규화)
    r = content_retention("추론 속도를 두 배 끌어올림", "추론 속도 2배 향상")
    assert r["numbers"]["ratio"] == 1.0 and r["numbers"]["missing"] == []


def test_number_loss_detected():
    r = content_retention("정확도 4.7%p 향상", "정확도 향상")
    assert r["numbers"]["ratio"] == 0.0
    assert "4.7" in r["numbers"]["missing"]


def test_hedge_category_preserved_across_synonyms():
    # '정도'(근사) → '약'(근사): 같은 범주이므로 보존
    r = content_retention("4.7%p 정도 향상", "약 4.7%p 향상")
    assert r["hedges"]["ratio"] == 1.0


def test_emphasis_hedge_loss_detected():
    # 평가에서 관측된 실패: '반드시' 탈락
    r = content_retention("모델 경량화가 반드시 필요하다", "모델 경량화 필요함")
    assert "강조" in r["hedges"]["missing_categories"]
    assert r["hedges"]["ratio"] == 0.0


def test_latin_term_preserved():
    r = content_retention("LoRA 모듈을 적용했다", "LoRA 모듈 적용")
    assert r["terms"]["ratio"] == 1.0


def test_latin_term_loss_detected():
    r = content_retention("attention 메커니즘 사용", "메커니즘 사용")
    assert r["terms"]["ratio"] == 0.0 and "attention" in r["terms"]["missing"]


def test_no_checkable_content_returns_none():
    r = content_retention("성능 향상", "성능 개선")
    assert r["content_retention"] is None  # 수치·라틴·헤지 모두 없음


def test_hedge_form_not_false_matched_in_compound():
    # '요약'의 '약'이 근사 헤지로 오탐되지 않아야 한다(형태소 매칭)
    r = content_retention("결과 요약 제시", "결과 요약")
    assert r["hedges"]["ratio"] is None  # '약'은 NNG '요약'의 일부, 헤지 아님


def test_objective_includes_retention():
    from gaejo.evaluator import objective

    d = objective("정확도 4.7%p 정도 향상", "정확도 약 4.7%p 향상")
    assert "retention" in d
    assert d["retention"]["numbers"]["ratio"] == 1.0
    assert d["retention"]["hedges"]["ratio"] == 1.0
