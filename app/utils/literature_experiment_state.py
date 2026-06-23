"""文献装置模式状态机。

该模块服务于防爆舱-加热模块产气实验的二维教学仿真。
状态和数值只用于流程演示、数据回放和风险评价训练。
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime

import streamlit as st


LITERATURE_SOC_OPTIONS = [0, 25, 50, 75, 100]

SAMPLING_STAGES = [
    ("t2_100", "T2=100℃"),
    ("venting", "喷阀"),
    ("temperature_peak", "热失控温度峰值"),
    ("pressure_stable", "反应结束 / 压力稳定"),
]

INITIAL_LITERATURE_EXPERIMENT_STATE = {
    "experiment_mode": "literature_explosion_chamber_heating",
    "current_state": "soc_selection",
    "selected_soc": None,
    "cell_loaded": False,
    "thermocouples_placed": False,
    "voltage_leads_connected": False,
    "pressure_sensor_checked": False,
    "chamber_door_closed": False,
    "vacuum_done": False,
    "nitrogen_filled": False,
    "heating_started": False,
    "t2_reached_100": False,
    "venting_detected": False,
    "thermal_runaway_triggered": False,
    "temperature_peak_reached": False,
    "pressure_stable": False,
    "sampling_completed": {
        "t2_100": False,
        "venting": False,
        "temperature_peak": False,
        "pressure_stable": False,
    },
    "gc_started": False,
    "gc_finished": False,
    "gas_composition_viewed": False,
    "gas_trends_viewed": False,
    "lel_risk_evaluated": False,
    "report_generated": False,
    "temperature_t1_c": 25.0,
    "temperature_t2_c": 25.0,
    "temperature_t3_c": 25.0,
    "pressure_kpa": 101.3,
    "voltage_v": 3.22,
    "heating_power_w": 0,
    "score": 100,
    "error_count": 0,
    "operation_logs": [],
    "data_source_notes": [
        "装置流程依据曾垂辉等 2026 文献描述整理，用于二维教学仿真。",
        "表 1 和表 2 已录入明确给出的文献数据；表 3 组分数值未提供时保持 pending_user_input。",
        "未数字化图 3、图 5、图 6、图 7 曲线。",
    ],
}


def initial_literature_experiment_state() -> dict:
    """返回文献装置模式初始状态副本。"""
    return deepcopy(INITIAL_LITERATURE_EXPERIMENT_STATE)


def init_literature_session_state() -> None:
    """初始化 Streamlit session_state。"""
    if "literature_experiment" not in st.session_state:
        st.session_state["literature_experiment"] = initial_literature_experiment_state()


def get_literature_experiment_state() -> dict:
    """读取 Streamlit 中的文献模式状态。"""
    init_literature_session_state()
    return st.session_state["literature_experiment"]


def reset_literature_experiment() -> None:
    """重置文献装置模式。"""
    st.session_state["literature_experiment"] = initial_literature_experiment_state()
    for key in [
        "literature_lel_result",
        "literature_gas_volume",
        "literature_gc_result",
        "literature_daq_result",
        "literature_report_status",
        "interactive_experiment_last",
    ]:
        st.session_state.pop(key, None)


def _sampling_done(state: dict) -> bool:
    return all(bool(v) for v in state.get("sampling_completed", {}).values())


def _log(state: dict, action: str, message: str, level: str = "info") -> None:
    state.setdefault("operation_logs", []).insert(
        0,
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "action": action,
            "message": message,
            "level": level,
        },
    )


def _deny(state: dict, action: str, message: str) -> tuple[dict, bool, str]:
    new_state = deepcopy(state)
    new_state["score"] = max(0, int(new_state.get("score", 100)) - 3)
    new_state["error_count"] = int(new_state.get("error_count", 0)) + 1
    _log(new_state, action, f"{message}（教学提示：请按文献装置流程完成前置条件。）", "error")
    return new_state, False, message


def can_perform_literature_action(state: dict, action: str, payload: dict | None = None) -> tuple[bool, str]:
    """判断文献装置模式动作是否允许。"""
    payload = payload or {}
    s = state
    if action == "select_soc":
        if s.get("cell_loaded"):
            return False, "电池已放入，本轮不能再更改 SOC。"
        soc = payload.get("soc")
        if soc not in LITERATURE_SOC_OPTIONS:
            return False, "SOC 必须为 0、25、50、75 或 100%。"
    if action == "load_prismatic_cell" and s.get("selected_soc") is None:
        return False, "未选择 SOC，不能放入方壳 LFP 电池。"
    if action == "place_thermocouples" and not s.get("cell_loaded"):
        return False, "未放入电池，不能布置 T1/T2/T3 热电偶。"
    if action == "connect_voltage_leads" and not s.get("thermocouples_placed"):
        return False, "未布置热电偶，不能连接电压采集线。"
    if action == "check_pressure_sensor" and not s.get("voltage_leads_connected"):
        return False, "未连接电压采集线，不能进行压力传感器检查。"
    if action == "close_chamber_door":
        if not s.get("thermocouples_placed"):
            return False, "未布置热电偶，不能关闭防爆舱门。"
        if not s.get("pressure_sensor_checked"):
            return False, "未检查压力传感器，不能关闭防爆舱门。"
        if s.get("chamber_door_closed"):
            return False, "防爆舱门已关闭。"
    if action == "start_vacuum" and not s.get("chamber_door_closed"):
        return False, "防爆舱门未关闭，不能抽真空。"
    if action == "fill_nitrogen" and not s.get("vacuum_done"):
        return False, "未完成抽真空，不能充入氮气至大气压。"
    if action == "start_heating" and not s.get("nitrogen_filled"):
        return False, "未完成氮气置换，不能启动加热教学演示。"
    if action == "observe_t2_100" and not s.get("heating_started"):
        return False, "未启动加热教学演示，不能观察 T2=100℃节点。"
    if action == "sample_t2_100" and not s.get("t2_reached_100"):
        return False, "T2 未达到 100℃，不能进行第一次采气。"
    if action == "observe_venting" and not s.get("sampling_completed", {}).get("t2_100"):
        return False, "第一次采气未完成，不能进入喷阀采气节点。"
    if action == "sample_venting" and not s.get("venting_detected"):
        return False, "尚未检测到安全阀喷阀，不能进行第二次采气。"
    if action == "observe_temperature_peak" and not s.get("sampling_completed", {}).get("venting"):
        return False, "第二次采气未完成，不能进入温度峰值节点。"
    if action == "observe_temperature_peak" and s.get("selected_soc") == 0:
        return False, "0%SOC 可出现安全阀喷阀，但参考事实不支持将其强行推进为热失控温度峰值。"
    if action == "sample_temperature_peak" and not s.get("temperature_peak_reached"):
        return False, "温度峰值尚未达到，不能进行第三次采气。"
    if action == "observe_pressure_stable" and not s.get("sampling_completed", {}).get("temperature_peak"):
        return False, "第三次采气未完成，不能进入压力稳定节点。"
    if action == "sample_pressure_stable" and not s.get("pressure_stable"):
        return False, "舱内压力尚未稳定，不能进行第四次采气。"
    if action == "start_gc" and not _sampling_done(s):
        return False, "四个阶段采气未全部完成，不能送入 GC 分析。"
    if action == "finish_gc" and not s.get("gc_started"):
        return False, "GC 分析尚未启动，不能完成 GC。"
    if action in {"view_gas_composition", "view_gas_trends"} and not s.get("gc_finished"):
        return False, "GC 未完成，不能查看气体组成或阶段变化。"
    if action == "evaluate_lel_risk" and not s.get("gc_finished"):
        return False, "未完成 GC，不能进行可燃风险评价。"
    if action == "generate_report" and not s.get("lel_risk_evaluated"):
        return False, "未完成可燃风险评价，不能生成文献装置模式报告。"
    return True, "可以执行。"


def perform_literature_action(
    state: dict,
    action: str,
    payload: dict | None = None,
) -> tuple[dict, bool, str]:
    """执行文献装置模式动作，返回新状态。"""
    payload = payload or {}
    ok, message = can_perform_literature_action(state, action, payload)
    if not ok:
        return _deny(state, action, message)

    s = deepcopy(state)
    if action == "select_soc":
        s["selected_soc"] = payload.get("soc")
        message = f"已选择 SOC：{s['selected_soc']}%。"
    elif action == "load_prismatic_cell":
        s["cell_loaded"] = True
        s["current_state"] = "cell_loaded"
        message = "方壳 LFP 电池样品已放入防爆舱。"
    elif action == "place_thermocouples":
        s["thermocouples_placed"] = True
        s["current_state"] = "sensors_placed"
        message = "T1/T2/T3 热电偶已布置。"
    elif action == "connect_voltage_leads":
        s["voltage_leads_connected"] = True
        message = "电压采集线已连接。"
    elif action == "check_pressure_sensor":
        s["pressure_sensor_checked"] = True
        message = "压力传感器和舱内压力表检查完成。"
    elif action == "close_chamber_door":
        s["chamber_door_closed"] = True
        s["current_state"] = "chamber_closed"
        message = "防爆舱门已关闭。"
    elif action == "start_vacuum":
        s["vacuum_done"] = True
        s["current_state"] = "vacuuming"
        s["pressure_kpa"] = 8.0
        message = "抽真空完成，压力下降为教学显示值。"
    elif action == "fill_nitrogen":
        s["nitrogen_filled"] = True
        s["current_state"] = "nitrogen_filled"
        s["pressure_kpa"] = 101.3
        message = "已充入氮气至大气压，舱内气氛标记为 N₂。"
    elif action == "start_heating":
        s["heating_started"] = True
        s["current_state"] = "heating"
        s["heating_power_w"] = 440
        s["temperature_t2_c"] = 80.0
        message = "加热教学演示已启动，进入温度观察阶段。"
    elif action == "observe_t2_100":
        s["t2_reached_100"] = True
        s["current_state"] = "t2_100"
        s["temperature_t2_c"] = 100.0
        message = "T2 已达到 100℃，提示第一次采气。"
    elif action == "sample_t2_100":
        s["sampling_completed"]["t2_100"] = True
        message = "第一次采气完成：T2=100℃阶段。"
    elif action == "observe_venting":
        s["venting_detected"] = True
        s["current_state"] = "venting"
        s["temperature_t2_c"] = 145.0
        s["pressure_kpa"] = 118.0
        message = "检测到安全阀喷阀，提示第二次采气。"
    elif action == "sample_venting":
        s["sampling_completed"]["venting"] = True
        message = "第二次采气完成：喷阀阶段。"
    elif action == "observe_temperature_peak":
        s["thermal_runaway_triggered"] = True
        s["temperature_peak_reached"] = True
        s["current_state"] = "temperature_peak"
        s["temperature_t2_c"] = 260.0
        s["pressure_kpa"] = 138.0
        message = "热失控温度峰值已标记，提示第三次采气。"
    elif action == "sample_temperature_peak":
        s["sampling_completed"]["temperature_peak"] = True
        message = "第三次采气完成：热失控温度峰值阶段。"
    elif action == "observe_pressure_stable":
        s["pressure_stable"] = True
        s["current_state"] = "pressure_stable"
        s["temperature_t2_c"] = 80.0
        s["pressure_kpa"] = 103.0
        message = "舱内压力已稳定，提示第四次采气。"
    elif action == "sample_pressure_stable":
        s["sampling_completed"]["pressure_stable"] = True
        s["current_state"] = "sampling_complete"
        message = "第四次采气完成：反应结束 / 压力稳定阶段。"
    elif action == "start_gc":
        s["gc_started"] = True
        s["current_state"] = "gc_analysis"
        message = "GC 气相色谱分析已启动。"
    elif action == "finish_gc":
        s["gc_finished"] = True
        message = "GC 分析完成，可查看气体组成与阶段变化。"
    elif action == "view_gas_composition":
        s["gas_composition_viewed"] = True
        message = "已查看阶段性气体组成表。"
    elif action == "view_gas_trends":
        s["gas_trends_viewed"] = True
        message = "已查看 H2 / CO2 / CO / 碳氢化合物阶段变化。"
    elif action == "evaluate_lel_risk":
        s["lel_risk_evaluated"] = True
        s["current_state"] = "lel_risk_evaluation"
        message = "LFL_mix 可燃风险评价已完成。"
    elif action == "generate_report":
        s["report_generated"] = True
        s["current_state"] = "report_generated"
        message = "文献装置模式报告记录已生成。"
    else:
        return _deny(state, action, "未知动作，无法执行。")

    _log(s, action, message, "info")
    return s, True, message


def perform_literature_session_action(action: str, payload: dict | None = None) -> tuple[bool, str]:
    """对 Streamlit session_state 执行动作。"""
    state = get_literature_experiment_state()
    new_state, ok, message = perform_literature_action(state, action, payload)
    st.session_state["literature_experiment"] = new_state
    return ok, message
