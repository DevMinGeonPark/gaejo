"""종결 판별기 테스트 — EF/ETN 불일치 처리와 영문/조사 종결 분류 검증."""
import pytest

kiwipiepy = pytest.importorskip("kiwipiepy")  # noqa: F841

from gaejo.detector import classify_ending, is_gaejo


@pytest.mark.parametrize(
    "text,expected",
    [
        ("제안 모델이 정확도를 3.2%p 개선함", "ㅁ음"),   # 동사+음슴체, Kiwi는 EF로 태깅
        ("노이즈에 강건함", "ㅁ음"),                      # 형용사+음슴체, Kiwi는 ETN
        ("데이터를 수집함.", "ㅁ음"),                     # 마침표 있어도 음슴체
        ("성능 개선함이 확인됨", "ㅁ음"),
        ("향후 다양한 데이터셋 검증하기", "기"),
        ("노이즈 강건성 확보", "명사"),
        ("같은 색 같은 가중치 사용", "명사"),
        ("CYCLE 전략", "명사"),
        ("우리는 정확도를 개선했습니다", "완전문장"),
        ("실험 결과는 다음과 같다", "완전문장"),
        ("정확도를", "기타"),                            # 조사 종결
        ("Experimental Results", "영문"),                # 한글 없음
        ("Batch size 32", "영문"),
    ],
)
def test_classify_ending(text, expected):
    assert classify_ending(text).ending == expected


@pytest.mark.parametrize(
    "text,gaejo",
    [
        ("성능 향상", True),
        ("제안함", True),
        ("우리는 개선했습니다", False),
        ("정확도를", False),
        ("Results", False),  # 영문
    ],
)
def test_is_gaejo(text, gaejo):
    assert is_gaejo(text) is gaejo


def test_has_korean_flag():
    assert classify_ending("성능 향상").has_korean is True
    assert classify_ending("Results").has_korean is False


def test_empty():
    r = classify_ending("   ")
    assert r.ending in {"기타", "영문"}
    assert r.is_gaejo is False
