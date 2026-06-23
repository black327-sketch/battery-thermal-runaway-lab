"""Load and render staged reaction mechanisms for the virtual lab.

The source of equations is ``docs/阶段方程式.json``. This module only maps
existing project states and actions to that file, and does not invent new
reaction equations.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MECHANISM_PATH = PROJECT_ROOT / "docs" / "阶段方程式.json"


ACTION_TRIGGER_MAP: dict[str, str] = {
    "select_soc": "soc_selected",
    "load_battery": "battery_loaded",
    "close_arc_door": "chamber_closed",
    "start_leak_test": "leak_test_completed",
    "open_vacuum_valve": "vacuum_started",
    "start_vacuum_pump": "vacuum_completed",
    "open_nitrogen_valve": "nitrogen_valve_open",
    "close_nitrogen_valve": "nitrogen_purge_completed",
    "complete_replacement_cycle": "nitrogen_purge_completed",
    "start_arc": "arc_heating_started",
    "finish_arc_heating": "sei_decomposition",
    "trigger_thermal_runaway": "thermal_runaway",
    "finish_cooling": "cooling",
    "connect_gas_bag": "sampling",
    "open_sampling_valve": "sampling_valve_open",
    "close_sampling_valve": "sampling_completed",
    "start_gc": "gc_analysis",
    "finish_gc": "ms_analysis",
    "calculate_gas_volume": "computer_analysis",
    "calculate_lel": "lfl_calculation",
    "generate_report": "report_generation",
    "evaluate_lel_risk": "risk_assessment",
}

STATE_TRIGGER_MAP: dict[str, str] = {
    "sample_preparation": "initial",
    "battery_loaded": "battery_loaded",
    "leak_test": "leak_test_completed",
    "vacuuming": "vacuum_started",
    "nitrogen_filling": "nitrogen_filling",
    "atmosphere_replacement": "nitrogen_purge_completed",
    "arc_ready": "nitrogen_purge_completed",
    "arc_heating": "arc_heating_started",
    "thermal_runaway": "thermal_runaway",
    "cooling": "cooling",
    "gas_sampling": "sampling_valve_open",
    "gc_analysis": "gc_analysis",
    "gas_volume_calculation": "computer_analysis",
    "lel_risk_evaluation": "lfl_calculation",
    "report_generated": "report_generation",
    "soc_selection": "initial",
    "cell_loaded": "battery_loaded",
    "sensors_placed": "battery_loaded",
    "chamber_closed": "chamber_closed",
    "heating": "arc_heating_started",
    "t2_100": "sei_decomposition",
    "venting": "thermal_runaway",
    "temperature_peak": "thermal_runaway",
    "pressure_stable": "cooling",
    "sampling_complete": "sampling_completed",
}


@lru_cache(maxsize=1)
def load_mechanism_data(path: str | Path | None = None) -> dict[str, Any]:
    """Load staged mechanisms from the project JSON file."""

    source = Path(path) if path else MECHANISM_PATH
    with source.open("r", encoding="utf-8") as f:
        return json.load(f)


def _stage_by_id(data: Mapping[str, Any], stage_id: str) -> dict[str, Any] | None:
    for stage in data.get("stages", []) or []:
        if isinstance(stage, Mapping) and stage.get("id") == stage_id:
            return dict(stage)
    return None


def mechanism_for_trigger(trigger: str | None) -> dict[str, Any]:
    """Return mechanism stage for an interaction trigger."""

    data = load_mechanism_data()
    mapping = data.get("interaction_mapping", {}) or {}
    stage_id = mapping.get(trigger or "initial")
    stage = _stage_by_id(data, str(stage_id)) if stage_id else None
    if stage:
        return stage
    fallback = dict(data.get("fallback", {}) or {})
    fallback.setdefault("title", "当前交互阶段")
    fallback.setdefault("display_message", "当前阶段以装置操作和数据采集为主，未触发新的化学反应方程式。")
    fallback.setdefault("equations", [])
    fallback.setdefault("main_gases", [])
    fallback.setdefault("teaching_focus", [])
    return fallback


def mechanism_for_state(state: Mapping[str, Any] | str | None) -> dict[str, Any]:
    """Return mechanism stage for a lab state mapping or state key."""

    if isinstance(state, Mapping):
        state_key = str(state.get("current_state", "sample_preparation"))
    elif state:
        state_key = str(state)
    else:
        state_key = "sample_preparation"
    return mechanism_for_trigger(STATE_TRIGGER_MAP.get(state_key, state_key))


def mechanism_for_action(action: str, ok: bool = True) -> dict[str, Any]:
    """Return mechanism stage after an action, with natural text for failed actions."""

    if not ok:
        return {
            "title": "流程未更新",
            "category": "流程提示",
            "mechanism_summary": "当前操作不符合实验流程，未更新反应机理。",
            "equations": [],
            "main_gases": [],
            "display_message": "当前操作不符合实验流程，未更新反应机理。",
            "teaching_focus": ["按右侧实验步骤完成前置条件后再继续操作。"],
            "report_text": "该次操作未通过流程校验，未计入阶段反应机理记录。",
        }
    return mechanism_for_trigger(ACTION_TRIGGER_MAP.get(action, action))


def format_mechanism_markdown(stage: Mapping[str, Any], *, max_equations: int = 3) -> str:
    """Format one mechanism stage as compact Markdown."""

    title = str(stage.get("title", "当前交互阶段"))
    summary = str(stage.get("mechanism_summary") or stage.get("display_message") or "")
    equations = list(stage.get("equations", []) or [])[:max_equations]
    gases = list(stage.get("main_gases", []) or [])
    focus = list(stage.get("teaching_focus", []) or [])
    parts = [f"**当前阶段：{title}**", summary]
    if equations:
        parts.append("**主要反应方程式**")
        for item in equations:
            if isinstance(item, Mapping):
                reaction = item.get("reaction", "")
                description = item.get("description", "")
                parts.append(f"- `{reaction}`：{description}")
            else:
                parts.append(f"- `{item}`")
    else:
        parts.append("当前阶段以装置操作和数据采集为主，未触发新的化学反应方程式。")
    if gases:
        parts.append("**主要产气物种：**" + "、".join(str(gas) for gas in gases))
    if focus:
        parts.append("**教学提示：**" + "；".join(str(item) for item in focus[:3]))
    return "\n\n".join(parts)


def collect_completed_mechanisms(state: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Collect report-ready mechanisms from completed interactive states."""

    state = state or {}
    ordered: list[tuple[str, bool]] = [
        ("soc_selected", bool(state.get("selected_soc"))),
        ("battery_loaded", bool(state.get("battery_loaded") or state.get("cell_loaded"))),
        ("chamber_closed", bool(state.get("arc_door_closed") or state.get("chamber_door_closed"))),
        ("leak_test_completed", bool(state.get("leak_test_passed"))),
        ("nitrogen_purge_completed", int(state.get("replacement_count", 0) or 0) >= 3 or bool(state.get("nitrogen_filled"))),
        ("arc_heating_started", state.get("current_state") in {"arc_heating", "thermal_runaway", "cooling", "gas_sampling", "gc_analysis", "gas_volume_calculation", "lel_risk_evaluation", "report_generated", "heating", "t2_100", "venting", "temperature_peak", "pressure_stable"}),
        ("thermal_runaway", state.get("current_state") in {"thermal_runaway", "cooling", "gas_sampling", "gc_analysis", "gas_volume_calculation", "lel_risk_evaluation", "report_generated", "venting", "temperature_peak", "pressure_stable"}),
        ("sampling_completed", bool(state.get("gas_bag_filled")) or all((state.get("sampling_completed", {}) or {}).values())),
        ("gc_analysis", bool(state.get("gc_finished"))),
        ("lfl_calculation", bool(state.get("lel_calculated") or state.get("lel_risk_evaluated"))),
        ("risk_assessment", bool(state.get("lel_calculated") or state.get("lel_risk_evaluated"))),
    ]
    seen: set[str] = set()
    stages: list[dict[str, Any]] = []
    for trigger, done in ordered:
        if not done:
            continue
        stage = mechanism_for_trigger(trigger)
        sid = str(stage.get("id", stage.get("title", trigger)))
        if sid not in seen:
            seen.add(sid)
            stages.append(stage)
    return stages or [mechanism_for_state(state)]
