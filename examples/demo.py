"""GAEJO 데모 — API 키 없이 판별기·메트릭·프롬프트를 보여준다.

실행:  python examples/demo.py
변환까지 보려면 ANTHROPIC_API_KEY를 설정하고 주석 처리된 부분을 활성화.
"""
from gaejo import classify_ending, score_text
from gaejo.transform import messages_for

SAMPLES = [
    "우리는 제안 모델이 정확도를 4.7%p 정도 끌어올렸습니다.",
    "기존 방법은 데이터가 많이 필요했는데, 저희 방법은 적은 데이터로도 잘 됩니다.",
    "그래서 실시간 처리를 위해서는 모델 경량화가 반드시 필요합니다.",
]


def main():
    print("# 1) 종결 판별 (detector)")
    for s in ["성능 개선함", "노이즈 강건성 확보", "검증하기", "개선했습니다", "Results"]:
        r = classify_ending(s)
        print(f"  {s!r:22} → {r.ending:5} (gaejo={r.is_gaejo})")

    print("\n# 2) 준수도 메트릭 (score)")
    block = "노이즈 강건성 확보\n성능 개선함\n우리는 정확도를 높였습니다"
    rep = score_text(block)
    print(f"  개조식 종결 비율(한글): {rep.korean_gaejo_ratio}  완전문장: {rep.full_sentence_count}")
    print(f"  경고: {rep.warnings}")

    print("\n# 3) 변환 프롬프트 (transform.messages_for) — API 키 불필요")
    msg = messages_for(SAMPLES[0], unit="bullet")
    print(f"  system {len(msg['system'])}자, user {len(msg['user'])}자, model={msg['model']}")

    # --- 실제 변환 (ANTHROPIC_API_KEY 필요) ---
    # from gaejo.transform import transform
    # for s in SAMPLES:
    #     print(f"  {s}\n   → {transform(s)}")


if __name__ == "__main__":
    main()
