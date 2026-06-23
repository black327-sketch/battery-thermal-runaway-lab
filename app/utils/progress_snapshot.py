"""Browser progress snapshot helpers for tablet demos.

Snapshots are intentionally small and do not contain API keys, personal data,
raw logs, or downloadable report contents.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import streamlit as st

from app.utils.experiment_state import INITIAL_EXPERIMENT_STATE


SNAPSHOT_VERSION = 1

_BOOLEAN_FIELDS = {
    "battery_loaded",
    "arc_door_closed",
    "leak_test_passed",
    "gas_bag_filled",
    "gc_finished",
    "gas_volume_calculated",
    "lel_calculated",
    "report_generated",
}

_STATE_BY_STEP = {
    "battery_loaded": "battery_loaded",
    "arc_door_closed": "battery_loaded",
    "leak_test_passed": "leak_test",
    "gas_bag_filled": "gas_sampling",
    "gc_finished": "gc_analysis",
    "gas_volume_calculated": "gas_volume_calculation",
    "lel_calculated": "lel_risk_evaluation",
    "report_generated": "report_generated",
}


def _coerce_soc(value: Any) -> int | None:
    try:
        if value in {"", None}:
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def is_valid_progress_snapshot(snapshot: Mapping[str, Any] | None) -> bool:
    """Return whether a snapshot is the current safe schema."""

    return bool(snapshot and int(snapshot.get("version", 0) or 0) == SNAPSHOT_VERSION)


def apply_progress_snapshot_to_session(snapshot: Mapping[str, Any] | None) -> bool:
    """Restore the minimal experiment state after explicit user confirmation."""

    if not is_valid_progress_snapshot(snapshot):
        return False

    state = deepcopy(INITIAL_EXPERIMENT_STATE)
    soc = _coerce_soc(snapshot.get("soc"))
    if soc is not None:
        state["selected_soc"] = soc

    completed_steps = snapshot.get("completed_steps", [])
    if not isinstance(completed_steps, list):
        completed_steps = []
    for step in completed_steps:
        if step in _BOOLEAN_FIELDS:
            state[step] = True
            state["current_state"] = _STATE_BY_STEP.get(step, state["current_state"])

    stage = str(snapshot.get("stage") or "").strip()
    if stage:
        state["current_state"] = stage

    sampling = snapshot.get("sampling", {})
    if isinstance(sampling, Mapping):
        state["sampling_completed"] = {str(k): bool(v) for k, v in sampling.items()}

    if snapshot.get("gc_done"):
        state["gc_started"] = True
        state["gc_finished"] = True
        state["computer_result_ready"] = True
    if snapshot.get("lfl_done"):
        state["lel_calculated"] = True
        state["gas_volume_calculated"] = True
    if snapshot.get("report_done"):
        state["report_generated"] = True
        state["current_state"] = "report_generated"

    state["operation_logs"] = [
        {
            "time": "恢复",
            "action": "restore_progress_snapshot",
            "message": "已从浏览器本地快照恢复实验进度。",
            "level": "info",
            "severity": "normal",
        }
    ]
    st.session_state["experiment"] = state
    st.session_state["interactive_experiment_last"] = {
        "experiment_state": state,
        "score_summary": {
            "final_score": state.get("score", 100),
            "grade": "恢复快照",
            "error_count": state.get("error_count", 0),
            "completion_pct": 0.0,
            "deductions": [],
        },
    }
    return True
