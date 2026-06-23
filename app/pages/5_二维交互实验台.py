"""
二维交互实验台：热失控产气收集与燃爆风险评价。

本页仅用于虚拟仿真教学演示，不提供真实危险实验操作指导。
页面结构：顶部控制栏 → 左(步骤轴) 中(装置SVG) 右(仪器屏+设备控制) → 底部(监控+记录)
"""

from __future__ import annotations

from pathlib import Path
import sys
import logging

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.components.teaching_ai_widget import render_teaching_ai_widget
from app.utils.learning_trace import record_operation, record_warning
from app.utils.asset_utils import render_asset_image
from app.utils.assessment_engine import (
    assessment_summary,
    record_assessment_event,
    reset_assessment,
)
from app.utils.chart_utils import (
    plot_gc_chromatogram,
    plot_gas_composition_bar,
    plot_heating_rate_curve,
    plot_lel_risk_timeline,
    plot_pressure_curve,
    plot_risk_gauge,
    plot_temperature_curve,
    plot_zeng_key_point_comparison,
    plot_zeng_sampling_timeline,
    plot_zeng_stage_gas_trends,
)
from app.utils.data_loader import load_gas_data
from app.utils.dataset_manager import (
    DATASET_LABELS,
    get_active_dataset_config,
    list_available_datasets,
    load_active_arc_curve,
    load_active_gas_volume_formula,
    load_active_gc_composition,
    load_active_gc_peaks,
    load_active_pressure_curve,
    set_active_dataset,
)
from app.utils.equipment_svg import render_full_workbench_svg
from app.utils.experiment_state import (
    get_experiment_state,
    init_experiment_session_state,
    perform_action,
    reset_experiment,
)
from app.utils.literature_device_svg import render_explosion_chamber_heating_platform_svg
from app.utils.literature_experiment_state import (
    get_literature_experiment_state,
    init_literature_session_state,
    perform_literature_session_action,
    reset_literature_experiment,
)
from app.utils.gas_volume_calculator import calculate_gas_volume_from_params
from app.utils.immersive_lab import (
    LabAction,
    LabActionGroup,
    render_action_groups,
    render_safety_overlay,
    render_score_overlay,
    render_status_strip,
    render_window_header,
)
from app.utils.lab_canvas import render_canvas_toolbar, render_svg_canvas
from app.utils.lab_workbench import render_arc_workbench
from app.utils.lfl_calculator import (
    calculate_lfl_mix,
    load_lfl_constants,
    normalize_flammable_gases,
)
from app.utils.risk_model import calculate_risk_ratio, classify_risk_level, estimate_space_concentration
from app.utils.scoring import calculate_final_score
from app.utils.reaction_mechanism import mechanism_for_action
from app.utils.ui_components import (
    render_current_step_guide,
    render_instrument_panel,
    render_logbook,
    render_metric_card,
    render_model_notice,
    render_monitor_screen,
    render_page_header,
    render_risk_badge,
    render_section_title,
    render_warning_banner,
    state_label,
)
from app.utils.ui_theme import (
    apply_global_style,
    get_current_theme,
    render_global_footer,
    render_theme_toggle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
EXP_DIR = DATA_DIR / "experiment"
LOGGER = logging.getLogger(__name__)

st.set_page_config(page_title="二维交互实验台", page_icon="🔬", layout="wide")
init_experiment_session_state()
init_literature_session_state()
apply_global_style()


def _apply_workbench_fullscreen_chrome() -> None:
    """Hide Streamlit chrome and expand the page for the ARC workbench capture mode."""
    st.markdown(
        """
<style>
[data-testid="stSidebar"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
#MainMenu,
footer {
    display: none !important;
}
.stApp {
    background: var(--app-bg);
}
.block-container {
    max-width: 100vw !important;
    padding: 0.35rem 0.65rem 0.65rem !important;
}
div[data-testid="stVerticalBlock"] {
    gap: 0.45rem;
}
div[data-testid="stHorizontalBlock"] {
    gap: 0.85rem;
}
.immersive-titlebar {
    margin-bottom: 0.45rem;
    padding: 0.55rem 0.7rem;
}
.immersive-status-strip {
    margin: 0.35rem 0 0.45rem;
}
</style>
""",
        unsafe_allow_html=True,
    )


@st.cache_data
def _load_base_assets() -> tuple[pd.DataFrame, dict[str, float]]:
    return (
        load_gas_data(DATA_DIR / "normalized_gas_data.csv"),
        load_lfl_constants(DATA_DIR / "gas_lfl_constants.csv"),
    )


@st.cache_data
def _load_zeng_2026_assets() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        pd.read_csv(EXP_DIR / "literature_zeng_2026_metadata.csv"),
        pd.read_csv(EXP_DIR / "literature_zeng_2026_battery_sample.csv"),
        pd.read_csv(EXP_DIR / "literature_zeng_2026_arc_key_points.csv"),
        pd.read_csv(EXP_DIR / "literature_zeng_2026_gc_composition.csv"),
    )


def _extract_composition(row: pd.Series) -> dict[str, float]:
    composition: dict[str, float] = {}
    for col in row.index:
        if col.endswith("_pct") and col != "SOC_pct":
            try:
                composition[col.replace("_pct", "")] = float(row[col])
            except (TypeError, ValueError):
                continue
    return composition


def _select_sample(gas_df: pd.DataFrame, soc: object) -> pd.Series:
    if soc is not None and "SOC_pct" in gas_df.columns:
        matched = gas_df[gas_df["SOC_pct"].astype(str) == str(soc)]
        if not matched.empty:
            return matched.iloc[0]
    return gas_df.iloc[0]


def _normalize_gc_composition_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or not {"gas_component", "volume_fraction_pct"}.issubset(df.columns):
        return df
    rows = []
    group_cols = ["soc_pct"] if "soc_pct" in df.columns else []
    grouped = df.groupby(group_cols, dropna=False) if group_cols else [("", df)]
    for key, group in grouped:
        row = {"source": "validated_gc_composition", "notes": "已校验 GC 组分表"}
        if group_cols:
            row["SOC_pct"] = key if not isinstance(key, tuple) else key[0]
        for _, item in group.iterrows():
            gas = str(item.get("gas_component", "")).strip()
            if not gas:
                continue
            try:
                row[f"{gas}_pct"] = float(item.get("volume_fraction_pct"))
            except (TypeError, ValueError):
                continue
        rows.append(row)
    return pd.DataFrame(rows)


def _run_lel_calculation(state: dict, gas_df: pd.DataFrame, lfl_dict: dict[str, float]) -> dict:
    sample = _select_sample(gas_df, state.get("selected_soc"))
    composition = _extract_composition(sample)
    flammable = {gas: val for gas, val in composition.items() if gas in lfl_dict}
    lfl_mix = calculate_lfl_mix(flammable, lfl_dict)
    concentration = estimate_space_concentration(20.0, 10.0, 1.0)
    risk_ratio = calculate_risk_ratio(concentration, lfl_mix)
    risk_info = classify_risk_level(risk_ratio)
    result = {
        "sample_info": sample.to_dict(),
        "gas_composition": composition,
        "flammable_composition": flammable,
        "lfl_mix": lfl_mix,
        "space_concentration": concentration,
        "risk_ratio": risk_ratio,
        "risk_info": risk_info,
        "statement": "该 LFL 和 R 值仅用于教学模型，不用于真实工程防爆设计、消防应急或事故预测。",
    }
    st.session_state["interactive_lel_result"] = result
    return result


def _handle_action_result(ok: bool, message: str) -> None:
    """Show stable user feedback and rerun only after successful actions."""
    if ok:
        st.toast(message, icon="✅")
        st.rerun()
    if message:
        st.warning(message)
        st.rerun()


def _record_action_assessment(mode: str, action: str, ok: bool, message: str) -> None:
    """Record detailed assessment without changing the existing state machine."""
    record_assessment_event(mode, action, ok, message)
    st.session_state[f"{mode}_last_mechanism"] = mechanism_for_action(action, ok)
    try:
        summary = assessment_summary(mode)
        state_snapshot = get_literature_experiment_state() if mode == "literature" else get_experiment_state()
        alert = summary.get("last_alert") or summary.get("latest_severe_warning") or summary.get("latest_violation")
        record_operation(
            page_name="二维交互实验台",
            action_type="experiment",
            action_name=action,
            experiment_state=state_snapshot,
            ok=ok,
            error_category=str((alert or {}).get("category", "")) if isinstance(alert, dict) else "",
            warning_id=str((alert or {}).get("action", "")) if isinstance(alert, dict) else "",
        )
        if isinstance(alert, dict) and alert.get("reason"):
            record_warning(warning=alert)
    except Exception:
        LOGGER.debug("Learning trace record skipped for action %s", action, exc_info=True)


def _run_arc_action(action: str, payload: dict | None = None) -> None:
    """Run an ARC action without exposing exceptions to the page."""
    try:
        ok, message = perform_action(action, payload)
    except Exception:
        LOGGER.exception("ARC action failed: %s", action)
        st.warning("操作失败，请检查前置步骤后重试。")
        return
    _record_action_assessment("arc", action, ok, message)
    _handle_action_result(ok, message)


def _run_literature_action(action: str, payload: dict | None = None) -> None:
    """Run a literature-device action without exposing exceptions to the page."""
    try:
        ok, message = perform_literature_session_action(action, payload)
    except Exception:
        LOGGER.exception("Literature action failed: %s", action)
        st.warning("操作失败，请检查文献装置模式的前置步骤后重试。")
        return
    _record_action_assessment("literature", action, ok, message)
    _handle_action_result(ok, message)


def _render_assessment_snapshot(mode: str) -> None:
    """Render compact score, data-validity and consequence status."""
    summary = assessment_summary(mode)
    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("考核分", summary["score"])
    with c2:
        render_metric_card("数据有效性", "有效" if summary["valid_data"] else "需复核")
    with c3:
        render_metric_card("规范状态", summary["safety_status"])


def _render_assessment_panel(mode: str) -> None:
    """Render detailed assessment report for bottom tabs."""
    summary = assessment_summary(mode)
    render_section_title("严格考核记录", f"等级：{summary['grade']} · 当前分数：{summary['score']}")
    if summary["deductions"]:
        st.dataframe(pd.DataFrame(summary["deductions"]), use_container_width=True, hide_index=True)
    else:
        st.info("暂无扣分记录。")
    if summary["consequences"]:
        st.markdown("**后果模拟**")
        for item in summary["consequences"][:6]:
            st.warning(item)
    st.markdown("**学习建议**")
    for suggestion in summary["suggestions"]:
        st.markdown(f"- {suggestion}")


def _render_device_task_panel(mode: str, state: dict) -> None:
    """Render the current device-linked task focus."""
    if mode == "literature":
        sampled = state.get("sampling_completed", {}) or {}
        tasks = [
            ("电池区", "选择 SOC、放入方壳 LFP 电池、确认 T1/T2/T3 测点。", bool(state.get("cell_loaded"))),
            ("舱门区", "关闭防爆舱门，确认压力传感器和电压采集线。", bool(state.get("chamber_door_closed"))),
            ("气氛区", "按虚拟流程完成抽真空和氮气置换。", bool(state.get("nitrogen_filled"))),
            ("加热板", "进入教学加热观察，记录阶段状态。", bool(state.get("heating_started"))),
            ("集气袋", "按四个节点完成 T2=100℃、喷阀、温度峰值、压力稳定采样。", all(sampled.values()) if sampled else False),
            ("GC / 可燃风险", "完成 GC 组成查看，再进行 LFL_mix 可燃风险评价。", bool(state.get("lel_risk_evaluated"))),
        ]
    else:
        tasks = [
            ("ARC 腔体", "装入电池、关闭舱门、完成气密性检测。", bool(state.get("leak_test_passed"))),
            ("20 L 罐", "完成抽真空 / 氮气置换循环，避免跳过气氛控制。", int(state.get("replacement_count", 0)) >= 3),
            ("ARC 控制", "启动虚拟升温并进入热失控教学演示。", state.get("current_state") in {"thermal_runaway", "cooling", "gas_sampling", "gc_analysis", "gas_volume_calculation", "lel_risk_evaluation", "report_generated"}),
            ("集气袋", "冷却后连接集气袋并完成采样。", bool(state.get("gas_bag_filled"))),
            ("GC / 可燃风险", "完成 GC、产气量记录和 LFL_mix 可燃风险评价。", bool(state.get("lel_calculated"))),
        ]

    st.markdown("**设备任务面板**")
    for title, desc, done in tasks:
        icon = "✓" if done else "•"
        color = "var(--app-green)" if done else "var(--app-primary-light)"
        st.markdown(
            f"""
<div class="app-card-soft" style="padding:10px 12px;margin-bottom:8px;">
  <div style="font-weight:700;color:{color};">{icon} {title}</div>
  <div style="font-size:0.84rem;line-height:1.55;color:var(--app-text);">{desc}</div>
</div>
""",
            unsafe_allow_html=True,
        )


