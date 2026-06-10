"""GAEJO — 한국식 연구 발표 PPT 개조식(箇條式) 어휘 다듬기 하네스."""
from .detector import ENDING_TYPES, EndingResult, classify_ending, is_gaejo
from .evaluator import judge_prompt, objective
from .prompt import RULESET, build_messages
from .score import ComplianceReport, score_text

__version__ = "0.1.0"
__all__ = [
    "classify_ending",
    "is_gaejo",
    "EndingResult",
    "ENDING_TYPES",
    "score_text",
    "ComplianceReport",
    "build_messages",
    "RULESET",
    "objective",
    "judge_prompt",
    "__version__",
]
