"""GAEJO MCP 서버 — Claude Code·Codex 등 에이전트가 호출하는 개조식 도구.

설계: LLM은 에이전트(Claude Code/Codex) 자신이다. GAEJO는 스스로 텍스트를 생성하지 않고,
에이전트에게 (1) 개조식 변환 규칙(스타일 가이드)과 (2) 결과를 검증할 결정론적 도구
(종결 판별·준수도 채점·의미 보존 검사)를 제공한다. API 키 불필요.

전형적 사용 흐름(에이전트 입장):
  1. `gaejo_rules`로 규칙을 읽는다.
  2. 에이전트가 직접 구어체→개조식으로 변환한다.
  3. `check(원문, 변환본)`으로 검증하고, issues가 있으면 고쳐 다시 검증한다.

실행: `gaejo-mcp` (stdio). Claude Code/Codex의 MCP 설정에 등록해 사용.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .detector import classify_ending
from .prompt import RULESET
from .retention import content_retention
from .score import score_text

mcp = FastMCP("gaejo")


@mcp.tool()
def gaejo_rules() -> str:
    """한국 학술 연구 발표 PPT의 개조식(箇條式) 변환 규칙(스타일 가이드)을 반환한다.

    구어체/완전문장체를 개조식으로 바꾸기 전에 이 규칙을 따른다. 종결 양식, 압축,
    조사 생략, 기호 압축, 어휘, 제목 라벨화, 안티패턴 교정 지침을 담는다.
    """
    return RULESET


@mcp.tool()
def detect_ending(text: str) -> dict:
    """한 줄(불릿/구)의 종결 양식을 판별한다.

    ending ∈ {명사, ㅁ음, 기, 완전문장, 영문, 기타}. 명사/ㅁ음/기 = 개조식(is_gaejo=True),
    완전문장 = 비개조식(변환 필요), 영문 = 한글 없음(변환 대상 아님).
    """
    r = classify_ending(text)
    return {
        "ending": r.ending,
        "is_gaejo": r.is_gaejo,
        "final_form": r.final_form,
        "final_tag": r.final_tag,
        "n_words": r.n_words,
        "has_korean": r.has_korean,
    }


@mcp.tool()
def score(text: str, max_words: int = 12) -> dict:
    """블록(여러 줄) 텍스트의 개조식 준수도를 채점한다.

    개조식 종결 비율, 완전문장 잔존 수, 줄 길이, 종결 양식 분포, 경고를 반환한다.
    한 줄씩 줄바꿈(\\n)으로 구분해 넣는다.
    """
    return score_text(text, max_words=max_words).as_dict()


@mcp.tool()
def check(original: str, output: str, max_words: int = 12) -> dict:
    """변환 자기검증 — 에이전트가 자기 변환본을 검수·수정할 때 쓰는 핵심 도구.

    개조식 준수(스타일)와 의미 보존(원문 대비 수치·전문용어·헤지어)을 함께 보고,
    고쳐야 할 점을 issues로 돌려준다. ok=True면 통과, 아니면 issues를 반영해 다시 변환.
    """
    rep = score_text(output, max_words=max_words).as_dict()
    ret = content_retention(original, output)

    issues: list[str] = []
    fulls = [ln["text"] for ln in rep["lines"] if ln["ending"] == "완전문장"]
    if fulls:
        issues.append(f"완전문장 종결 {len(fulls)}줄 — 명사/명사형(-ㅁ/음)으로 변환: {fulls}")
    others = [ln["text"] for ln in rep["lines"] if ln["ending"] == "기타"]
    if others:
        issues.append(f"종결 불명확 {len(others)}줄(조사 종결/용언 노출): {others}")
    if (rep["ending_dist"].get("기") or 0) > 0:
        issues.append("'-기' 종결 사용 — 코퍼스 미사용 양식, 명사/-ㅁ음 권장")
    nmiss = ret["numbers"]["missing"]
    if nmiss:
        issues.append(f"수치 누락: {nmiss} — 원문 수치를 보존하라")
    tmiss = ret["terms"]["missing"]
    if tmiss:
        issues.append(f"전문용어 누락: {tmiss} — 영어 원어를 보존하라")
    hmiss = ret["hedges"]["missing_categories"]
    if hmiss:
        issues.append(f"뉘앙스 누락 범주: {hmiss}(근사/역접/강조/가능성) — 해당 뉘앙스를 살려라")

    ok = not issues  # 지적사항이 하나도 없을 때만 통과
    return {
        "ok": ok,
        "gaejo_ending_ratio": rep["korean_gaejo_ratio"],
        "full_sentences": rep["full_sentence_count"],
        "content_retention": ret["content_retention"],
        "issues": issues,
    }


def main() -> None:
    """stdio MCP 서버 실행 엔트리포인트(`gaejo-mcp`)."""
    mcp.run()


if __name__ == "__main__":
    main()
