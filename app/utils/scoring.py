"""教学实验评分工具。"""

from __future__ import annotations


CRITICAL_ACTIONS = {
    "start_arc_without_replacement",
    "sample_before_cooling",
    "skip_leak_test",
}


def score_action(action: str, success: bool, severity: str = "normal") -> int:
    """返回单次操作的分值变化。成功操作不加分，错误操作扣分。"""
    if success:
        return 0
    if action == "start_arc" and severity == "replacement":
        return -10
    if action == "open_sampling_valve" and severity == "cooling":
        return -10
    if action == "open_vacuum_valve" and severity == "leak_test":
        return -10
    if severity == "critical":
        return -8
    return -3


def calculate_final_score(experiment_state: dict) -> dict:
    """汇总最终评分、错误次数、关键错误和完成度。"""
    logs = experiment_state.get("operation_logs", [])
    errors = [log for log in logs if log.get("level") == "error"]
    critical_errors = [
        log for log in errors if log.get("severity") in {"critical", "replacement", "cooling", "leak_test"}
    ]
    ordered_states = [
        "sample_preparation",
        "battery_loaded",
        "leak_test",
        "vacuuming",
        "nitrogen_filling",
        "atmosphere_replacement",
        "arc_ready",
        "arc_heating",
        "thermal_runaway",
        "cooling",
        "gas_sampling",
        "gc_analysis",
        "gas_volume_calculation",
        "lel_risk_evaluation",
        "report_generated",
    ]
    current = experiment_state.get("current_state", "sample_preparation")
    completed = ordered_states.index(current) + 1 if current in ordered_states else 1
    return {
        "final_score": max(0, int(experiment_state.get("score", 100))),
        "error_count": int(experiment_state.get("error_count", len(errors))),
        "critical_errors": critical_errors,
        "completion_pct": round(completed / len(ordered_states) * 100, 1),
    }