def _literature_action_groups(state: dict, selected_soc: object) -> list[LabActionGroup]:
    """Build device-grouped actions for the literature immersive panel."""
    sampled = state.get("sampling_completed", {}) or {}
    door_ready = state.get("thermocouples_placed") and state.get("pressure_sensor_checked")
    gc_ready = all(sampled.get(s, False) for s in ["t2_100", "venting", "temperature_peak", "pressure_stable"])
    return [
        LabActionGroup(
            "样品与测点",
            "电池区、热电偶、电压线、压力传感器",
            (
                LabAction("load_prismatic_cell", "放入方壳 LFP 电池", "lit_imm_cell", state.get("cell_loaded")),
                LabAction("place_thermocouples", "确认 T1/T2/T3 测点", "lit_imm_tc", state.get("thermocouples_placed")),
                LabAction("connect_voltage_leads", "连接电压采集线", "lit_imm_volt", state.get("voltage_leads_connected")),
                LabAction("check_pressure_sensor", "检查压力传感器", "lit_imm_press", state.get("pressure_sensor_checked")),
            ),
        ),
        LabActionGroup(
            "舱门与气氛",
            "锁紧、抽真空、氮气置换",
            (
                LabAction("close_chamber_door", "关闭防爆舱门", "lit_imm_door", state.get("chamber_door_closed")),
                LabAction("start_vacuum", "执行虚拟抽真空", "lit_imm_vac", state.get("vacuum_done")),
                LabAction("fill_nitrogen", "完成氮气置换", "lit_imm_n2", state.get("nitrogen_filled")),
            ),
        ),
        LabActionGroup(
            "加热与阶段观察",
            "阶段 I、喷阀、峰值、结束",
            (
                LabAction("start_heating", "启动加热教学演示", "lit_imm_heat", state.get("heating_started"), primary=bool(state.get("nitrogen_filled") and not state.get("heating_started"))),
                LabAction("observe_t2_100", "记录 T2=100℃ 节点", "lit_imm_t2", state.get("t2_reached_100")),
                LabAction("observe_venting", "记录安全阀喷阀", "lit_imm_vent", state.get("venting_detected")),
                LabAction("observe_temperature_peak", "记录热失控温度峰值", "lit_imm_peak", state.get("temperature_peak_reached")),
                LabAction("observe_pressure_stable", "记录压力稳定", "lit_imm_stable", state.get("pressure_stable")),
            ),
        ),
        LabActionGroup(
            "四次气体采样",
            "一采、二采、三采、四采",
            (
                LabAction("sample_t2_100", "一采：T2=100℃", "lit_imm_s1", sampled.get("t2_100")),
                LabAction("sample_venting", "二采：安全阀喷阀", "lit_imm_s2", sampled.get("venting")),
                LabAction("sample_temperature_peak", "三采：温度峰值", "lit_imm_s3", sampled.get("temperature_peak")),
                LabAction("sample_pressure_stable", "四采：压力稳定", "lit_imm_s4", sampled.get("pressure_stable")),
            ),
        ),
        LabActionGroup(
            "GC / LFL / 报告",
            "组成分析、风险解释、报告终端",
            (
                LabAction("start_gc", "启动 GC 分析", "lit_imm_gc", state.get("gc_started"), primary=gc_ready and not state.get("gc_started")),
                LabAction("finish_gc", "完成 GC 分析", "lit_imm_gc_done", state.get("gc_finished")),
                LabAction("view_gas_composition", "查看气体组成", "lit_imm_view_gas", False),
                LabAction("evaluate_lel_risk", "计算 LFL_mix 可燃风险", "lit_imm_lel", state.get("lel_risk_evaluated")),
                LabAction("generate_report", "生成报告摘要", "lit_imm_report", state.get("report_generated"), primary=state.get("lel_risk_evaluated") and not state.get("report_generated")),
                LabAction("reset", "重置文献模式", "lit_imm_reset"),
            ),
        ),
    ]


def _arc_action_groups(state: dict) -> list[LabActionGroup]:
    """Build device-grouped actions for the ARC immersive panel."""
    cycle_ready = (
        state.get("cycle_vacuum_done")
        and state.get("cycle_nitrogen_done")
        and not state.get("vacuum_valve_open")
        and not state.get("nitrogen_valve_open")
    )
    n2_ready = not state.get("vacuum_valve_open") and state.get("cycle_vacuum_done")
    return [
        LabActionGroup(
            "样品与舱门",
            "SOC、装样、关门、气密性",
            (
                LabAction("load_battery", "装入电池", "arc_imm_battery", state.get("battery_loaded")),
                LabAction("close_arc_door", "关闭 ARC 舱门", "arc_imm_door", state.get("arc_door_closed")),
                LabAction("start_leak_test", "执行气密性检测", "arc_imm_leak", state.get("leak_test_passed"), primary=state.get("arc_door_closed") and not state.get("leak_test_passed")),
            ),
        ),
        LabActionGroup(
            "真空与氮气置换",
            "20 L 罐气氛链条",
            (
                LabAction("open_vacuum_valve", "打开真空阀", "arc_imm_vac_valve", state.get("vacuum_valve_open")),
                LabAction("start_vacuum_pump", "启动真空泵", "arc_imm_vac_pump", state.get("cycle_vacuum_done")),
                LabAction("close_vacuum_valve", "关闭真空阀", "arc_imm_close_vac", not state.get("vacuum_valve_open")),
                LabAction("open_nitrogen_valve", "打开氮气阀", "arc_imm_n2", state.get("nitrogen_valve_open")),
                LabAction("close_nitrogen_valve", "关闭氮气阀", "arc_imm_close_n2", not state.get("nitrogen_valve_open")),
                LabAction("complete_replacement_cycle", "完成本轮置换", "arc_imm_cycle", not cycle_ready),
            ),
        ),
        LabActionGroup(
            "热失控演示",
            "虚拟升温、热失控、冷却",
            (
                LabAction("start_arc", "启动 ARC 虚拟升温", "arc_imm_start", state.get("current_state") in {"arc_heating", "thermal_runaway", "cooling", "gas_sampling", "gc_analysis", "gas_volume_calculation", "lel_risk_evaluation", "report_generated"}, primary=state.get("current_state") == "arc_ready"),
                LabAction("finish_arc_heating", "完成升温阶段", "arc_imm_heat_done", False),
                LabAction("trigger_thermal_runaway", "进入热失控演示", "arc_imm_runaway", state.get("current_state") == "thermal_runaway"),
                LabAction("finish_cooling", "完成冷却", "arc_imm_cool", state.get("current_state") in {"cooling", "gas_sampling", "gc_analysis", "gas_volume_calculation", "lel_risk_evaluation", "report_generated"}),
            ),
        ),
        LabActionGroup(
            "采样与分析",
            "集气袋、GC、LFL、报告",
            (
                LabAction("connect_gas_bag", "连接集气袋", "arc_imm_bag", state.get("gas_bag_connected")),
                LabAction("open_sampling_valve", "打开采样阀", "arc_imm_sampling", state.get("sampling_valve_open")),
                LabAction("close_sampling_valve", "关闭采样阀并完成采样", "arc_imm_close_sampling", not state.get("sampling_valve_open")),
                LabAction("start_gc", "启动 GC", "arc_imm_gc", state.get("gc_started")),
                LabAction("finish_gc", "完成 GC", "arc_imm_gc_done", state.get("gc_finished")),
                LabAction("calculate_gas_volume", "记录产气量", "arc_imm_gas_vol", state.get("gas_volume_calculated")),
                LabAction("calculate_lel", "计算 LFL_mix 可燃风险", "arc_imm_lel", state.get("lel_calculated")),
                LabAction("generate_report", "生成报告摘要", "arc_imm_report", state.get("current_state") == "report_generated", primary=state.get("lel_calculated") and state.get("current_state") != "report_generated"),
                LabAction("reset", "重置实验", "arc_imm_reset"),
            ),
        ),
    ]


def _handle_literature_immersive_action(action: str, payload: dict | None = None) -> None:
    """Dispatch literature actions from the immersive operation panel."""
    if action == "reset":
        reset_literature_experiment()
        reset_assessment("literature")
        st.rerun()
    if action == "generate_report":
        try:
            ok, msg = perform_literature_session_action("generate_report")
        except Exception:
            LOGGER.exception("Literature report action failed")
            st.warning("报告生成失败，请检查前置步骤后重试。")
            ok, msg = False, ""
        _record_action_assessment("literature", "generate_report", ok, msg)
        if ok:
            st.session_state["interactive_experiment_last"] = {
                "experiment_state": get_literature_experiment_state().copy(),
                "score_summary": {
                    "final_score": get_literature_experiment_state().get("score", 100),
                    "error_count": get_literature_experiment_state().get("error_count", 0),
                    "completion_pct": 100.0,
                },
                "active_dataset": get_active_dataset_config(),
            }
        _handle_action_result(ok, msg)
        return
    _run_literature_action(action, payload)


def _handle_arc_immersive_action(
    action: str,
    payload: dict | None = None,
    *,
    gas_df_for_lel: pd.DataFrame | None = None,
    lfl_dict_for_lel: dict[str, float] | None = None,
    gas_volume_formula: pd.DataFrame | None = None,
    dataset_config_for_report: dict | None = None,
) -> None:
    """Dispatch ARC actions from the immersive operation panel."""
    if action == "reset":
        reset_experiment()
        reset_assessment("arc")
        st.rerun()
    if action == "calculate_gas_volume":
        try:
            ok, msg = perform_action("calculate_gas_volume")
            if ok and gas_volume_formula is not None and not gas_volume_formula.empty:
                st.session_state["interactive_gas_volume"] = calculate_gas_volume_from_params(
                    {"validated_rows": len(gas_volume_formula)}
                )
        except Exception:
            LOGGER.exception("Gas volume action failed")
            st.warning("产气量记录失败，请检查 GC 是否已完成。")
            ok, msg = False, ""
        _record_action_assessment("arc", "calculate_gas_volume", ok, msg)
        _handle_action_result(ok, msg)
        return
    if action == "calculate_lel":
        try:
            ok, msg = perform_action("calculate_lel")
            if ok and gas_df_for_lel is not None and lfl_dict_for_lel is not None:
                _run_lel_calculation(get_experiment_state(), gas_df_for_lel, lfl_dict_for_lel)
        except Exception:
            LOGGER.exception("LFL action failed")
            st.warning("可燃风险评价失败，请检查产气量记录和气体组成数据。")
            ok, msg = False, ""
        _record_action_assessment("arc", "calculate_lel", ok, msg)
        _handle_action_result(ok, msg)
        return
    if action == "generate_report":
        try:
            ok, msg = perform_action("generate_report")
        except Exception:
            LOGGER.exception("ARC report action failed")
            st.warning("报告生成失败，请检查可燃风险评价是否已完成。")
            ok, msg = False, ""
        _record_action_assessment("arc", "generate_report", ok, msg)
        if ok:
            st.session_state["interactive_experiment_last"] = {
                "experiment_state": get_experiment_state().copy(),
                "score_summary": calculate_final_score(get_experiment_state()),
                "active_dataset": dataset_config_for_report or {},
            }
        _handle_action_result(ok, msg)
        return
    _run_arc_action(action, payload)


