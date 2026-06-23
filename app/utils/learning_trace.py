"""Session-local learning trace utilities for the AI study companion."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Mapping

import streamlit as st


TRACE_KEY = "ai_pet_learning_trace"


DEFAULT_LEARNING_STATE: dict[str, Any] = {
    "current_soc": "未选择",
    "sample_prepared": False,
    "sensors_ready": False,
    "leak_test_done": False,
    "nitrogen_replacement_done": False,
    "t2_100_reached": False,
    "sample_t2_100_done": False,
    "vented": False,
    "sample_venting_done": False,
    "thermal_runaway_triggered": False,
    "temperature_peak_reached": False,
    "sample_temperature_peak_done": False,
    "pressure_stable_or_finished": False,
    "sample_pressure_stable_done": False,
    "gc_finished": False,
    "lfl_mix_finished": False,
    "report_generated": False,
}


DEFAULT_TRACE: dict[str, Any] = {
    "operation_events": [],
    "qa_events": [],
    "warning_events": [],
    "learning_state": deepcopy(DEFAULT_LEARNING_STATE),
}


ACTION_STATE_MAP = {
    "select_soc": ("current_soc", None),
    "load_battery": ("sample_prepared", True),
    "load_prismatic_cell": ("sample_prepared", True),
    "place_thermocouples": ("sensors_ready", True),
    "connect_voltage_leads": ("sensors_ready", True),
    "check_pressure_sensor": ("sensors_ready", True),
    "start_leak_test": ("leak_test_done", True),
    "fill_nitrogen": ("nitrogen_replacement_done", True),
    "complete_replacement_cycle": ("nitrogen_replacement_done", True),
    "observe_t2_100": ("t2_100_reached", True),
    "sample_t2_100": ("sample_t2_100_done", True),
    "observe_venting": ("vented", True),
    "sample_venting": ("sample_venting_done", True),
    "trigger_thermal_runaway": ("thermal_runaway_triggered", True),
    "observe_temperature_peak": ("temperature_peak_reached", True),
    "sample_temperature_peak": ("sample_temperature_peak_done", True),
    "observe_pressure_stable": ("pressure_stable_or_finished", True),
    "sample_pressure_stable": ("sample_pressure_stable_done", True),
    "finish_gc": ("gc_finished", True),
    "calculate_lel": ("lfl_mix_finished", True),
    "evaluate_lel_risk": ("lfl_mix_finished", True),
    "generate_report": ("report_generated", True),
}


def new_trace() -> dict[str, Any]:
    return deepcopy(DEFAULT_TRACE)


def ensure_trace(trace: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if trace is None:
        return new_trace()
    if isinstance(trace, dict):
        trace.setdefault("operation_events", [])
        trace.setdefault("qa_events", [])
        trace.setdefault("warning_events", [])
        trace.setdefault("learning_state", {})
        if not isinstance(trace["operation_events"], list):
            trace["operation_events"] = []
        if not isinstance(trace["qa_events"], list):
            trace["qa_events"] = []
        if not isinstance(trace["warning_events"], list):
            trace["warning_events"] = []
        if not isinstance(trace["learning_state"], dict):
            trace["learning_state"] = {}
        normalized_state = deepcopy(DEFAULT_LEARNING_STATE)
        normalized_state.update(trace["learning_state"])
        trace["learning_state"] = normalized_state
        return trace

    merged = new_trace()
    for key in ("operation_events", "qa_events", "warning_events"):
        value = trace.get(key, [])
        merged[key] = list(value) if isinstance(value, list) else []
    state = trace.get("learning_state", {})
    if isinstance(state, Mapping):
        merged["learning_state"].update(dict(state))
    return merged


def get_learning_trace() -> dict[str, Any]:
    st.session_state.setdefault(TRACE_KEY, new_trace())
    st.session_state[TRACE_KEY] = ensure_trace(st.session_state[TRACE_KEY])
    return st.session_state[TRACE_KEY]


def reset_learning_trace() -> None:
    st.session_state[TRACE_KEY] = new_trace()


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _stage(state: Mapping[str, Any] | None) -> str:
    return str((state or {}).get("current_state", "未记录"))


def _soc(state: Mapping[str, Any] | None) -> str:
    value = (state or {}).get("selected_soc", "未选择")
    return "未选择" if value is None or value == "" else str(value)


def update_learning_state_from_experiment(
    trace: dict[str, Any],
    experiment_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    trace = ensure_trace(trace)
    state = experiment_state or {}
    sampled = state.get("sampling_completed", {}) if isinstance(state.get("sampling_completed"), Mapping) else {}
    learning_state = trace["learning_state"]
    learning_state.update(
        {
            "current_soc": _soc(state),
            "sample_prepared": bool(state.get("battery_loaded") or state.get("cell_loaded")),
            "sensors_ready": bool(
                state.get("thermocouples_placed")
                or state.get("voltage_leads_connected")
                or state.get("pressure_sensor_checked")
            ),
            "leak_test_done": bool(state.get("leak_test_passed") or state.get("chamber_door_closed")),
            "nitrogen_replacement_done": bool(state.get("nitrogen_filled") or int(state.get("replacement_count", 0) or 0) >= 3),
            "t2_100_reached": bool(state.get("t2_reached_100") or sampled.get("t2_100")),
            "sample_t2_100_done": bool(sampled.get("t2_100")),
            "vented": bool(state.get("venting_detected") or sampled.get("venting")),
            "sample_venting_done": bool(sampled.get("venting")),
            "thermal_runaway_triggered": bool(state.get("thermal_runaway_triggered") or state.get("current_state") == "thermal_runaway"),
            "temperature_peak_reached": bool(state.get("temperature_peak_reached") or sampled.get("temperature_peak")),
            "sample_temperature_peak_done": bool(sampled.get("temperature_peak")),
            "pressure_stable_or_finished": bool(state.get("pressure_stable") or sampled.get("pressure_stable")),
            "sample_pressure_stable_done": bool(sampled.get("pressure_stable")),
            "gc_finished": bool(state.get("gc_finished")),
            "lfl_mix_finished": bool(state.get("lel_calculated") or state.get("lel_risk_evaluated")),
            "report_generated": bool(state.get("report_generated") or state.get("current_state") == "report_generated"),
        }
    )
    return trace


def record_operation(
    *,
    page_name: str,
    action_type: str,
    action_name: str,
    experiment_state: Mapping[str, Any] | None = None,
    ok: bool = True,
    error_category: str = "",
    warning_id: str = "",
    corrected: bool = False,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace = get_learning_trace() if trace is None else ensure_trace(trace)
    update_learning_state_from_experiment(trace, experiment_state)
    mapped = ACTION_STATE_MAP.get(action_name)
    if ok and mapped:
        key, value = mapped
        if key == "current_soc":
            trace["learning_state"][key] = _soc(experiment_state)
        else:
            trace["learning_state"][key] = value
    event = {
        "timestamp": _timestamp(),
        "page_name": page_name,
        "current_soc": _soc(experiment_state),
        "current_stage": _stage(experiment_state),
        "action_type": action_type,
        "action_name": action_name,
        "is_flow_compliant": bool(ok),
        "error_category": error_category,
        "warning_id": warning_id,
        "corrected_later": bool(corrected),
    }
    trace["operation_events"].append(event)
    return trace


def classify_question(question: str) -> tuple[str, bool, bool]:
    text = question.lower()
    safety_terms = ("报警", "安全", "消防", "处置", "防爆", "工程", "真实", "lfl", "热失控")
    experiment_terms = (
        "soc",
        "采样",
        "喷阀",
        "t2",
        "100",
        "gc",
        "lfl",
        "报告",
        "气体",
        "h2",
        "co2",
        "co",
        "热失控",
    )
    if "lfl" in text or "防爆" in text:
        category = "LFL_mix与模型边界"
    elif "0%" in text or "喷阀" in text:
        category = "SOC与喷阀"
    elif "采样" in text or "t2" in text or "100" in text:
        category = "采样节点"
    elif "报警" in text:
        category = "报警解释"
    elif "报告" in text:
        category = "报告与数据来源"
    elif any(term in text for term in ("消防", "处置", "真实", "工程")):
        category = "安全边界"
    else:
        category = "实验问答" if any(term in text for term in experiment_terms) else "其他"
    return category, any(term in text for term in experiment_terms), any(term in text for term in safety_terms)


def record_qa(
    *,
    question: str,
    answer: str,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace = get_learning_trace() if trace is None else ensure_trace(trace)
    category, experiment_related, safety_related = classify_question(question)
    event = {
        "timestamp": _timestamp(),
        "question": question,
        "answer_summary": str(answer).strip().replace("\n", " ")[:180],
        "question_category": category,
        "is_experiment_related": experiment_related,
        "is_safety_boundary_related": safety_related,
        "triggered_insufficient_info": "资料不足" in answer or "不能可靠回答" in answer,
    }
    trace["qa_events"].append(event)
    return trace


def record_warning(
    *,
    warning: Mapping[str, Any],
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace = get_learning_trace() if trace is None else ensure_trace(trace)
    event = {
        "timestamp": _timestamp(),
        "warning_category": str(warning.get("category", "流程提醒")),
        "reason": str(warning.get("reason", warning.get("message", ""))),
        "impact": str(warning.get("impact", warning.get("consequence", ""))),
        "correct_action": str(warning.get("correct_action", warning.get("correction", ""))),
        "basis": str(warning.get("basis", "虚拟仿真教学流程约束")),
        "corrected_by_user": bool(warning.get("corrected_by_user", False)),
    }
    if not any(existing.get("reason") == event["reason"] and existing.get("warning_category") == event["warning_category"] for existing in trace["warning_events"]):
        trace["warning_events"].append(event)
    return trace


def sync_warnings_from_assessment(
    trace: dict[str, Any],
    assessment: Mapping[str, Any] | None,
) -> dict[str, Any]:
    trace = ensure_trace(trace)
    if not assessment:
        return trace
    for key in ("last_alert", "latest_severe_warning", "latest_violation"):
        value = assessment.get(key)
        if isinstance(value, Mapping) and value.get("reason"):
            record_warning(warning=value, trace=trace)
    for item in assessment.get("deductions", []) or []:
        if isinstance(item, Mapping) and item.get("reason"):
            record_warning(warning=item, trace=trace)
    return trace


def export_learning_trace_json(trace: Mapping[str, Any] | None = None) -> str:
    data = ensure_trace(trace or get_learning_trace())
    return json.dumps(data, ensure_ascii=False, indent=2)
