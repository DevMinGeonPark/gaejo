# 기여 가이드

GAEJO에 기여해 주셔서 감사합니다.

## 개발 환경

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

## 규칙 변경 시

- 종결 양식 규칙(`prompt.RULESET`)이나 판별 로직(`detector.py`)을 바꿀 때는
  근거를 `docs/methodology.md`에 통계로 남겨 주세요.
- few-shot 예시(`src/gaejo/data/fewshot_pairs.json`)는 **반드시 독창적 합성 데이터**여야 합니다.
  특정 발표·논문 슬라이드의 텍스트를 그대로 옮기지 마세요(저작권).
- 새 변환쌍을 추가하면 `classify_ending(target).ending`이 `ending` 필드와 일치하는지 확인하세요.

## 코퍼스 분석 데이터

코퍼스 원본(영상·프레임·전사 텍스트)은 저작권상 저장소에 포함하지 않습니다.
집계 통계와 규칙만 문서화합니다.

## PR 체크리스트

- [ ] `pytest`, `ruff check` 통과
- [ ] 규칙 변경 시 방법론 문서 갱신
- [ ] 합성 데이터 원칙 준수
