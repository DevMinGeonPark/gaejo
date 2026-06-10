# Changelog

이 프로젝트는 [Keep a Changelog](https://keepachangelog.com/)와
[Semantic Versioning](https://semver.org/)을 따른다.

## [0.1.0] - 2026-06-10

### Added
- `gaejo.detector` — Kiwi 기반 개조식 종결 판별기. 음슴체 `-ㅁ`의 EF/ETN 불일치를 태그+어미형태 병용으로 해결.
- `gaejo.score` — 개조식 준수도 메트릭(종결 비율·어절 수·완전문장 안티패턴), BLEU/ROUGE 비의존.
- `gaejo.prompt` — 코퍼스 보정 규칙 + few-shot 빌더(augmented zero-shot).
- `gaejo.transform` — Anthropic API 기반 변환 실행기 + 키 없이 메시지만 얻는 `messages_for`.
- `gaejo.evaluator` — 3축 평가(객관 메트릭 + LLM 판정 프롬프트).
- `gaejo` CLI (`detect`/`score`/`prompt`/`transform`).
- 독창적 합성 few-shot 데이터(16쌍), 방법론 문서, 테스트, CI.
