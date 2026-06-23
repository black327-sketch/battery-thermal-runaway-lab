"""Optional external LLM supplement for learning evaluation.

Default behavior is fully offline. This module never sends data unless
ENABLE_EXTERNAL_LLM_EVALUATION=true and OpenAI-compatible LLM settings are
present.
"""

from __future__ import annotations

import os
from typing import Any, Mapping


def is_external_llm_enabled(env: Mapping[str, str] | None = None) -> bool:
    env = env or os.environ
    return (
        str(env.get("ENABLE_EXTERNAL_LLM_EVALUATION", "")).lower() == "true"
        and bool(env.get("LLM_API_KEY"))
        and bool(env.get("LLM_BASE_URL"))
        and bool(env.get("LLM_MODEL"))
    )


def build_anonymized_summary(evaluation: Mapping[str, Any], *, max_items: int = 6) -> dict[str, Any]:
    metrics = dict(evaluation.get("metrics", {}))
    return {
        "metrics": {
            "total_operations": metrics.get("total_operations", 0),
            "valid_operations": metrics.get("valid_operations", 0),
            "warning_count": metrics.get("warning_count", 0),
            "sampling_done": metrics.get("sampling_done", 0),
            "sampling_total": metrics.get("sampling_total", 4),
            "qa_count": metrics.get("qa_count", 0),
            "experiment_qa_count": metrics.get("experiment_qa_count", 0),
            "safety_qa_count": metrics.get("safety_qa_count", 0),
            "gc_finished": metrics.get("gc_finished", False),
            "lfl_mix_finished": metrics.get("lfl_mix_finished", False),
            "report_generated": metrics.get("report_generated", False),
        },
        "levels": dict(evaluation.get("levels", {})),
        "suggestion_categories": list(evaluation.get("suggestions", []))[:max_items],
        "privacy_note": "This summary excludes raw questions, full answers, personal data, and full operation logs.",
    }


def get_external_llm_supplement(
    evaluation: Mapping[str, Any],
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return optional LLM supplement metadata.

    The project intentionally keeps network use disabled by default. To avoid
    adding dependencies or hidden network calls, this adapter exposes the
    privacy-preserving payload and a status object. A future integration can
    call a provider here without changing the local rule evaluation.
    """

    env = env or os.environ
    if not is_external_llm_enabled(env):
        return {
            "enabled": False,
            "used": False,
            "status": "disabled",
            "message": "当前评价基于本地规则。",
            "anonymized_summary": build_anonymized_summary(evaluation),
            "supplement": "",
        }
    if not env.get("LLM_MODEL"):
        return {
            "enabled": True,
            "used": False,
            "status": "fallback",
            "message": "外接大模型未配置模型名称，已回退本地规则评价。",
            "anonymized_summary": build_anonymized_summary(evaluation),
            "supplement": "",
        }
    return {
        "enabled": True,
        "used": False,
        "status": "not_called",
        "message": "外接大模型接口已预留但默认不联网；当前仍使用本地规则评价。",
        "anonymized_summary": build_anonymized_summary(evaluation),
        "supplement": "",
    }
