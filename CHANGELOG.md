# Changelog

이 프로젝트는 [Keep a Changelog](https://keepachangelog.com/)와
[Semantic Versioning](https://semver.org/)을 따른다.

## [Unreleased]

### Fixed (멀티에이전트 감사 — 61건 발견, 46건 확정 반영)
- **detector**: NFD(분해형) 한글 입력이 '영문'으로 오분류되던 버그 — NFC 정규화 전처리 추가.
  zero-width 문자(U+200B 등) 제거, 후행 이모지(W_EMOJI) 무시, 한글 없는 기호 전용 줄('---', '→')을
  '영문'으로 분류, URL/EMAIL 종결을 체언성 종결로 인정.
- **score**: 불릿 정규식이 소수("1.5배")·절번호("3.2")·연도("2024.")를 잘라먹던 버그 수정
  (숫자 마커 1~3자리 + 뒤 숫자 negative lookahead). 한국 PPT 머리기호(▶ ■ ○ ● ※ ‣ 등) 확장.
  한글 줄이 없으면 `korean_gaejo_ratio`가 0.0 대신 `None`. '-기' 종결 경고 추가.
- **prompt**: `load_pairs()`의 lru_cache가 가변 리스트를 반환해 호출자 변형 시 캐시가 오염되던 버그.
- **transform**: `stop_reason == "max_tokens"` 무음 잘림 가드, 빈/비텍스트 응답 가드,
  `ANTHROPIC_AUTH_TOKEN` 인정. 기본 `max_tokens` 1024 → 16000.
- **evaluator**: `llm_judge` JSON 추출 견고화(`raw_decode` + 잘림/비JSON 가드), max_tokens 400 → 1024.
- **cli**: `--max-tokens` 플래그 추가, `--model` 기본값 우회 로직 제거(빈 문자열/직접 호출 경로 수정),
  detect/score의 kiwipiepy 미설치 안내, 멀티라인 detect는 줄별 배열 출력, Anthropic API 오류 처리.

### Changed
- 기본 모델을 `claude-sonnet-4-6` → `claude-opus-4-8`(현행 권장)로 갱신.
- `transform()`이 스트리밍(`messages.stream`)을 사용 — 큰 `max_tokens`에서도 SDK 10분 가드에 걸리지 않음.
- 자모 전용 줄("ㅋㅋㅋ")은 이제 한국어로 취급되어 '영문'이 아닌 '기타'로 분류됨(평가 분모 포함).
- 패키징: PEP 639 라이선스 표기(`License-Expression: MIT`), 버전 단일 소스화(hatch dynamic),
  `py.typed` 추가(PEP 561), placeholder URL 제거.
- CI: Python 3.9~3.14 매트릭스, pip 캐시, kiwipiepy 임포트 가드, `pytest -rs`.
- 테스트 30개 → 62개(cli/transform/evaluator 신규 + 감사·재검증 회귀 테스트).

### Added (MCP 서버 — 에이전트 도구 형태)
- `gaejo.mcp_server` + `gaejo-mcp` 실행 스크립트 — Claude Code·Codex가 호출하는 MCP 도구
  (`gaejo_rules`/`detect_ending`/`score`/`check`). LLM은 에이전트가 담당, GAEJO는 규칙+결정론적 검증 제공(키 불필요).
- `check(original, output)`: 자기검증 도구 — 개조식 준수+의미보존 후 고칠 점(issues) 반환, ok 게이트.
- `[project.optional-dependencies] mcp`. 테스트 80 → 87개(mcp 7건, 라이브 stdio 호출 포함).

### Added (HIL + 평가 캐스케이드)
- `gaejo.hil` — Human-in-the-loop 검토 gold 적재(JSONL) + `judge_agreement`(LLM judge↔사람 일치도:
  pearson·accept정확도·Cohen's κ). LLM judge를 사람 정답으로 검증하는 교정 도구.
- CLI `gaejo review --cases ... --out gold.jsonl` — 후보 승인/수정/기각 인터랙티브 루프
  (후보·judge 사전제공 시 키 불필요). `examples/hil_cases.jsonl` 샘플 동봉.
- 테스트 71 → 79개(hil 8건).

### Added (의미 보존 객관 메트릭)
- `gaejo.retention.content_retention(original, output)` — 수치·전문용어·헤지어 보존을 형태소 규칙으로
  측정(LLM/키 불필요). 평가에서 측정된 약점 축(수치·뉘앙스 누락)을 객관 게이트로 포착.
- `gaejo.evaluator.objective`가 이제 `original`을 실제로 사용 — 반환 dict에 `retention` 키 추가
  (감사 지적사항: objective가 original을 무시하던 문제 해소).
- 테스트 62 → 71개(retention 9건).

### Docs
- `docs/evaluation.md` + `examples/evaluate.py` + `examples/eval_cases.json` 추가 —
  홀드아웃 10케이스 기능 검증(스타일 0.97·의미보존 0.92·자연 0.95·개조식 종결 100%).
  합성 few-shot 교체 후에도 품질 유지·향상 확인.

## [0.1.0] - 2026-06-10

### Added
- `gaejo.detector` — Kiwi 기반 개조식 종결 판별기. 음슴체 `-ㅁ`의 EF/ETN 불일치를 태그+어미형태 병용으로 해결.
- `gaejo.score` — 개조식 준수도 메트릭(종결 비율·어절 수·완전문장 안티패턴), BLEU/ROUGE 비의존.
- `gaejo.prompt` — 코퍼스 보정 규칙 + few-shot 빌더(augmented zero-shot).
- `gaejo.transform` — Anthropic API 기반 변환 실행기 + 키 없이 메시지만 얻는 `messages_for`.
- `gaejo.evaluator` — 3축 평가(객관 메트릭 + LLM 판정 프롬프트).
- `gaejo` CLI (`detect`/`score`/`prompt`/`transform`).
- 독창적 합성 few-shot 데이터(16쌍), 방법론 문서, 테스트, CI.
