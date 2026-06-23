# GAEJO — 한국 연구 발표 개조식 변환기 v0.1.0

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org)

말하듯 풀어 쓴 슬라이드 문구를 한국 연구 발표의 **개조식(箇條式)** — 명사·명사형으로 끊어 압축한 불릿 — 으로 다듬어 주는 도구입니다. Claude Code·Codex 같은 에이전트가 변환을 맡고, GAEJO는 **개조식 규칙**과 **형태소 기반 검증**을 제공합니다. 변환 자체는 에이전트(LLM)가 하므로 **API 키가 없어도** 됩니다.

```
"우리는 정확도를 4.7%p 정도 끌어올렸습니다"   →  "정확도 약 4.7%p 향상"
"노이즈가 많아지니까 성능이 떨어집니다"        →  "노이즈 증가 → 성능 저하"
"저희가 제안하는 방법을 설명드리겠습니다"      →  "제안 방법"            (제목은 라벨로)
```

## 왜 개조식인가

한국 연구 발표 슬라이드는 완전문장으로 쓰지 않습니다. 명사·명사형으로 끊어 압축한 불릿이 관례죠. 그런데 슬라이드 초안을 LLM에 맡기면 십중팔구 말하듯 풀어쓰거나, 영어 문장 구조 그대로 옮겨 놓습니다.

영어권 슬라이드 가이드("불릿당 10단어" 같은)나 BLEU·ROUGE로는 이 한국어 종결·압축을 잡지 못합니다. 한국어 개조식의 핵심은 *어떻게 끝맺느냐*(명사냐, `-ㅁ/음`이냐, 완전문장이냐)에 있고, 그건 형태소를 봐야 알 수 있기 때문입니다.

