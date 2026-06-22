# GAEJO 개조식

> PowerPoint 텍스트를 **한국 학술 연구 발표의 개조식(箇條式) 문체**로 다듬는 도구.
> 구어체·완전문장체 슬라이드 텍스트 → 명사·명사형 종결의 압축된 개조식으로.
>
> **Claude Code·Codex 같은 에이전트가 호출하는 MCP 도구**가 1차 사용 형태다 —
> LLM(에이전트)이 변환을 하고, GAEJO는 ① 개조식 규칙과 ② 결정론적 검증(판별·채점·의미보존)을 제공한다.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org)

```
"우리는 정확도를 4.7%p 정도 끌어올렸습니다"   →   "정확도 약 4.7%p 향상"      # 출력 예시(모델에 따라 다를 수 있음)
"방법론에 대해서 설명드리겠습니다"            →   "제안 방법론"               # 제목: 라벨형
"노이즈가 많아지니까 성능이 떨어졌습니다"      →   "노이즈 증가 → 성능 저하"
```

GAEJO는 파인튜닝 없이 **LLM 프롬프트 + 형태소 규칙**으로 동작한다. 규칙은 한국 연구 발표 슬라이드
코퍼스 분석으로 도출·보정했다(→ [docs/methodology.md](docs/methodology.md)).

---

## 설치

> 아직 PyPI에 배포되지 않았다. 소스에서 설치한다.

```bash
git clone https://github.com/DevMinGeonPark/gaejo && cd gaejo
pip install -e ".[all]"      # kiwipiepy + anthropic 포함
# 또는 부분 설치
pip install -e ".[kiwi]"     # 판별기·메트릭만 (LLM 변환 제외)
```

(zsh에서는 extras 대괄호를 반드시 따옴표로 감싼다.)
`gaejo` 코어 자체는 의존성이 없다. 판별/메트릭에는 `kiwipiepy`, MCP 서버에는 `mcp`가 필요하다.

## 에이전트 도구로 사용 (MCP) — Claude Code · Codex

**1차 사용 형태.** GAEJO는 스스로 LLM을 호출하지 않는다. Claude Code/Codex가 변환을 하고,
GAEJO MCP 서버가 규칙·검증 도구를 제공한다(API 키 불필요).

```bash
pip install -e ".[kiwi,mcp]"   # 또는 ".[all]"
```

**노출 도구 4개:**
| 도구 | 역할 |
|---|---|
| `gaejo_rules()` | 개조식 변환 규칙(스타일 가이드) — 변환 전에 읽음 |
| `detect_ending(text)` | 한 줄 종결 양식 판별 |
| `score(text)` | 블록 개조식 준수도 채점 |
| `check(original, output)` | **자기검증** — 개조식+의미보존 검사 후 고칠 점(issues) 반환 |

**에이전트 사용 흐름:** `gaejo_rules`로 규칙 로드 → 에이전트가 직접 변환 → `check(원문, 변환본)`으로
검증 → `ok:false`면 `issues`를 반영해 재변환.

**Claude Code 등록:**
```bash
claude mcp add gaejo -- gaejo-mcp
```
또는 프로젝트 `.mcp.json`:
```json
{ "mcpServers": { "gaejo": { "command": "gaejo-mcp" } } }
```

**Codex 등록** (`~/.codex/config.toml`):
```toml
[mcp_servers.gaejo]
command = "gaejo-mcp"
```

## 빠른 시작

### CLI

```bash
gaejo detect "성능 개선함"            # 종결 양식 판별 → {"ending": "ㅁ음", ...}
gaejo score  "제안 방법 제안
노이즈에 강건함"                       # 개조식 준수도 메트릭(객관)
gaejo prompt "정확도를 끌어올렸습니다"   # 변환 프롬프트만 출력(API 키 불필요)

export ANTHROPIC_API_KEY=sk-...
gaejo transform "우리는 정확도를 4.7%p 정도 끌어올렸습니다"
# → 정확도 약 4.7%p 향상     (출력 예시 — LLM 비결정성으로 표현이 달라질 수 있음)
gaejo transform - --unit slide --max-tokens 32000 < slide.txt   # 긴 입력은 상한 조절
```

### Python

```python
from gaejo import classify_ending, score_text
from gaejo.transform import transform          # ANTHROPIC_API_KEY 필요
from gaejo.evaluator import objective, llm_judge

classify_ending("성능 개선함").ending          # 'ㅁ음'
score_text("노이즈에 강건함\n성능 향상").korean_gaejo_ratio   # 1.0

orig = "기존 방법은 데이터가 많이 필요했는데 저희는 적게 써도 됩니다"
out = transform(orig, unit="bullet")
objective(orig, out)   # 객관 메트릭(개조식 종결 비율·길이·안티패턴) — 출력만 평가
llm_judge(orig, out)   # 3축 LLM 판정(스타일·의미보존·자연스러움)

# API 키 없이 외부 LLM에 넘길 메시지만 얻기
from gaejo.transform import messages_for
messages_for("...", unit="slide")   # {"system":..., "user":..., "model":...}
```

