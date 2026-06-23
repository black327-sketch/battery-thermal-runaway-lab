"""Reusable Streamlit workbench panels for the 2D interactive lab."""

from __future__ import annotations

import streamlit as st

from app.utils.immersive_lab import (
    LabActionGroup,
    render_action_groups,
    render_safety_overlay,
    render_score_overlay,
)
from app.utils.lab_canvas import render_canvas_toolbar, render_svg_canvas
from app.utils.lab_fullscreen import render_fullscreen_bridge
from app.utils.reaction_mechanism import format_mechanism_markdown, mechanism_for_state
from app.utils.ui_components import render_instrument_panel, render_logbook, render_monitor_screen, state_label


def render_realtime_panel(state: dict, summary: dict, *, mode: str = "arc") -> None:
    """Render a dense realtime data panel for the workbench lower-left area."""

    sampled = state.get("sampling_completed", {}) or {}
    if mode == "literature":
        sample_progress = f"{sum(1 for value in sampled.values() if value)}/4"
        t2 = float(state.get("temperature_t2_c", 25.0) or 25.0)
        pressure = float(state.get("pressure_kpa", 101.3) or 101.3)
        voltage = state.get("voltage_v", "教学读数")
        soc = state.get("selected_soc", "--")
    else:
        sample_progress = "1/1" if state.get("gas_bag_filled") else ("进行中" if state.get("sampling_valve_open") else "待采样")
        t2 = float(state.get("temperature", 25.0) or 25.0)
        pressure = float(state.get("pressure", 101.3) or 101.3)
        voltage = "已接入" if state.get("battery_loaded") else "待接入"
        soc = state.get("selected_soc", "--")

    rows = [
        ("T1", f"{max(24.0, t2 - 5):.1f} C"),
        ("T2", f"{t2:.1f} C"),
        ("T3", f"{max(24.0, t2 - 9):.1f} C"),
        ("电压", str(voltage)),
        ("压力", f"{pressure:.1f} kPa"),
        ("采样进度", sample_progress),
        ("SOC", str(soc)),
        ("当前阶段", state_label(str(state.get("current_state", "")))),
        ("热失控状态", "演示中" if state.get("current_state") == "thermal_runaway" else "未触发" if state.get("current_state") in {"sample_preparation", "battery_loaded", "leak_test", "vacuuming", "nitrogen_filling", "atmosphere_replacement", "arc_ready"} else "已进入流程"),
        ("DAQ 数据采集仪状态", "记录中" if summary.get("valid_data", True) else "需复核"),
    ]
    html = "".join(
        f'<div class="workbench-data-row"><span>{label}</span><b>{value}</b></div>'
        for label, value in rows
    )
    st.markdown(
        f"""
<div class="workbench-panel-title">实时数据 / 健康监控</div>
<div class="workbench-data-grid">{html}</div>
""",
        unsafe_allow_html=True,
    )
    render_monitor_screen(
        t2=t2,
        pressure=pressure,
        heating_rate=float(state.get("heating_rate", 0.0) or 0.0),
        gc_done=state.get("gc_finished", False),
    )
    render_logbook(state.get("operation_logs", [])[:5] or [])


def render_sync_mechanism_panel(state: dict) -> None:
    """Render the synchronized mechanism panel for the current ARC state."""

    stage = mechanism_for_state(state)
    st.markdown(
        """
<div class="workbench-panel-title">同步反应机理</div>
<div class="workbench-panel-hint">随当前阶段同步显示主要机理、方程式和教学提示。</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(format_mechanism_markdown(stage), unsafe_allow_html=False)


def render_arc_workbench(
    *,
    state: dict,
    summary: dict,
    svg_markup: str,
    action_groups: list[LabActionGroup],
    action_handler,
    fullscreen: bool,
    title: str,
) -> None:
    """Render the ARC mode as a product-style virtual simulation workbench."""

    render_safety_overlay(summary)
    render_fullscreen_bridge(".block-container")
    left, center, right = st.columns([0.72, 3.1, 0.9], gap="medium")

    with left:
        with st.container(border=True):
            render_score_overlay(summary, state_label(str(state.get("current_state", ""))))
        with st.container(border=True, height=520 if fullscreen else 430):
            render_realtime_panel(state, summary, mode="arc")

    with center:
        render_canvas_toolbar("arc_canvas")
        render_svg_canvas(
            svg_markup,
            title=title,
            key_prefix="arc_canvas",
            height=700 if fullscreen else 520,
        )
        with st.container(border=True):
            render_sync_mechanism_panel(state)

    with right:
        with st.container(border=True, height=760 if fullscreen else 620):
            render_instrument_panel(state, mode="arc", assessment_summary=summary)
            st.markdown('<div class="workbench-panel-title">实验操作台</div>', unsafe_allow_html=True)
            render_action_groups(action_groups, action_handler)