def _render_runaway_focus_view(mode: str, state: dict) -> None:
    """Render the thermal-runaway focused teaching view."""
    active_states = {"thermal_runaway", "temperature_peak", "venting"}
    current_state = state.get("current_state", "")
    toggle_key = f"{mode}_manual_runaway_focus"
    auto_focus = current_state in active_states
    focus = st.toggle("热失控专用画面", value=auto_focus or bool(st.session_state.get(toggle_key, False)), key=toggle_key)
    if not (focus or auto_focus):
        return

    st.markdown(
        """
<div class="app-card" style="border-color:var(--app-orange);">
  <h3 style="margin:0 0 8px;color:var(--app-primary);">热失控阶段专用画面</h3>
  <p style="margin:0;color:var(--app-text);line-height:1.65;">
  当前视图突出电池、温度峰值、压力变化、电压跌落、气体释放与采样节点。
  所有数值和状态均为虚拟仿真或教学回放，不用于真实工程、消防应急或事故预测。
  </p>
</div>
""",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("温度读数", f"{float(state.get('temperature_t2_c', state.get('temperature', 25.0))):.1f}", "℃")
    with c2:
        render_metric_card("压力读数", f"{float(state.get('pressure_kpa', state.get('pressure', 101.3))):.1f}", "kPa")
    with c3:
        voltage = state.get("voltage_v", "教学显示")
        render_metric_card("电压状态", voltage)

    stage_df = pd.DataFrame(
        [
            ["阶段 I", "外部加热、自热初期、SEI 膜分解", "关注 T2 变化与第一次采样节点。"],
            ["阶段 II", "喷阀、压力释放、电压下降、内短路和自加速反应", "关注喷阀与温度峰值采样节点。"],
            ["阶段 III", "温度峰值后下降、反应趋于结束、气体扩散", "关注压力稳定和报告中的数据完整性。"],
        ],
        columns=["阶段", "教学关注点", "记录要求"],
    )
    st.dataframe(stage_df, use_container_width=True, hide_index=True)
    mech_cols = st.columns(4)
    items = [
        ("assets/mechanism/02_sei_decomposition.png", "SEI 分解"),
        ("assets/mechanism/03_separator_melting_short_circuit.png", "隔膜熔融 / 内短路"),
        ("assets/mechanism/05_hydrogen_generation_pathway.png", "H₂ 来源"),
        ("assets/mechanism/06_co_co2_generation_pathway.png", "CO / CO₂ 来源"),
    ]
    for col, (path, title) in zip(mech_cols, items):
        with col:
            render_asset_image(path, f"{title} 机理示意，仅用于教学理解。", title)


def _render_mechanism_gallery(mode: str, state: dict) -> None:
    """Render context-aware mechanism illustrations for the current stage."""
    current_state = state.get("current_state", "")
    if mode == "literature":
        if current_state in {"heating", "t2_100", "venting", "temperature_peak", "pressure_stable"}:
            render_asset_image(
                "assets/mechanism/07_venting_gas_cloud.png",
                "文献装置模式气体释放与采集示意图，仅用于教学理解。",
                "产气与采样机理示意",
            )
        if state.get("gc_finished") or state.get("lel_risk_evaluated"):
            c1, c2, c3 = st.columns(3)
            with c1:
                render_asset_image("assets/mechanism/05_hydrogen_generation_pathway.png", "H₂ 生成路径示意，仅用于教学理解。", "H₂ 路径")
            with c2:
                render_asset_image("assets/mechanism/06_co_co2_generation_pathway.png", "CO / CO₂ 生成路径示意，仅用于教学理解。", "CO / CO₂ 路径")
            with c3:
                render_asset_image("assets/mechanism/08_lel_risk_evaluation.png", "LFL_mix 可燃风险解释示意，不作为消防应急判据。", "可燃风险解释")
        return

    if current_state in {"arc_heating", "thermal_runaway"}:
        c1, c2, c3 = st.columns(3)
        with c1:
            render_asset_image("assets/mechanism/02_sei_decomposition.png", "SEI 分解机理示意，仅用于教学理解。", "SEI 分解")
        with c2:
            render_asset_image("assets/mechanism/03_separator_melting_short_circuit.png", "隔膜熔融与短路机理示意，仅用于教学理解。", "隔膜短路")
        with c3:
            render_asset_image("assets/mechanism/04_cathode_oxygen_electrolyte_oxidation.png", "正极释氧 / 电解液氧化示意，仅用于教学理解。", "释氧与氧化")
    elif current_state in {"cooling", "gas_sampling", "gc_analysis"}:
        render_asset_image(
            "assets/mechanism/07_venting_gas_cloud.png",
            "喷阀和气云教学示意，不用于真实泄放或防爆设计。",
            "气云与采样示意",
        )
    elif state.get("lel_calculated"):
        render_asset_image(
            "assets/mechanism/08_lel_risk_evaluation.png",
            "LFL_mix 可燃风险解释示意，不作为真实安全决策依据。",
            "可燃风险解释",
        )


def _render_step_axis(step_defs: list[tuple[str, bool]], *, height: int = 480) -> None:
    """Render a compact scrollable step axis."""
    active_idx = next((i for i, (_, done) in enumerate(step_defs) if not done), len(step_defs) - 1)
    rows = []
    for idx, (label, done) in enumerate(step_defs):
        if done:
            icon, color, weight = "✓", "var(--app-green)", "normal"
        elif idx == active_idx:
            icon, color, weight = "▶", "var(--app-primary-light)", "bold"
        else:
            icon, color, weight = "○", "var(--app-muted)", "normal"
        rows.append(
            f'<div style="display:flex;gap:8px;align-items:center;padding:4px 0;">'
            f'<span style="color:{color};width:18px;text-align:center;flex-shrink:0;">{icon}</span>'
            f'<span style="color:var(--app-text);font-size:0.82rem;font-weight:{weight};">{label}</span>'
            f'</div>'
        )
    st.markdown(
        f"""<div class="immersive-stage-left" style="max-height:{height}px;">
<div style="font-weight:800;font-size:0.92rem;color:var(--app-primary);margin-bottom:8px;">实验流程线</div>
{''.join(rows)}
</div>""",
        unsafe_allow_html=True,
    )


def _render_literature_immersive_window(
    literature_state: dict,
    *,
    selected_soc: object,
    sampled: dict,
    summary: dict,
    zeng_key_df: pd.DataFrame,
    zeng_gc_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
) -> None:
    """Render the literature mode as one immersive lab window."""
    current_state = literature_state.get("current_state", "soc_selection")
    fullscreen = bool(st.session_state.get("literature_canvas_fullscreen", False))
    st.markdown(f'<div class="immersive-shell {"is-fullscreen" if fullscreen else ""}">', unsafe_allow_html=True)
    render_window_header(
        "文献装置沉浸式实验窗口",
        "防爆舱、气氛控制、四次采样、GC 和 LFL_mix 可燃风险评价在同一窗口内完成。",
        fullscreen=fullscreen,
        key_prefix="literature_canvas",
    )
    render_safety_overlay(summary)
    render_status_strip(
        [
            ("SOC", f"{selected_soc if selected_soc is not None else '未选择'}%", "active" if selected_soc is not None else "idle"),
            ("舱门", "已锁紧" if literature_state.get("chamber_door_closed") else "待确认", "done" if literature_state.get("chamber_door_closed") else "active"),
            ("气氛", "N₂" if literature_state.get("nitrogen_filled") else ("真空" if literature_state.get("vacuum_done") else "待置换"), "done" if literature_state.get("nitrogen_filled") else "active"),
            ("采样", f"{sum(1 for v in sampled.values() if v)}/4", "done" if all(sampled.values()) else "active"),
            ("GC", "已完成" if literature_state.get("gc_finished") else "待分析", "done" if literature_state.get("gc_finished") else "active"),
        ]
    )
    left, center, right = st.columns([0.68, 2.58, 0.92], gap="medium")
    with left:
        render_score_overlay(summary, state_label(current_state))
        _render_step_axis(
            [
                ("选择 SOC", bool(selected_soc is not None)),
                ("放入方壳 LFP 电池", literature_state.get("cell_loaded", False)),
                ("布置 T1/T2/T3 热电偶", literature_state.get("thermocouples_placed", False)),
                ("连接电压 / 压力采集", literature_state.get("pressure_sensor_checked", False)),
                ("关闭防爆舱门", literature_state.get("chamber_door_closed", False)),
                ("抽真空", literature_state.get("vacuum_done", False)),
                ("氮气置换", literature_state.get("nitrogen_filled", False)),
                ("启动加热演示", literature_state.get("heating_started", False)),
                ("一采 · T2=100℃", sampled.get("t2_100", False)),
                ("二采 · 安全阀喷阀", sampled.get("venting", False)),
                ("三采 · 温度峰值", sampled.get("temperature_peak", False)),
                ("四采 · 压力稳定", sampled.get("pressure_stable", False)),
                ("GC 气相色谱分析", literature_state.get("gc_finished", False)),
                ("LFL_mix 可燃风险评价", literature_state.get("lel_risk_evaluated", False)),
                ("报告摘要", literature_state.get("report_generated", False)),
            ],
            height=640 if fullscreen else 520,
        )
        render_current_step_guide(current_state)
    with center:
        st.session_state["literature_canvas_runaway_focus"] = current_state in {"venting", "temperature_peak"}
        render_canvas_toolbar("literature_canvas")
        render_svg_canvas(
            render_explosion_chamber_heating_platform_svg({**literature_state, "_assessment_summary": summary}),
            title="文献装置数字孪生画布",
            key_prefix="literature_canvas",
            height=840 if fullscreen else 760,
        )
        _render_runaway_focus_view("literature", literature_state)
    with right:
        with st.container(border=True, height=720 if fullscreen else 640):
            st.markdown("**实验操作台**")
            render_theme_toggle(key="literature_imm_theme_toggle")
            soc_val = st.selectbox(
                "SOC",
                options=[0, 25, 50, 75, 100],
                index=[0, 25, 50, 75, 100].index(selected_soc) if selected_soc in [0, 25, 50, 75, 100] else 4,
                key="lit_imm_soc_select",
            )
            if st.button("确认 SOC", key="lit_imm_soc_confirm", use_container_width=True):
                _handle_literature_immersive_action("select_soc", {"soc": soc_val})
            render_instrument_panel(literature_state, mode="literature", assessment_summary=summary)
            render_action_groups(
                _literature_action_groups(literature_state, selected_soc),
                _handle_literature_immersive_action,
            )
    st.markdown('<div class="immersive-data-zone">', unsafe_allow_html=True)
    with st.expander("实验反馈与数据区", expanded=not fullscreen):
        daq_tab, curve_tab, sample_tab, gc_tab, lel_tab, assess_tab, report_tab = st.tabs(
            ["实时 DAQ 数据采集仪", "曲线", "四次采样", "GC 组分", "LFL 解释", "考核记录", "报告摘要"]
        )
        with daq_tab:
            render_monitor_screen(
                t2=float(literature_state.get("temperature_t2_c", 25.0) or 25.0),
                pressure=float(literature_state.get("pressure_kpa", 101.3) or 101.3),
                gc_done=literature_state.get("gc_finished", False),
            )
            render_logbook(literature_state.get("operation_logs", []) or [])
        with curve_tab:
            st.plotly_chart(plot_zeng_sampling_timeline(zeng_key_df, selected_soc if selected_soc is not None else 100, theme_mode), use_container_width=True)
            st.plotly_chart(plot_zeng_key_point_comparison(zeng_key_df, "max_temperature_c", "不同 SOC 最高温度对比", "最高温度 (℃)", theme_mode), use_container_width=True)
        with sample_tab:
            sample_rows = [
                {"采样节点": "一采 · T2=100℃", "状态": "完成" if sampled.get("t2_100") else summary.get("sample_status", {}).get("sample_t2_100", "待完成")},
                {"采样节点": "二采 · 安全阀喷阀", "状态": "完成" if sampled.get("venting") else summary.get("sample_status", {}).get("sample_venting", "待完成")},
                {"采样节点": "三采 · 温度峰值", "状态": "完成" if sampled.get("temperature_peak") else summary.get("sample_status", {}).get("sample_temperature_peak", "待完成")},
                {"采样节点": "四采 · 压力稳定", "状态": "完成" if sampled.get("pressure_stable") else summary.get("sample_status", {}).get("sample_pressure_stable", "待完成")},
            ]
            st.dataframe(pd.DataFrame(sample_rows), use_container_width=True, hide_index=True)
        with gc_tab:
            st.dataframe(zeng_gc_df, use_container_width=True, hide_index=True)
            st.plotly_chart(plot_zeng_stage_gas_trends(zeng_gc_df, theme_mode), use_container_width=True)
        with lel_tab:
            st.info("LFL 教学解释仅用于教学估算，不用于真实工程判断。")
            render_asset_image("assets/mechanism/08_lel_risk_evaluation.png", "LFL_mix 可燃风险解释示意。", "可燃风险解释")
        with assess_tab:
            _render_assessment_panel("literature")
        with report_tab:
            render_logbook(literature_state.get("operation_logs", []) or [])
            st.dataframe(pd.DataFrame(summary["suggestions"], columns=["学习建议"]), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
    with st.expander("文献数据来源", expanded=False):
        st.dataframe(metadata_df, use_container_width=True, hide_index=True)
        st.warning("本文献数据仅用于教学平台的数据回放与风险评价演示，不用于真实事故预测、消防应急或工程防爆设计。")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_arc_immersive_window(
    state: dict,
    *,
    summary: dict,
    arc_curve: pd.DataFrame,
    pressure_curve: pd.DataFrame,
    peaks_df: pd.DataFrame,
    gas_df: pd.DataFrame,
    lfl_dict: dict[str, float],
    active_gas_volume_formula: pd.DataFrame,
    dataset_config: dict,
) -> None:
    """Render ARC mode as one immersive lab window."""
    fullscreen = bool(st.session_state.get("arc_canvas_fullscreen", False))
    current_state = state.get("current_state", "sample_preparation")
    render_window_header(
        "ARC 通用模式沉浸式实验窗口",
        "ARC、20 L 罐、采样、GC、LFL 与报告摘要统一在实验窗口内操作。",
        fullscreen=fullscreen,
        key_prefix="arc_canvas",
    )
    render_status_strip(
        [
            ("SOC", f"{state.get('selected_soc') or '未选择'}", "active" if state.get("selected_soc") else "idle"),
            ("舱门", "已关闭" if state.get("arc_door_closed") else "待关闭", "done" if state.get("arc_door_closed") else "active"),
            ("置换", f"{state.get('replacement_count', 0)}/3", "done" if int(state.get("replacement_count", 0)) >= 3 else "active"),
            ("采样", "完成" if state.get("gas_bag_filled") else "待采样", "done" if state.get("gas_bag_filled") else "active"),
            ("LFL", "已评价" if state.get("lel_calculated") else "待评价", "done" if state.get("lel_calculated") else "active"),
        ]
    )
    action_handler = lambda action, payload=None: _handle_arc_immersive_action(
        action,
        payload,
        gas_df_for_lel=gas_df,
        lfl_dict_for_lel=lfl_dict,
        gas_volume_formula=active_gas_volume_formula,
        dataset_config_for_report=dataset_config,
    )
    with st.container(border=True):
        st.markdown("**实验电池 SOC 选择**")
        st.caption("SOC 影响热失控产气量、产气速率和可燃风险，本平台用于教学对比。")
        soc_options = [25, 50, 75, 100]
        soc_cols = st.columns(4, gap="small")
        for idx, soc_value in enumerate(soc_options):
            selected = str(state.get("selected_soc")) == str(soc_value)
            with soc_cols[idx]:
                if st.button(
                    f"{soc_value}%",
                    key=f"arc_imm_soc_{soc_value}",
                    type="primary" if selected else "secondary",
                    disabled=bool(state.get("battery_loaded")) and not selected,
                    use_container_width=True,
                ):
                    _handle_arc_immersive_action("select_soc", {"soc": soc_value})
    render_arc_workbench(
        state=state,
        summary=summary,
        svg_markup=render_full_workbench_svg({**state, "_assessment_summary": summary}),
        action_groups=_arc_action_groups(state),
        action_handler=action_handler,
        fullscreen=fullscreen,
        title="ARC 通用模式数字孪生画布",
    )
    if fullscreen:
        return

    _render_runaway_focus_view("arc", state)
    with st.expander("实验反馈与数据区", expanded=True):
        daq_tab, curve_tab, sample_tab, gc_tab, lel_tab, assess_tab, report_tab = st.tabs(
            ["实时 DAQ 数据采集仪", "曲线", "采样记录", "GC 组分", "LFL 解释", "考核记录", "报告摘要"]
        )
        with daq_tab:
            render_monitor_screen(
                t2=float(state.get("temperature", 25.0) or 25.0),
                pressure=float(state.get("pressure", 101.3) or 101.3),
                heating_rate=float(state.get("heating_rate", 0.0) or 0.0),
                gc_done=state.get("gc_finished", False),
            )
            render_logbook(state.get("operation_logs", []) or [])
        with curve_tab:
            st.plotly_chart(plot_temperature_curve(arc_curve, theme_mode), use_container_width=True)
            st.plotly_chart(plot_pressure_curve(pressure_curve, theme_mode), use_container_width=True)
        with sample_tab:
            st.dataframe(pd.DataFrame([
                {"节点": "连接集气袋", "状态": "完成" if state.get("gas_bag_connected") else "待完成"},
                {"节点": "打开采样阀", "状态": "完成" if state.get("sampling_started") else "待完成"},
                {"节点": "关闭采样阀", "状态": "完成" if state.get("gas_bag_filled") else ("待关闭" if state.get("sampling_valve_open") else "待完成")},
                {"节点": "采样完成", "状态": "完成" if state.get("gas_bag_filled") else "待完成"},
            ]), use_container_width=True, hide_index=True)
        with gc_tab:
            if state.get("gc_finished"):
                st.plotly_chart(plot_gc_chromatogram(peaks_df, theme_mode), use_container_width=True) if not peaks_df.empty else st.warning("暂无色谱数据")
                sample = _select_sample(gas_df, state.get("selected_soc"))
                st.plotly_chart(plot_gas_composition_bar(_extract_composition(sample), set(lfl_dict.keys()), "GC 气体组成", theme_mode), use_container_width=True)
            else:
                st.info("GC 分析完成后显示色谱峰和气体组成。")
        with lel_tab:
            if state.get("lel_calculated") or "interactive_lel_result" in st.session_state:
                lel_result = st.session_state.get("interactive_lel_result") or _run_lel_calculation(state, gas_df, lfl_dict)
                render_risk_badge(lel_result["risk_info"]["level"])
                st.plotly_chart(plot_risk_gauge(lel_result["risk_ratio"], theme_mode=theme_mode), use_container_width=True)
                st.caption(lel_result["statement"])
            else:
                st.info("完成 GC 和产气量记录后进入 LFL_mix 可燃风险评价。")
        with assess_tab:
            _render_assessment_panel("arc")
        with report_tab:
            render_logbook(state.get("operation_logs", []) or [])
            st.dataframe(pd.DataFrame(summary["suggestions"], columns=["学习建议"]), use_container_width=True, hide_index=True)
    return
    st.markdown(f'<div class="immersive-shell {"is-fullscreen" if fullscreen else ""}">', unsafe_allow_html=True)
    render_window_header(
        "ARC 通用模式沉浸式实验窗口",
        "ARC、20 L 罐、采样、GC、LFL 与报告摘要统一在实验窗口内操作。",
        fullscreen=fullscreen,
        key_prefix="arc_canvas",
    )
    render_safety_overlay(summary)
    render_status_strip(
        [
            ("SOC", f"{state.get('selected_soc') or '未选择'}", "active" if state.get("selected_soc") else "idle"),
            ("舱门", "已关闭" if state.get("arc_door_closed") else "待关闭", "done" if state.get("arc_door_closed") else "active"),
            ("置换", f"{state.get('replacement_count', 0)}/3", "done" if int(state.get("replacement_count", 0)) >= 3 else "active"),
            ("采样", "完成" if state.get("gas_bag_filled") else "待采样", "done" if state.get("gas_bag_filled") else "active"),
            ("LFL", "已评价" if state.get("lel_calculated") else "待评价", "done" if state.get("lel_calculated") else "active"),
        ]
    )
    left, center, right = st.columns([0.72, 2.16, 1.08], gap="medium")
    with left:
        render_score_overlay(summary, state_label(current_state))
        _render_step_axis(
            [
                ("电池准备", state.get("battery_loaded", False)),
                ("ARC 舱门 / 气密性", state.get("leak_test_passed", False)),
                ("20 L 罐三轮置换", state.get("replacement_count", 0) >= 3),
                ("ARC 虚拟热失控", state.get("current_state") in {"thermal_runaway", "cooling", "gas_sampling", "gc_analysis", "gas_volume_calculation", "lel_risk_evaluation", "report_generated"}),
                ("冷却后采样", state.get("gas_bag_filled", False)),
                ("GC 分析", state.get("gc_finished", False)),
                ("产气量记录", state.get("gas_volume_calculated", False)),
                ("可燃风险评价", state.get("lel_calculated", False)),
                ("报告生成", state.get("current_state") == "report_generated"),
            ],
            height=640 if fullscreen else 520,
        )
        render_current_step_guide(current_state)
    with center:
        st.session_state["arc_canvas_runaway_focus"] = current_state == "thermal_runaway"
        render_canvas_toolbar("arc_canvas")
        render_svg_canvas(
            render_full_workbench_svg({**state, "_assessment_summary": summary}),
            title="ARC 通用模式数字孪生画布",
            key_prefix="arc_canvas",
            height=740 if fullscreen else 570,
        )
        _render_runaway_focus_view("arc", state)
    with right:
        with st.container(border=True, height=760 if fullscreen else 640):
            st.markdown("**实验操作台**")
            render_theme_toggle(key="arc_imm_theme_toggle")
            soc = st.selectbox("SOC", options=[50, 100], index=1 if state.get("selected_soc") in {100, "100"} else 0, key="arc_imm_soc_select")
            if st.button("确认 SOC", key="arc_imm_soc_confirm", use_container_width=True):
                _handle_arc_immersive_action("select_soc", {"soc": soc})
            render_instrument_panel(state, mode="arc", assessment_summary=summary)
            render_action_groups(
                _arc_action_groups(state),
                lambda action, payload=None: _handle_arc_immersive_action(
                    action,
                    payload,
                    gas_df_for_lel=gas_df,
                    lfl_dict_for_lel=lfl_dict,
                    gas_volume_formula=active_gas_volume_formula,
                    dataset_config_for_report=dataset_config,
                ),
            )
    st.markdown('<div class="immersive-data-zone">', unsafe_allow_html=True)
    with st.expander("实验反馈与数据区", expanded=not fullscreen):
        daq_tab, curve_tab, sample_tab, gc_tab, lel_tab, assess_tab, report_tab = st.tabs(
            ["实时 DAQ 数据采集仪", "曲线", "采样记录", "GC 组分", "LFL 解释", "考核记录", "报告摘要"]
        )
        with daq_tab:
            render_monitor_screen(
                t2=float(state.get("temperature", 25.0) or 25.0),
                pressure=float(state.get("pressure", 101.3) or 101.3),
                heating_rate=float(state.get("heating_rate", 0.0) or 0.0),
                gc_done=state.get("gc_finished", False),
            )
            render_logbook(state.get("operation_logs", []) or [])
        with curve_tab:
            st.plotly_chart(plot_temperature_curve(arc_curve, theme_mode), use_container_width=True)
            st.plotly_chart(plot_heating_rate_curve(arc_curve, theme_mode), use_container_width=True)
            st.plotly_chart(plot_pressure_curve(pressure_curve, theme_mode), use_container_width=True)
        with sample_tab:
            st.dataframe(pd.DataFrame([
                {"节点": "连接集气袋", "状态": "完成" if state.get("gas_bag_connected") else "待完成"},
                {"节点": "打开采样阀", "状态": "完成" if state.get("sampling_started") else "待完成"},
                {"节点": "关闭采样阀", "状态": "完成" if state.get("gas_bag_filled") else ("待关闭" if state.get("sampling_valve_open") else "待完成")},
                {"节点": "采样完成", "状态": "完成" if state.get("gas_bag_filled") else "待完成"},
            ]), use_container_width=True, hide_index=True)
        with gc_tab:
            if state.get("gc_finished"):
                st.plotly_chart(plot_gc_chromatogram(peaks_df, theme_mode), use_container_width=True) if not peaks_df.empty else st.warning("暂无色谱数据")
                sample = _select_sample(gas_df, state.get("selected_soc"))
                st.plotly_chart(plot_gas_composition_bar(_extract_composition(sample), set(lfl_dict.keys()), "GC 气体组成", theme_mode), use_container_width=True)
            else:
                st.info("GC 分析完成后显示色谱峰和气体组成。")
        with lel_tab:
            if state.get("lel_calculated") or "interactive_lel_result" in st.session_state:
                lel_result = st.session_state.get("interactive_lel_result") or _run_lel_calculation(state, gas_df, lfl_dict)
                render_risk_badge(lel_result["risk_info"]["level"])
                st.plotly_chart(plot_risk_gauge(lel_result["risk_ratio"], theme_mode=theme_mode), use_container_width=True)
                st.caption(lel_result["statement"])
            else:
                st.info("完成 GC 和产气量记录后进入 LFL_mix 可燃风险评价。")
        with assess_tab:
            _render_assessment_panel("arc")
        with report_tab:
            render_logbook(state.get("operation_logs", []) or [])
            st.dataframe(pd.DataFrame(summary["suggestions"], columns=["学习建议"]), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ─── 全局状态 ───────────────────────────────────────────────
theme_mode = get_current_theme()
gas_df, lfl_dict = _load_base_assets()
state = get_experiment_state()
literature_state = get_literature_experiment_state()

capture_mode = st.query_params.get("capture")
workbench_mode = st.query_params.get("workbench")
if capture_mode in {"zoom-right"}:
    st.session_state["arc_canvas_zoom"] = 1.75
    st.session_state["arc_canvas_fullscreen"] = True
elif capture_mode == "large":
    st.session_state["arc_canvas_fullscreen"] = True
    st.session_state["literature_canvas_fullscreen"] = True
elif workbench_mode == "large":
    st.session_state["arc_canvas_fullscreen"] = True
    st.session_state["literature_canvas_fullscreen"] = True
    _apply_workbench_fullscreen_chrome()
elif capture_mode in {"hotspots", "alert", "legend", "n2-active", "n2-closed", "score-unified", "fullscreen-immersive"}:
    st.session_state["arc_canvas_fullscreen"] = True
    if capture_mode in {"alert", "score-unified"}:
        reset_assessment("arc")
    state.update(
        {
            "selected_soc": 100,
            "battery_loaded": True,
            "arc_door_closed": True,
            "leak_test_passed": True,
            "replacement_count": 1 if capture_mode in {"n2-active", "n2-closed"} else 3,
            "cycle_vacuum_done": True,
            "cycle_nitrogen_done": capture_mode == "n2-closed",
            "nitrogen_valve_open": capture_mode == "n2-active",
            "gas_bag_connected": capture_mode in {"hotspots", "legend", "score-unified", "fullscreen-immersive"},
            "sampling_valve_open": capture_mode == "hotspots",
            "gc_started": capture_mode in {"hotspots", "legend", "score-unified", "fullscreen-immersive"},
            "temperature": 180.0,
            "pressure": 101.3 if capture_mode in {"n2-active", "n2-closed"} else 118.0,
            "heating_rate": 3.2,
            "current_state": (
                "nitrogen_filling"
                if capture_mode == "n2-active"
                else "atmosphere_replacement"
                if capture_mode == "n2-closed"
                else "gc_analysis"
                if capture_mode in {"score-unified", "fullscreen-immersive"}
                else "arc_heating"
                if capture_mode != "alert"
                else "sample_preparation"
            ),
        }
    )
    if capture_mode == "alert":
        record_assessment_event("arc", "start_arc", False, "未完成氮气置换即启动 ARC", severity="critical")
    elif capture_mode == "score-unified":
        record_assessment_event("arc", "start_arc", False, "未完成氮气置换即启动 ARC", severity="major")

if capture_mode in {"literature-cleaned"}:
    st.session_state["literature_canvas_fullscreen"] = True
    literature_state.update(
        {
            "selected_soc": 100,
            "cell_loaded": True,
            "thermocouples_placed": True,
            "voltage_leads_connected": True,
            "pressure_sensor_checked": True,
            "chamber_door_closed": True,
            "vacuum_done": True,
            "nitrogen_filled": True,
            "current_state": "nitrogen_filled",
            "temperature_t2_c": 25.0,
            "pressure_kpa": 101.3,
        }
    )

if capture_mode in {"score-unified", "fullscreen-immersive"}:
    _apply_workbench_fullscreen_chrome()
    render_page_header(
        title="二维交互实验台：ARC 通用模式沉浸视图",
        description="截图验证视图：展示同一评分源、仪器控制屏和可滚动操作区。",
        tags=["ARC 通用模式", "实验评分", "沉浸式画布"],
    )
    render_arc_workbench(
        state=state,
        summary=assessment_summary("arc"),
        svg_markup=render_full_workbench_svg({**state, "_assessment_summary": assessment_summary("arc")}),
        action_groups=_arc_action_groups(state),
        action_handler=lambda action, payload=None: None,
        fullscreen=True,
        title="ARC 通用模式数字孪生画布",
    )
    st.stop()

if capture_mode in {"literature-cleaned"}:
    render_page_header(
        title="二维交互实验台：文献装置模式",
        description="截图验证视图：展示整理后的文献装置数字孪生画布。",
        tags=["文献装置", "数字孪生画布", "教学说明"],
    )
    render_canvas_toolbar("literature_canvas")
    render_svg_canvas(
        render_explosion_chamber_heating_platform_svg(literature_state),
        title="文献装置数字孪生画布",
        key_prefix="literature_canvas",
        height=720,
    )
    st.stop()

if capture_mode in {"standard", "large", "hotspots", "alert", "legend", "n2-active", "n2-closed", "zoom-right"}:
    render_page_header(
        title="二维交互实验台：热失控产气收集与燃爆风险评价",
        description="截图验证视图：仅展示教学安全边界、画布工具栏和二维设备连接总览。",
        tags=["二维交互实验台", "ARC", "GC", "LFL_mix 可燃风险评价"],
    )
    render_warning_banner("本页面为虚拟教学演示，不输出真实危险实验操作指导。")
    render_canvas_toolbar("arc_canvas")
    render_svg_canvas(
        render_full_workbench_svg({**state, "_assessment_summary": assessment_summary("arc")}),
        title="ARC 通用模式数字孪生画布",
        key_prefix="arc_canvas",
        height=760 if capture_mode == "large" else 680,
    )
    st.stop()

# ─── 页面头部 ───────────────────────────────────────────────
arc_fullscreen_active = bool(st.session_state.get("arc_canvas_fullscreen", False))
if not arc_fullscreen_active:
    render_page_header(
        title="二维交互实验台：热失控产气收集与燃爆风险评价",
        description="按实验流程完成样品准备、气氛控制、热失控触发、气体采样和 GC 分析，最终进行 LFL_mix 可燃风险评价并生成实验报告。",
        tags=["虚拟实验台", "工业控制面板", "GC 分析", "LFL_mix 可燃风险评价"],
    )
    render_warning_banner("本页面为虚拟教学演示，不输出真实危险实验操作指导。")
    if not st.session_state.get("guide_safety_ack", False):
        st.info("建议先在“实验导学”页确认虚拟实验规范。本页不会提供真实危险实验 SOP，所有数据均用于教学演示。")

# ─── 实验模式 ───────────────────────────────────────────────
st.session_state.setdefault("experiment_mode_choice", "教学 ARC / 通用热失控模式")
render_section_title("实验模式", "选择本次二维交互实验台的核心入口。")
mode_cols = st.columns(2, gap="medium")
mode_options = [
    (
        "教学 ARC / 通用热失控模式",
        "用于完成标准化产气采集、GC-MS 分析与 LFL_mix 风险评价流程。",
        "arc_mode_select",
    ),
    (
        "文献装置沉浸式实验窗口",
        "用于理解文献实验装置结构、采样流程和数据采集逻辑。",
        "literature_mode_select",
    ),
]
for col, (label, desc, key) in zip(mode_cols, mode_options):
    selected = st.session_state["experiment_mode_choice"] == label
    with col:
        st.markdown(
            f"""
<div style="border:2px solid {'var(--app-primary-light)' if selected else 'var(--app-border)'};background:{'rgba(0,131,143,0.08)' if selected else 'var(--app-surface)'};border-radius:12px;padding:12px 14px;margin-bottom:8px;">
  <div style="font-weight:800;color:var(--app-primary);font-size:1rem;">{label}</div>
  <div style="font-size:0.86rem;line-height:1.55;color:var(--app-text);margin-top:4px;">{desc}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("进入该模式" if not selected else "当前模式", key=key, type="primary" if selected else "secondary", use_container_width=True):
            st.session_state["experiment_mode_choice"] = label
            st.rerun()
experiment_mode = st.session_state["experiment_mode_choice"]
assistant_state = get_literature_experiment_state() if experiment_mode.startswith("文献装置") else get_experiment_state()
assistant_assessment = assessment_summary("literature" if experiment_mode.startswith("文献装置") else "arc")
render_teaching_ai_widget(
    page_name="二维交互实验台",
    experiment_state=assistant_state,
    assessment=assistant_assessment,
    key_prefix="lab_page",
)

# ═══════════════════════════════════════════════════════════════
# 文献装置模式
# ═══════════════════════════════════════════════════════════════
if experiment_mode.startswith("文献装置"):
    literature_state = get_literature_experiment_state()
    metadata_df, battery_df, zeng_key_df, zeng_gc_df = _load_zeng_2026_assets()
    current_state = literature_state.get("current_state", "soc_selection")
    selected_soc = literature_state.get("selected_soc")
    sampled = literature_state.get("sampling_completed", {}) or {}
    literature_summary = assessment_summary("literature")

    _render_literature_immersive_window(
        literature_state,
        selected_soc=selected_soc,
        sampled=sampled,
        summary=literature_summary,
        zeng_key_df=zeng_key_df,
        zeng_gc_df=zeng_gc_df,
        metadata_df=metadata_df,
    )
    render_global_footer()
    st.stop()

    # ── 顶栏 ──
    top = st.container()
    with top:
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([0.8, 0.7, 0.5, 0.6, 0.55, 0.55, 0.6, 0.68])
        with c1:
            soc_val = st.selectbox("SOC", options=[0, 25, 50, 75, 100],
                                   index=[0, 25, 50, 75, 100].index(selected_soc) if selected_soc in [0, 25, 50, 75, 100] else 4)
        with c2:
            if st.button("📌 确认选择 SOC", key="lit_top_soc", use_container_width=True):
                _run_literature_action("select_soc", {"soc": soc_val})
        with c3:
            render_metric_card("模式", "文献装置")
        with c4:
            render_metric_card("阶段", state_label(current_state))
        with c5:
            done_count = sum(1 for v in sampled.values() if v)
            render_metric_card("采气", f"{done_count}/4")
        with c6:
            render_metric_card("评分", f"{literature_state.get('score', 100)}")
        with c7:
            render_metric_card("考核", f"{literature_summary['score']}")
        with c8:
            render_metric_card("数据", "有效" if literature_summary["valid_data"] else "需复核")
    _render_assessment_snapshot("literature")

    # ── 主体三栏 ──
    left_nav, center_svg, right_panel = st.columns([0.72, 2.2, 1.08], gap="medium")

    with left_nav:
        # 实验步骤时间轴（简化版——纯朴HTML）
        steps_html = []
        step_defs = [
            ("选择 SOC", bool(selected_soc is not None)),
            ("放入方壳 LFP 电池", literature_state.get("cell_loaded", False)),
            ("布置 T1/T2/T3 热电偶", literature_state.get("thermocouples_placed", False)),
            ("连接电压采集线", literature_state.get("voltage_leads_connected", False)),
            ("检查压力传感器", literature_state.get("pressure_sensor_checked", False)),
            ("关闭防爆舱门", literature_state.get("chamber_door_closed", False)),
            ("抽真空", literature_state.get("vacuum_done", False)),
            ("充入氮气至大气压", literature_state.get("nitrogen_filled", False)),
            ("启动加热演示", literature_state.get("heating_started", False)),
            ("T2=100℃ 一采", sampled.get("t2_100", False)),
            ("喷阀 二采", sampled.get("venting", False)),
            ("温度峰值 三采", sampled.get("temperature_peak", False)),
            ("压力稳定 四采", sampled.get("pressure_stable", False)),
            ("GC 气相色谱分析", literature_state.get("gc_finished", False)),
            ("可燃风险评价", literature_state.get("lel_risk_evaluated", False)),
            ("生成实验报告", literature_state.get("report_generated", False)),
        ]
        # 确定当前活跃步骤
        active_idx = None
        for i, (_, done) in enumerate(step_defs):
            if not done and active_idx is None:
                active_idx = i
                break
        if active_idx is None:
            active_idx = len(step_defs) - 1

        for idx, (label, done) in enumerate(step_defs):
            if done:
                icon, color = "✓", "var(--app-green)"
                weight = "normal"
            elif idx == active_idx:
                icon, color = "▶", "var(--app-primary-light)"
                weight = "bold"
            else:
                icon, color = "○", "var(--app-muted)"
                weight = "normal"
            steps_html.append(
                f'<div style="display:flex;gap:8px;align-items:center;padding:3px 0;">'
                f'<span style="color:{color};width:18px;text-align:center;flex-shrink:0;">{icon}</span>'
                f'<span style="color:var(--app-text);font-size:0.82rem;font-weight:{weight};">{label}</span>'
                f'</div>'
            )

        st.markdown(
            f"""<div style="background:var(--app-surface);border:1px solid var(--app-border);
border-radius:12px;padding:12px 14px;max-height:520px;overflow-y:auto;">
<div style="font-weight:bold;font-size:0.9rem;color:var(--app-primary);margin-bottom:8px;">
🧪 实验流程</div>
{''.join(steps_html)}
</div>""",
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        render_current_step_guide(current_state)
        st.markdown("<br>", unsafe_allow_html=True)
        render_model_notice("表1/表2为文献明确数值，表3组分数值未提供时仅保留教学占位。", title="📖 数据说明")

    with center_svg:
        render_section_title("数字孪生实验画布", "防爆舱 · 加热板 · 传感器 · 采样 · GC · DAQ")
        st.session_state["literature_canvas_runaway_focus"] = current_state in {"venting", "temperature_peak"}
        render_canvas_toolbar("literature_canvas")
        render_svg_canvas(
            render_explosion_chamber_heating_platform_svg(literature_state),
            title="文献装置数字孪生画布",
            key_prefix="literature_canvas",
            height=620,
        )
        _render_runaway_focus_view("literature", literature_state)
        _render_mechanism_gallery("literature", literature_state)

        # 装置标签（可折叠）
        with st.expander("📌 装置功能说明", expanded=False):
            st.markdown("""
| 设备 | 功能 | 操作提示 |
|------|------|----------|
| 🔒 防爆舱体 | 隔绝空气承载热失控实验 | 关闭舱门后抽真空置换 |
| 🔋 方壳 LFP 电池 | 电池样品占位 | 选择 SOC 后放入舱内 |
| 🌡️ T1/T2/T3 | K 型热电偶，T2 主控 | T2=100℃ 触发一采 |
| ⚡ 电压采集线 | V+/V- 接电池至 DAQ | 在布置热电偶后连接 |
| 🔥 加热模块 | 虚拟加热演示 | 置换完成后启动教学演示 |
| 📊 压力传感器 | 模拟表盘监测舱压 | 观察指针变化判断阶段 |
| 🏷️ 集气袋 | 四阶段分时采样 | 各阶段条件满足后采样 |
| 🔬 GC 色谱仪 | FID/TCD 气体组成分析 | 四阶段采气完成后送入 |
| 💻 DAQ 数据采集仪 | 温度/压力/电压记录 | 监控屏实时显示 |
| 💨 真空泵 | 舱内抽真空 | 关舱门后方可启动 |
| 🫧 氮气瓶 | 高纯 N₂ 惰性气氛 | 抽真空后充入至大气压 |
""")

        tab1, tab2, tab3, tab4 = st.tabs(["表1 样品", "表2 关键节点", "表3 组分", "SOC 对比"])
        with tab1:
            st.caption("来源：曾垂辉等 2026，表 1。")
            st.dataframe(battery_df, use_container_width=True, hide_index=True)
        with tab2:
            st.caption("来源：曾垂辉等 2026，表 2。0% SOC 标记为未热失控。")
            st.dataframe(zeng_key_df, use_container_width=True, hide_index=True)
        with tab3:
            st.caption("表 3 具体数值未提供，当前为教学占位。")
            st.dataframe(zeng_gc_df, use_container_width=True, hide_index=True)
            st.plotly_chart(plot_zeng_stage_gas_trends(zeng_gc_df, theme_mode), use_container_width=True)
        with tab4:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(plot_zeng_key_point_comparison(zeng_key_df, "max_temperature_c", "不同 SOC 最高温度对比", "最高温度 (℃)", theme_mode), use_container_width=True)
                st.plotly_chart(plot_zeng_key_point_comparison(zeng_key_df, "thermal_runaway_time_s", "不同 SOC 热失控时间对比", "热失控时间 (s)", theme_mode), use_container_width=True)
            with c2:
                st.plotly_chart(plot_zeng_key_point_comparison(zeng_key_df, "max_heating_rate_c_per_s", "不同 SOC 最大温升速率对比", "最大温升速率 (℃/s)", theme_mode), use_container_width=True)
                st.plotly_chart(plot_zeng_sampling_timeline(zeng_key_df, selected_soc if selected_soc is not None else 100, theme_mode), use_container_width=True)

    with right_panel:
        # 仪器控制屏
        render_instrument_panel(literature_state, mode="literature")
        _render_device_task_panel("literature", literature_state)

        # ── 设备控制面板（使用 st.button，紧凑排列）──

        # 样品准备区
        with st.container(border=True):
            st.caption("🔋 样品准备 · 防爆舱")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("放入方壳 LFP 电池", key="lit_btn_cell",
                             disabled=literature_state.get("cell_loaded") or selected_soc is None,
                             use_container_width=True,
                             help="将选定 SOC 的方壳磷酸铁锂硬壳电池放入防爆舱内"):
                    _run_literature_action("load_prismatic_cell")
            with b2:
                if st.button("布置 T1/T2/T3 热电偶", key="lit_btn_tc",
                             disabled=literature_state.get("thermocouples_placed") or not literature_state.get("cell_loaded"),
                             use_container_width=True,
                             help="将三根 K 型热电偶固定在电池壳体不同位置"):
                    _run_literature_action("place_thermocouples")
            b3, b4 = st.columns(2)
            with b3:
                if st.button("连接电压采集线", key="lit_btn_volt",
                             disabled=literature_state.get("voltage_leads_connected") or not literature_state.get("thermocouples_placed"),
                             use_container_width=True):
                    _run_literature_action("connect_voltage_leads")
            with b4:
                if st.button("检查压力传感器", key="lit_btn_press",
                             disabled=literature_state.get("pressure_sensor_checked") or not literature_state.get("voltage_leads_connected"),
                             use_container_width=True):
                    _run_literature_action("check_pressure_sensor")

        # 舱门与气氛控制
        door_ready = literature_state.get("thermocouples_placed") and literature_state.get("pressure_sensor_checked")
        with st.container(border=True):
            st.caption("🔒 防爆舱 · 气氛控制")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("关闭防爆舱门", key="lit_btn_door",
                             disabled=literature_state.get("chamber_door_closed") or not door_ready,
                             use_container_width=True):
                    _run_literature_action("close_chamber_door")
            with b2:
                if st.button("抽真空", key="lit_btn_vac",
                             disabled=literature_state.get("vacuum_done") or not literature_state.get("chamber_door_closed"),
                             use_container_width=True):
                    _run_literature_action("start_vacuum")
            b3, b4 = st.columns(2)
            with b3:
                if st.button("充入氮气", key="lit_btn_n2",
                             disabled=literature_state.get("nitrogen_filled") or not literature_state.get("vacuum_done"),
                             use_container_width=True):
                    _run_literature_action("fill_nitrogen")
            with b4:
                n2_ready = literature_state.get("nitrogen_filled") and not literature_state.get("heating_started")
                if st.button("⚡ 启动加热演示", key="lit_btn_heat",
                             disabled=literature_state.get("heating_started") or not literature_state.get("nitrogen_filled"),
                             type="primary" if n2_ready else "secondary",
                             use_container_width=True):
                    _run_literature_action("start_heating")

        # 加热观察
        if literature_state.get("heating_started"):
            with st.container(border=True):
                st.caption("🌡️ 温度监测 · 加热演示")
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("T2 达到 100℃", key="lit_btn_t2",
                                 disabled=literature_state.get("t2_reached_100"),
                                 use_container_width=True):
                        _run_literature_action("observe_t2_100")
                with b2:
                    if st.button("检测安全阀喷阀", key="lit_btn_vent",
                                 disabled=literature_state.get("venting_detected") or not sampled.get("t2_100"),
                                 use_container_width=True):
                        _run_literature_action("observe_venting")
                b3, b4 = st.columns(2)
                with b3:
                    if st.button("观察温度峰值", key="lit_btn_peak",
                                 disabled=literature_state.get("temperature_peak_reached") or not sampled.get("venting"),
                                 use_container_width=True):
                        _run_literature_action("observe_temperature_peak")
                with b4:
                    if st.button("观察压力稳定", key="lit_btn_stable",
                                 disabled=literature_state.get("pressure_stable") or not sampled.get("temperature_peak"),
                                 use_container_width=True):
                        _run_literature_action("observe_pressure_stable")

        # 四阶段采气
        with st.container(border=True):
            st.caption("🏷️ 集气袋四阶段采样")
            s1, s2 = st.columns(2)
            with s1:
                if st.button("一采 · T2=100℃", key="lit_btn_s1",
                             disabled=sampled.get("t2_100") or not literature_state.get("t2_reached_100"),
                             use_container_width=True):
                    _run_literature_action("sample_t2_100")
            with s2:
                if st.button("二采 · 安全阀喷阀", key="lit_btn_s2",
                             disabled=sampled.get("venting") or not literature_state.get("venting_detected"),
                             use_container_width=True):
                    _run_literature_action("sample_venting")
            s3, s4 = st.columns(2)
            with s3:
                if st.button("三采 · 温度峰值", key="lit_btn_s3",
                             disabled=sampled.get("temperature_peak") or not literature_state.get("temperature_peak_reached"),
                             use_container_width=True):
                    _run_literature_action("sample_temperature_peak")
            with s4:
                if st.button("四采 · 压力稳定", key="lit_btn_s4",
                             disabled=sampled.get("pressure_stable") or not literature_state.get("pressure_stable"),
                             use_container_width=True):
                    _run_literature_action("sample_pressure_stable")

        # GC 与风险评价
        gc_ready = all(sampled.get(s, False) for s in ["t2_100", "venting", "temperature_peak", "pressure_stable"])
        with st.container(border=True):
            st.caption("🔬 GC 分析与风险评价")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("启动 GC 分析", key="lit_btn_gc",
                             disabled=literature_state.get("gc_started") or not gc_ready,
                             type="primary" if gc_ready and not literature_state.get("gc_started") else "secondary",
                             use_container_width=True):
                    _run_literature_action("start_gc")
            with b2:
                if st.button("完成 GC", key="lit_btn_gc_done",
                             disabled=literature_state.get("gc_finished") or not literature_state.get("gc_started"),
                             use_container_width=True):
                    _run_literature_action("finish_gc")
            b3, b4 = st.columns(2)
            with b3:
                if st.button("查看气体组成", key="lit_btn_view_gas",
                             disabled=not literature_state.get("gc_finished"),
                             use_container_width=True):
                    _run_literature_action("view_gas_composition")
            with b4:
                lel_ready = literature_state.get("gc_finished") and not literature_state.get("lel_risk_evaluated")
                if st.button("计算可燃风险", key="lit_btn_lel",
                             disabled=literature_state.get("lel_risk_evaluated") or not literature_state.get("gc_finished"),
                             type="primary" if lel_ready else "secondary",
                             use_container_width=True):
                    _run_literature_action("evaluate_lel_risk")

        # 报告
        rpt_ready = literature_state.get("lel_risk_evaluated") and not literature_state.get("report_generated")
        with st.container(border=True):
            st.caption("📊 实验报告")
            if st.button("📝 生成实验报告", key="lit_btn_rpt",
                         disabled=literature_state.get("report_generated") or not literature_state.get("lel_risk_evaluated"),
                         type="primary" if rpt_ready else "secondary",
                         use_container_width=True):
                try:
                    ok, msg = perform_literature_session_action("generate_report")
                except Exception:
                    LOGGER.exception("Literature report action failed")
                    st.warning("报告生成失败，请检查前置步骤后重试。")
                    ok, msg = False, ""
                _record_action_assessment("literature", "generate_report", ok, msg)
                if ok:
                    st.session_state["interactive_experiment_last"] = {
                        "experiment_state": get_literature_experiment_state().copy(),
                        "score_summary": {
                            "final_score": get_literature_experiment_state().get("score", 100),
                            "error_count": get_literature_experiment_state().get("error_count", 0),
                            "completion_pct": 100.0,
                        },
                        "active_dataset": get_active_dataset_config(),
                    }
                _handle_action_result(ok, msg)

        # 重置
        if st.button("🔄 重置文献模式实验", key="lit_btn_reset", use_container_width=True):
            reset_literature_experiment()
            reset_assessment("literature")
            st.rerun()

    # ── 底部：DAQ / 曲线 / 采样 / GC / LFL / 考核 / 报告 ──
    st.markdown("---")
    daq_tab, curve_tab, sample_tab, gc_tab, lel_tab, assess_tab, report_tab = st.tabs(
        ["实时 DAQ 数据采集仪", "曲线", "四次采样", "GC 组分", "LFL 解释", "考核记录", "报告摘要"]
    )
    with daq_tab:
        render_section_title("数据采集监控终端", "DAQ 数据采集仪实时显示")
        d1, d2 = st.columns([1, 1])
        with d1:
            render_monitor_screen(
                t2=float(literature_state.get("temperature_t2_c", 25.0) or 25.0),
                pressure=float(literature_state.get("pressure_kpa", 101.3) or 101.3),
                gc_done=literature_state.get("gc_finished", False),
            )
        with d2:
            render_logbook(literature_state.get("operation_logs", []) or [])
    with curve_tab:
        st.caption("来源：曾垂辉等 2026 已整理字段；曲线仅用于教学对比。")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(
                plot_zeng_key_point_comparison(zeng_key_df, "max_temperature_c", "不同 SOC 最高温度对比", "最高温度 (℃)", theme_mode),
                use_container_width=True,
            )
            st.plotly_chart(
                plot_zeng_key_point_comparison(zeng_key_df, "thermal_runaway_time_s", "不同 SOC 热失控时间对比", "热失控时间 (s)", theme_mode),
                use_container_width=True,
            )
        with c2:
            st.plotly_chart(
                plot_zeng_key_point_comparison(zeng_key_df, "max_heating_rate_c_per_s", "不同 SOC 最大温升速率对比", "最大温升速率 (℃/s)", theme_mode),
                use_container_width=True,
            )
            st.plotly_chart(
                plot_zeng_sampling_timeline(zeng_key_df, selected_soc if selected_soc is not None else 100, theme_mode),
                use_container_width=True,
            )
    with sample_tab:
        sample_rows = [
            {"采样节点": "一采 · T2=100℃", "状态": "完成" if sampled.get("t2_100") else "待完成", "教学含义": "初期产气 / SEI 膜分解 / 电解液蒸发"},
            {"采样节点": "二采 · 安全阀喷阀", "状态": "完成" if sampled.get("venting") else "待完成", "教学含义": "早期预警到全面失控的缓冲阶段"},
            {"采样节点": "三采 · 温度峰值", "状态": "完成" if sampled.get("temperature_peak") else "待完成", "教学含义": "热失控最剧烈阶段"},
            {"采样节点": "四采 · 压力稳定", "状态": "完成" if sampled.get("pressure_stable") else "待完成", "教学含义": "反应结束 / 气体扩散阶段"},
        ]
        st.dataframe(pd.DataFrame(sample_rows), use_container_width=True, hide_index=True)
    with gc_tab:
        st.caption("表 3 具体数值未提供时保持教学占位，后续可替换为用户录入数据。")
        st.dataframe(zeng_gc_df, use_container_width=True, hide_index=True)
        st.plotly_chart(plot_zeng_stage_gas_trends(zeng_gc_df, theme_mode), use_container_width=True)
    with lel_tab:
        st.info("LFL 教学解释仅用于 Le Chatelier 混合规则教学演示，不用于真实安全决策。")
        render_asset_image("assets/mechanism/08_lel_risk_evaluation.png", "LFL_mix 可燃风险解释示意。", "可燃风险解释")
    with assess_tab:
        _render_assessment_panel("literature")
    with report_tab:
        render_section_title("报告摘要", "当前记录可进入报告生成模块继续整理")
        render_logbook(literature_state.get("operation_logs", []) or [])
        st.dataframe(pd.DataFrame(assessment_summary("literature")["suggestions"], columns=["学习建议"]), use_container_width=True, hide_index=True)

    # 文献信息
    with st.expander("📖 文献数据来源", expanded=False):
        st.dataframe(metadata_df, use_container_width=True, hide_index=True)
        st.warning("本文献数据仅用于教学平台的数据回放与风险评价演示，不用于真实事故预测、消防应急或工程防爆设计。")

    render_global_footer()
    st.stop()

# ═══════════════════════════════════════════════════════════════
# 教学 ARC / 通用热失控模式
# ═══════════════════════════════════════════════════════════════
dataset_df = list_available_datasets()
dataset_config = get_active_dataset_config()
arc_curve = load_active_arc_curve()
pressure_curve = load_active_pressure_curve()
peaks_df = load_active_gc_peaks()
active_gc_df = load_active_gc_composition()
active_gas_volume_formula = load_active_gas_volume_formula()

if dataset_config["is_validated_literature"] and not active_gc_df.empty:
    gas_df = _normalize_gc_composition_table(active_gc_df)

arc_summary = assessment_summary("arc")

# ── 数据集 ──
with st.expander("📂 数据集切换", expanded=False):
    ds1, ds2 = st.columns([1, 2])
    with ds1:
        selected_dataset = st.radio(
            "数据集", options=["teaching_demo", "validated_literature"],
            format_func=lambda k: DATASET_LABELS[k],
            index=0 if dataset_config["dataset_name"] == "teaching_demo" else 1,
        )
        if selected_dataset != dataset_config["dataset_name"]:
            set_active_dataset(selected_dataset)
            st.rerun()
    with ds2:
        dataset_config = get_active_dataset_config()
        if dataset_config["is_teaching_demo"]:
            st.info(dataset_config["message"])
        elif dataset_config["missing_items"]:
            st.warning(dataset_config["message"])
        else:
            st.success(dataset_config["message"])
        st.dataframe(dataset_df, use_container_width=True, hide_index=True)

_render_arc_immersive_window(
    state,
    summary=arc_summary,
    arc_curve=arc_curve,
    pressure_curve=pressure_curve,
    peaks_df=peaks_df,
    gas_df=gas_df,
    lfl_dict=lfl_dict,
    active_gas_volume_formula=active_gas_volume_formula,
    dataset_config=dataset_config,
)
render_global_footer()
st.stop()

# ── 主体三栏 ──
left_nav, center_svg, right_panel = st.columns([0.72, 2.2, 1.08], gap="medium")

with left_nav:
    # 实验步骤轴
    arc_step_defs = [
        ("电池准备", state.get("battery_loaded", False)),
        ("ARC 舱门 / 气密性", state.get("leak_test_passed", False)),
        ("20 L 罐三轮置换", state.get("replacement_count", 0) >= 3),
        ("ARC 虚拟热失控", state.get("current_state") in {"thermal_runaway", "cooling", "gas_sampling", "gc_analysis", "gas_volume_calculation", "lel_risk_evaluation", "report_generated"}),
        ("冷却后采样", state.get("gas_bag_filled", False)),
        ("GC 分析", state.get("gc_finished", False)),
        ("产气量记录", state.get("gas_volume_calculated", False)),
        ("可燃风险评价", state.get("lel_calculated", False)),
        ("报告生成", state.get("current_state") == "report_generated"),
    ]
    active_idx = next((i for i, (_, d) in enumerate(arc_step_defs) if not d), len(arc_step_defs) - 1)
    steps_html = []
    for idx, (label, done) in enumerate(arc_step_defs):
        icon, color = ("✓", "var(--app-green)") if done else ("▶", "var(--app-primary-light)") if idx == active_idx else ("○", "var(--app-muted)")
        weight = "bold" if idx == active_idx else "normal"
        steps_html.append(
            f'<div style="display:flex;gap:8px;align-items:center;padding:3px 0;">'
            f'<span style="color:{color};width:18px;text-align:center;">{icon}</span>'
            f'<span style="color:var(--app-text);font-size:0.82rem;font-weight:{weight};">{label}</span>'
            f'</div>'
        )
    st.markdown(
        f"""<div style="background:var(--app-surface);border:1px solid var(--app-border);
border-radius:12px;padding:12px 14px;max-height:480px;overflow-y:auto;">
<div style="font-weight:bold;font-size:0.9rem;color:var(--app-primary);margin-bottom:8px;">🧪 实验流程</div>
{''.join(steps_html)}
</div>""",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)
    render_current_step_guide(state.get("current_state", "sample_preparation"))
    st.markdown("<br>", unsafe_allow_html=True)
    render_model_notice("压力和温度变化为教学演示数据，非文献原始数据。", title="教学说明")

with center_svg:
    render_section_title("数字孪生实验画布", "ARC · 20L 罐 · N₂ · 真空泵 · 集气袋 · GC")
    st.session_state["arc_canvas_runaway_focus"] = state.get("current_state") == "thermal_runaway"
    render_canvas_toolbar("arc_canvas")
    render_svg_canvas(
        render_full_workbench_svg(state),
        title="ARC 通用模式数字孪生画布",
        key_prefix="arc_canvas",
        height=600,
    )
    _render_runaway_focus_view("arc", state)
    _render_mechanism_gallery("arc", state)
    with st.expander("📌 装置说明", expanded=False):
        st.markdown("""
| 设备 | 功能 |
|------|------|
| 🔬 ARC | 加速量热仪，虚拟升温与热失控演示 |
| 🫙 20L 密封罐 | 气体收集与压力监测 |
| 🫧 N₂ 瓶 | 高纯氮气，惰性气氛置换 |
| 💨 真空泵 | 旋片式真空泵 |
| 🏷️ 集气袋 | 气体采样收集 |
| 🔬 GC | FID/TCD 色谱分析 |
| 💻 监控屏 | T/P/dT/dt 实时数据 |
""")
    tab_arc, tab_press, tab_gc = st.tabs(["ARC 曲线", "压力曲线", "GC 色谱"])
    with tab_arc:
        st.caption("教学插值曲线，非文献原始数据。")
        st.plotly_chart(plot_temperature_curve(arc_curve, theme_mode), use_container_width=True)
        st.plotly_chart(plot_heating_rate_curve(arc_curve, theme_mode), use_container_width=True)
    with tab_press:
        st.caption("教学演示数据。")
        st.plotly_chart(plot_pressure_curve(pressure_curve, theme_mode), use_container_width=True)
    with tab_gc:
        if state.get("gc_finished"):
            st.caption("教学模拟 GC 色谱峰。")
            st.plotly_chart(plot_gc_chromatogram(peaks_df, theme_mode), use_container_width=True) if not peaks_df.empty else st.warning("暂无色谱数据")
        else:
            st.info("GC 分析完成后显示色谱峰。")

with right_panel:
    # 仪器控制屏
    render_instrument_panel(state, mode="arc", assessment_summary=arc_summary)
    _render_device_task_panel("arc", state)

    # ── 电池与舱门 ──
    with st.container(border=True):
        st.caption("🔋 样品准备 · 舱门控制")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("装入电池", key="arc_btn_battery",
                         disabled=state.get("battery_loaded") or not state.get("selected_soc"),
                         use_container_width=True):
                _run_arc_action("load_battery")
        with b2:
            if st.button("关闭 ARC 舱门", key="arc_btn_door",
                         disabled=state.get("arc_door_closed") or not state.get("battery_loaded"),
                         use_container_width=True):
                _run_arc_action("close_arc_door")
        if st.button("🔍 气密性检测", key="arc_btn_leak",
                     disabled=state.get("leak_test_passed") or not state.get("arc_door_closed"),
                     use_container_width=True,
                     type="primary" if state.get("arc_door_closed") and not state.get("leak_test_passed") else "secondary"):
            _run_arc_action("start_leak_test")

    # ── 气氛置换 ──
    with st.container(border=True):
        st.caption("💨 气氛置换 · 真空 / 氮气")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("开真空阀", key="arc_btn_vac_valve",
                         disabled=state.get("vacuum_valve_open") or not state.get("leak_test_passed"),
                         use_container_width=True):
                _run_arc_action("open_vacuum_valve")
        with b2:
            if st.button("启动真空泵", key="arc_btn_vac_pump",
                         disabled=not state.get("vacuum_valve_open") or state.get("cycle_vacuum_done"),
                         use_container_width=True):
                _run_arc_action("start_vacuum_pump")
        b3, b4 = st.columns(2)
        with b3:
            if st.button("关真空阀", key="arc_btn_close_vac",
                         disabled=not state.get("vacuum_valve_open") or not state.get("cycle_vacuum_done"),
                         use_container_width=True):
                _run_arc_action("close_vacuum_valve")
        with b4:
            n2_ready = not state.get("vacuum_valve_open") and state.get("cycle_vacuum_done")
            if st.button("开氮气阀", key="arc_btn_n2_valve",
                         disabled=state.get("nitrogen_valve_open") or not n2_ready,
                         use_container_width=True):
                _run_arc_action("open_nitrogen_valve")
        b5, b6 = st.columns(2)
        with b5:
            if st.button("关氮气阀", key="arc_btn_close_n2",
                         disabled=not state.get("nitrogen_valve_open"),
                         use_container_width=True):
                _run_arc_action("close_nitrogen_valve")
        with b6:
            cycle_ready = state.get("cycle_vacuum_done") and state.get("cycle_nitrogen_done") and not state.get("vacuum_valve_open") and not state.get("nitrogen_valve_open")
            if st.button("✓ 完成本轮置换", key="arc_btn_cycle",
                         disabled=not cycle_ready,
                         use_container_width=True):
                _run_arc_action("complete_replacement_cycle")

    # ── ARC 控制 ──
    with st.container(border=True):
        st.caption("🔥 ARC 热失控控制")
        b1, b2 = st.columns(2)
        with b1:
            arc_ready = state.get("current_state") == "arc_ready"
            if st.button("⚡ 启动 ARC", key="arc_btn_arc",
                         disabled=state.get("current_state") not in {"arc_ready", "arc_heating"} or state.get("current_state") == "arc_heating",
                         type="primary" if arc_ready else "secondary",
                         use_container_width=True):
                _run_arc_action("start_arc")
        with b2:
            if st.button("完成升温", key="arc_btn_heat_done",
                         disabled=state.get("current_state") != "arc_heating",
                         use_container_width=True):
                _run_arc_action("finish_arc_heating")
        b3, b4 = st.columns(2)
        with b3:
            if st.button("进入热失控演示", key="arc_btn_runaway",
                         disabled=state.get("current_state") not in {"arc_heating", "thermal_runaway"} or state.get("current_state") == "thermal_runaway",
                         use_container_width=True):
                _run_arc_action("trigger_thermal_runaway")
        with b4:
            if st.button("完成冷却", key="arc_btn_cool",
                         disabled=state.get("current_state") != "thermal_runaway",
                         use_container_width=True):
                _run_arc_action("finish_cooling")

    # ── 采样 ──
    with st.container(border=True):
        st.caption("🏷️ 气体采样")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("连接集气袋", key="arc_btn_bag",
                         disabled=state.get("gas_bag_connected") or state.get("current_state") not in {"cooling", "gas_sampling"},
                         use_container_width=True):
                _run_arc_action("connect_gas_bag")
        with b2:
            if st.button("打开采样阀", key="arc_btn_sampling",
                         disabled=state.get("sampling_valve_open") or not state.get("gas_bag_connected"),
                         use_container_width=True):
                _run_arc_action("open_sampling_valve")
        if st.button("关闭采样阀 · 完成采样", key="arc_btn_close_sampling",
                     disabled=not state.get("sampling_valve_open"),
                     use_container_width=True):
            _run_arc_action("close_sampling_valve")

    # ── GC ──
    with st.container(border=True):
        st.caption("🔬 GC 分析与评价")
        b1, b2 = st.columns(2)
        with b1:
            gc_ready_arc = state.get("gas_bag_filled") and not state.get("gc_started")
            if st.button("启动 GC", key="arc_btn_gc",
                         disabled=state.get("gc_started") or not state.get("gas_bag_filled"),
                         type="primary" if gc_ready_arc else "secondary",
                         use_container_width=True):
                _run_arc_action("start_gc")
        with b2:
            if st.button("完成 GC", key="arc_btn_gc_done",
                         disabled=state.get("gc_finished") or not state.get("gc_started"),
                         use_container_width=True):
                _run_arc_action("finish_gc")
        b3, b4 = st.columns(2)
        with b3:
            if st.button("记录产气量", key="arc_btn_gas_vol",
                         disabled=state.get("gas_volume_calculated") or not state.get("gc_finished"),
                         use_container_width=True):
                try:
                    ok, msg = perform_action("calculate_gas_volume")
                    if ok and not active_gas_volume_formula.empty:
                        st.session_state["interactive_gas_volume"] = calculate_gas_volume_from_params({"validated_rows": len(active_gas_volume_formula)})
                except Exception:
                    LOGGER.exception("Gas volume action failed")
                    st.warning("产气量记录失败，请检查 GC 是否已完成。")
                    ok, msg = False, ""
                _record_action_assessment("arc", "calculate_gas_volume", ok, msg)
                _handle_action_result(ok, msg)
        with b4:
            lel_ready_arc = state.get("gas_volume_calculated") and not state.get("lel_calculated")
            if st.button("计算可燃风险", key="arc_btn_lel",
                         disabled=state.get("lel_calculated") or not state.get("gas_volume_calculated"),
                         type="primary" if lel_ready_arc else "secondary",
                         use_container_width=True):
                try:
                    ok, msg = perform_action("calculate_lel")
                    if ok:
                        _run_lel_calculation(get_experiment_state(), gas_df, lfl_dict)
                except Exception:
                    LOGGER.exception("LFL action failed")
                    st.warning("可燃风险评价失败，请检查产气量记录和气体组成数据。")
                    ok, msg = False, ""
                _record_action_assessment("arc", "calculate_lel", ok, msg)
                _handle_action_result(ok, msg)

    # ── 报告 ──
    with st.container(border=True):
        st.caption("📊 实验报告")
        rpt_ready_arc = state.get("lel_calculated") and state.get("current_state") != "report_generated"
        if st.button("📝 生成实验报告", key="arc_btn_rpt",
                     disabled=state.get("current_state") == "report_generated" or not state.get("lel_calculated"),
                     type="primary" if rpt_ready_arc else "secondary",
                     use_container_width=True):
            try:
                ok, msg = perform_action("generate_report")
            except Exception:
                LOGGER.exception("ARC report action failed")
                st.warning("报告生成失败，请检查可燃风险评价是否已完成。")
                ok, msg = False, ""
            _record_action_assessment("arc", "generate_report", ok, msg)
            if ok:
                st.session_state["interactive_experiment_last"] = {
                    "experiment_state": get_experiment_state().copy(),
                    "score_summary": calculate_final_score(get_experiment_state()),
                    "active_dataset": dataset_config,
                }
            _handle_action_result(ok, msg)

    if st.button("🔄 重置实验", key="arc_btn_reset", use_container_width=True):
        reset_experiment()
        reset_assessment("arc")
        st.rerun()

# ── 底部：DAQ / 曲线 / 采样 / GC / LFL / 考核 / 报告 ──
st.markdown("---")
arc_daq_tab, arc_curve_tab, arc_sample_tab, arc_gc_tab, arc_lel_tab, arc_assess_tab, arc_report_tab = st.tabs(
    ["实时 DAQ 数据采集仪", "曲线", "采样记录", "GC 组分", "LFL 解释", "考核记录", "报告摘要"]
)
with arc_daq_tab:
    render_section_title("数据采集监控终端", "DAQ 数据采集仪实时显示")
    d1, d2 = st.columns([1, 1])
    with d1:
        render_monitor_screen(
            t2=float(state.get("temperature", 25.0) or 25.0),
            pressure=float(state.get("pressure", 101.3) or 101.3),
            heating_rate=float(state.get("heating_rate", 0.0) or 0.0),
            gc_done=state.get("gc_finished", False),
        )
    with d2:
        render_logbook(state.get("operation_logs", []) or [])
with arc_curve_tab:
    st.caption("教学插值曲线，非文献原始数据。")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(plot_temperature_curve(arc_curve, theme_mode), use_container_width=True)
        st.plotly_chart(plot_heating_rate_curve(arc_curve, theme_mode), use_container_width=True)
    with c2:
        st.plotly_chart(plot_pressure_curve(pressure_curve, theme_mode), use_container_width=True)
with arc_sample_tab:
    sample_rows = [
        {"节点": "冷却后连接集气袋", "状态": "完成" if state.get("gas_bag_connected") else "待完成", "说明": "仅为虚拟采样链条记录。"},
        {"节点": "打开采样阀", "状态": "完成" if state.get("sampling_started") else "待完成", "说明": "用于展示管路状态，不指导真实采样。"},
        {"节点": "关闭采样阀", "状态": "完成" if state.get("gas_bag_filled") else ("待关闭" if state.get("sampling_valve_open") else "待完成"), "说明": "关闭后采样流程进入完成状态。"},
        {"节点": "采样完成", "状态": "完成" if state.get("gas_bag_filled") else "待完成", "说明": "完成后方可进入 GC 教学分析。"},
    ]
    st.dataframe(pd.DataFrame(sample_rows), use_container_width=True, hide_index=True)
with arc_gc_tab:
    if state.get("gc_finished"):
        st.caption("教学模拟 GC 色谱峰。")
        st.plotly_chart(plot_gc_chromatogram(peaks_df, theme_mode), use_container_width=True) if not peaks_df.empty else st.warning("暂无色谱数据")
        sample = _select_sample(gas_df, state.get("selected_soc"))
        composition = _extract_composition(sample)
        st.plotly_chart(plot_gas_composition_bar(composition, set(lfl_dict.keys()), "GC 气体组成", theme_mode), use_container_width=True)
    else:
        st.info("GC 分析完成后显示色谱峰和气体组成。")
with arc_lel_tab:
    if state.get("lel_calculated") or "interactive_lel_result" in st.session_state:
        lel_result = st.session_state.get("interactive_lel_result") or _run_lel_calculation(state, gas_df, lfl_dict)
        render_section_title("教学风险评价结果", "Le Chatelier 混合规则 · 均匀混合假设")
        r1, r2 = st.columns([1, 1])
        with r1:
            render_risk_badge(lel_result["risk_info"]["level"])
            st.plotly_chart(plot_risk_gauge(lel_result["risk_ratio"], theme_mode=theme_mode), use_container_width=True)
            st.caption(lel_result["statement"])
        with r2:
            risk_df = pd.DataFrame([
                {"step": "采样前", "risk_ratio": 0.0},
                {"step": "GC 完成", "risk_ratio": 0.0},
                {"step": "可燃风险评价", "risk_ratio": (st.session_state.get("interactive_lel_result") or {}).get("risk_ratio", 0.0) or 0.0},
            ])
            st.plotly_chart(plot_lel_risk_timeline(risk_df, theme_mode), use_container_width=True)
    else:
        st.info("完成 GC 和产气量记录后进入 LFL_mix 可燃风险评价。")
        render_asset_image("assets/mechanism/08_lel_risk_evaluation.png", "LFL_mix 可燃风险解释示意。", "可燃风险解释")
with arc_assess_tab:
    _render_assessment_panel("arc")
with arc_report_tab:
    render_section_title("实验记录本", "自动记录每步操作")
    render_logbook(state.get("operation_logs", []) or [])
    st.dataframe(pd.DataFrame(assessment_summary("arc")["suggestions"], columns=["学习建议"]), use_container_width=True, hide_index=True)

# ── 重置按钮 ──
if st.button("🔄 重置实验全部数据", key="arc_btn_reset_bottom", use_container_width=True):
    reset_experiment()
    reset_assessment("arc")
    st.rerun()

render_global_footer()