GAEJO는 이 규칙을 실제 한국 발표 슬라이드 코퍼스에서 뽑아 정리하고, [Kiwi](https://github.com/bab2min/kiwi) 형태소 분석으로 변환 결과를 **결정론적으로** 검증합니다. 근거: [docs/methodology.md](docs/methodology.md)

## 개조식 6원칙

코퍼스(실제 발표 슬라이드)에서 도출하고 보정한 규칙입니다.

1. **명사로 끝낸다.** 기본은 순수 명사 종결 — "성능 향상", "한계 존재"(코퍼스의 약 75%). 주어·부사어를 거느린 완결 서술절이나 저자의 판단·당위일 때만 `-ㅁ/음`을 쓴다 — "제안함", "필요함". `-기`로 끝맺는 일은 없다(코퍼스 0%).
2. **압축하되 뜻은 지킨다.** 용언 어미를 잘라 명사화한다. 조사는 명사구로 묶이면 떨구고("최대 batch 사용"), 절차·인과를 한 줄에 풀어야 하면 살린다("PCA를 도입").
3. **기호로 줄인다.** 인과·비례·귀결은 `→` `⇒` `∝`, 라벨–정의 대응은 `:`로 외주화한다. "반복이 많아질수록 느려진다" → "반복 증가 ∝ 속도 저하".
4. **영어는 영어로.** LoRA·ROUGE·transformer 같은 전문용어는 원어 그대로. 정착된 한자어가 있을 때만 옮긴다(가중치·분산·처리량).
5. **제목은 라벨.** "제안 방법", "실험 결과"처럼 명사구로. 주장은 제목이 아니라 본문 불릿에 둔다.
6. **뉘앙스를 버리지 않는다.** 수치(4.7%p), 근사("약/정도"), 역접("다만/오히려")은 압축하더라도 살린다. 변환에서 가장 자주 깨지는 지점이고, GAEJO 검증이 집중해서 잡는 부분이다.

## 설치

아직 PyPI에 올리지 않았습니다. 소스에서 설치합니다.

```bash
git clone https://github.com/DevMinGeonPark/gaejo && cd gaejo
pip install -e ".[kiwi]"      # 판별·검증에 필요한 kiwipiepy 포함
```

코어 자체는 의존성이 없습니다. 종결 판별·검증에는 `kiwipiepy`, (선택) MCP 서버에는 `mcp`, (선택) 직접 API 변환에는 `anthropic`이 필요합니다 — 한 번에 다 받으려면 `".[all]"`. zsh에서는 대괄호를 따옴표로 감싸세요.

## 사용법 — Claude Code에서 3분

GAEJO의 1차 형태는 **Claude Code 스킬**입니다. 에이전트가 규칙대로 변환하고, `gaejo` CLI로 스스로 검증합니다.

**0. 전제.** [Claude Code](https://claude.com/claude-code)가 깔려 있어야 합니다(`claude --version`).

**1. 스킬 설치.**

```bash
mkdir -p ~/.claude/skills/gaejo && cp skill/SKILL.md ~/.claude/skills/gaejo/
```

**2. 그냥 부탁하세요.** Claude Code를 켜고 슬라이드 문구를 붙여넣은 뒤 "개조식으로 다듬어줘"라고 하면, "개조식·슬라이드·발표자료" 같은 신호에 스킬이 자동으로 잡힙니다.

**3. 안에서 일어나는 일.** 에이전트가 규칙을 읽고 변환한 다음, 줄마다 `gaejo check`로 검증합니다. 통과 못 하면 지적사항(`issues`)을 반영해 다시 고치는 루프를 돕니다.

```
$ gaejo check "모델 경량화가 반드시 필요합니다" "모델 경량화 필요함"
{"ok": false, "issues": ["뉘앙스 누락 범주: ['강조'] — 해당 뉘앙스를 살려라"]}
# '반드시'를 되살려 재변환
$ gaejo check "모델 경량화가 반드시 필요합니다" "모델 경량화 반드시 필요함"
{"ok": true, "issues": []}
```

> 변환은 에이전트(Claude)가, 검증은 `gaejo` CLI가 합니다. 그래서 **API 키가 필요 없습니다.**

## CLI — 에이전트가 부르는 도구

| 명령 | 하는 일 |
|---|---|
| `gaejo check "<원문>" "<변환본>"` | 변환 자기검증 — 개조식 준수 + 의미 보존 → `ok` / 고칠 점 |
| `gaejo score "<여러 줄>"` | 블록 단위 개조식 준수도 채점 |
| `gaejo detect "<줄>"` | 한 줄의 종결 양식 판별(명사 / ㅁ음 / 기 / 완전문장 / …) |
| `gaejo prompt "<문장>"` | 변환 규칙·few-shot 전체를 프롬프트로 출력 |

Codex처럼 스킬이 없는 에이전트는 `AGENTS.md`에 위 CLI 사용법을 적어 두면 똑같이 씁니다. 순수 MCP를 선호하면 `pip install -e ".[mcp]"` 후 `claude mcp add gaejo -- gaejo-mcp`로 같은 도구를 노출할 수 있습니다.

에이전트 없이 직접 변환까지 하고 싶다면(키 필요):

```bash
export ANTHROPIC_API_KEY=sk-...
gaejo transform "우리는 정확도를 4.7%p 정도 끌어올렸습니다"   # → 정확도 약 4.7%p 향상
```

## 구성 요소

| 모듈 | 역할 |
|---|---|
| `gaejo.detector` | Kiwi 종결 판별기. 음슴체 `-ㅁ`이 어간 품사·마침표에 따라 EF/ETN으로 갈리는 문제를 태그+어미형태로 해결 |
| `gaejo.score` | 개조식 준수도 메트릭(종결 비율·길이·완전문장 잔존). BLEU/ROUGE 비의존 |
| `gaejo.retention` | 의미 보존 검사 — 원문 대비 수치·전문용어·뉘앙스(근사/역접/강조/가능성) 누락 탐지 |
| `gaejo.evaluator.check` | 위 둘을 묶은 자기검증 진입점. CLI·스킬·MCP가 공유 |
| `gaejo.prompt` | 코퍼스 보정 규칙 + 합성 few-shot |
| `gaejo.hil` | 사람 검토 gold 적재 + LLM 판정과 사람 결정의 일치도(교정) |
| `gaejo.transform` · `gaejo.mcp_server` | (선택) 직접 API 변환 · MCP 서버 |

## 품질

홀드아웃 10케이스(few-shot과 겹치지 않음) 기준입니다.

| 축 | 점수 |
|---|---|
| 스타일 변환 정확도 (LLM 앙상블) | 0.97 |
| 의미 보존 (LLM 앙상블) | 0.92 |
| 자연스러움 (LLM 앙상블) | 0.95 |
| 개조식 종결 비율 (Kiwi, 객관) | 100% · 완전문장 0건 |

재현은 `ANTHROPIC_API_KEY=... python examples/evaluate.py --judge`, 방법론·약점은 [docs/evaluation.md](docs/evaluation.md)에 정리했습니다.

## 평가 캐스케이드

후보를 신뢰도 순으로 거르고, 통과 못 한 것만 사람에게 넘깁니다.

```
변환 → 객관 게이트(score + retention, 키 불필요) → LLM 판정(3축) → 사람 검토(HIL)
                                                                      └→ gold.jsonl
```

`gaejo review`로 후보를 승인·수정·기각하면 그 결정이 `gold.jsonl`로 쌓입니다. 이 gold는 (1) 나중에 참조 기반 평가의 정답이 되고 (2) LLM 판정이 사람과 얼마나 맞는지(`gaejo.hil.judge_agreement`로 상관·κ) 검증하는 데 씁니다.

## 데이터

동봉한 `src/gaejo/data/fewshot_pairs.json`은 전부 직접 만든 합성 예시입니다(특정 발표의 전사본이 아님). 규칙 보정에 쓴 코퍼스 분석은 문서에 통계로만 남기고, 원본 슬라이드 텍스트는 포함하지 않습니다.

## 한계

- 변환 품질은 에이전트(LLM)에 달려 있습니다. GAEJO는 변환을 *검증·교정*할 뿐, 직접 생성하지 않습니다.
- 의미 보존 검사는 형태소 휴리스틱입니다. 수치·용어·뉘앙스 누락은 잘 잡지만, 헤드라인 의문형·인용·연구질문을 완전문장으로 오탐할 수 있어 이런 항목은 예외로 둡니다(스킬이 안내). 주어 누락 같은 깊은 의미 손실은 LLM 판정의 몫입니다.
- 종결 규칙은 일반 학술 발표 기준이라, 도메인(공학 vs 인문사회)별 차이는 아직 반영하지 않았습니다.

## Contributors

- [MinGeonPark](https://github.com/DevMinGeonPark) — 설계·구현
- Claude (Anthropic) — 페어 프로그래밍

## 라이선스

[MIT](LICENSE)

---

**English** — GAEJO rewrites Korean presentation text into *gaejosik*, the nominal, telegraphic bullet style used in Korean academic slides (ending lines with nominalizers `-ㅁ/음` or bare nouns instead of full sentences). It ships as a Claude Code skill plus a Kiwi-based CLI: the agent rewrites, GAEJO supplies the rules and deterministic verification — no API key required. Rules are calibrated on a Korean research-slide corpus; bundled few-shot examples are original synthetic data. MIT licensed. See [docs/methodology.md](docs/methodology.md).