## 구성 요소

| 모듈 | 역할 |
|---|---|
| `gaejo.detector` | Kiwi 기반 종결 판별기. 음슴체 `-ㅁ`의 EF/ETN 불일치를 **태그+어미형태** 병용으로 해결 |
| `gaejo.score` | 개조식 준수도 메트릭(객관 축): 종결 비율·어절 수·완전문장 안티패턴. BLEU/ROUGE 비의존 |
| `gaejo.prompt` | 코퍼스 보정 규칙 + few-shot 빌더(augmented zero-shot) |
| `gaejo.mcp_server` | **MCP 서버**(Claude Code·Codex용 도구: rules/detect/score/check) |
| `gaejo.transform` | (선택) 직접 Anthropic API 호출 변환기 — 에이전트 없이 standalone으로 쓸 때만 |
| `gaejo.evaluator` | 3축 평가: 객관(스타일 `score` + 의미보존 `content_retention`) + LLM 판정 |
| `gaejo.hil` | Human-in-the-loop 검토·gold 적재, LLM judge↔사람 일치도(교정) |

## 개조식 핵심 규칙 (코퍼스 보정)

1. **순수 명사 종결이 디폴트(≈75%)** — `-ㅁ/음`은 완결 서술절·저자판단(≈24%), **`-기` 종결은 0%**.
2. **명사 vs -ㅁ음 변별 = 통사적 완결성** — 명사구만 → 명사 종결, 완결 서술절 → `-ㅁ음`.
3. **제목은 라벨형 명사구** — 주장형 헤드라인 강제하지 않음(한국 발표 관행). 주장은 본문 글머리표로.
4. **조사 생략은 조건부** — 명사구화 가능 시만 생략, 절차·인과 서술 시 보존.
5. **기호 압축** — 인과·비례·귀결은 `→/⇒/∝`, 라벨-정의는 `:`로 외주화.
6. **영어 전문용어 원어 유지** — 강제 번역 금지, '영어 명사구 + 한국어 조사/술어' 골격.

자세한 근거·반박된 가정·종결 결정 트리: **[docs/methodology.md](docs/methodology.md)**

## 품질 (홀드아웃 10케이스)

| 축 | 점수 |
|---|---|
| 스타일 변환 정확도 (LLM 앙상블) | **0.97** |
| 의미 보존 (LLM 앙상블) | **0.92** |
| 자연스러움 (LLM 앙상블) | **0.95** |
| 개조식 종결 비율 (객관/Kiwi) | **100%** · 완전문장 0건 |

재현: `ANTHROPIC_API_KEY=... python examples/evaluate.py --judge` · 방법론·약점: **[docs/evaluation.md](docs/evaluation.md)**

## 평가 캐스케이드 + HIL

변환 후보를 **신뢰도 순으로 걸러내고**, 통과 못 한 것만 사람이 검토한다:

```
transform → 객관 게이트(score+retention, 키 불필요) → LLM judge(3축) → HIL(사람 승인/수정)
                                                                          └→ gold.jsonl
```

`gaejo review --cases cases.jsonl --out gold.jsonl` 로 후보를 승인(`a`)/수정(`e`)/기각(`r`)하면,
사람 결정·수정본이 **gold**로 쌓인다. 이 gold는 (1) 향후 참조 기반 평가의 정답 (2) **LLM judge 검증**
(judge 점수 ↔ 사람 결정의 상관·κ — `gaejo.hil.judge_agreement`)에 쓰인다. 후보가 없으면 `transform`으로
생성(키 필요), 있으면 키 없이 검토만 가능. 자세히: **[docs/evaluation.md](docs/evaluation.md)**

## 데이터

동봉된 `src/gaejo/data/fewshot_pairs.json`은 **모두 독창적 합성 예시**다(특정 발표 전사본 아님).
규칙 보정에 쓰인 코퍼스 분석은 방법론 문서에 통계로만 기술하며, 원본 슬라이드 텍스트는 포함하지 않는다.

## 한계

- LLM 변환 성능은 백엔드 모델에 의존하며, 의미보존(특히 근사·역접 뉘앙스, 주어) 손실이 약점이다.
- 종결 규칙은 일반 학술 발표 기준이며, 도메인(공학 vs 인문사회)별 차이는 아직 반영하지 않았다.
- 형태소 판별은 `kiwipiepy` 버전 태깅에 의존한다.

## 라이선스

[MIT](LICENSE)

---

## English summary

**GAEJO** rewrites Korean presentation text into *gaejosik* — the nominal, telegraphic bullet style
used in Korean academic research slides (e.g. ending clauses with nominalizers `-ㅁ/음` or bare nouns
instead of full sentences). It is a prompt-only LLM harness plus a Kiwi-based morphological detector,
with rules calibrated on a Korean research-slide corpus. No fine-tuning required. MIT licensed.
Bundled few-shot examples are original synthetic data. See [docs/methodology.md](docs/methodology.md).
