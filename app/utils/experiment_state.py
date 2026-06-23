"""二维交互实验状态机。

所有操作均为虚拟教学演示，不提供真实危险实验操作指导。
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime

import streamlit as st

from app.utils.scoring import score_action


INITIAL_EXPERIMENT_STATE = {
    "current_state": "sample_preparation",
    "selected_soc": None,
    "battery_loaded": False,
    "arc_door_closed": False,
    "leak_test_passed": False,
    "replacement_count": 0,
    "vacuum_valve_open": False,
    "nitrogen_valve_open": False,
    "sampling_valve_open": False,
    "vacuum_pump_on": False,
    "cycle_vacuum_done": False,
    "cycle_nitrogen_done": False,
    "gas_bag_connected": False,
    "gas_bag_filled": False,
    "sampling_started": False,
    "gc_started": False,
    "gc_finished": False,
    "ms_started": False,
    "ms_finished": False,
    "computer_result_ready": False,
    "gas_volume_calculated": False,
    "lel_calculated": False,
    "temperature": 25.0,
    "pressure": 101.3,
    "heating_rate": 0.0,
    "elapsed_time": 0.0,
    "score": 100,
    "error_count": 0,
    "operation_logs": [],
    "data_source_notes": [
        "压力变化为教学可视化模拟数据，非文献原始曲线。",
        "ARC 曲线为教学插值 / 模拟曲线，非文献原始数据。",
    ],
}


def init_experiment_session_state() -> None:
    """初始化 Streamlit session_state 中的实验状态。"""
    if "experiment" not in st.session_state:
        st.session_state["experiment"] = deepcopy(INITIAL_EXPERIMENT_STATE)


def get_experiment_state() -> dict:
    """返回当前实验状态。"""
    init_experiment_session_state()
    return st.session_state["experiment"]


def reset_experiment() -> None:
    """重置实验。"""
    st.session_state["experiment"] = deepcopy(INITIAL_EXPERIMENT_STATE)
    for key in [
        "interactive_lel_result",
        "interactive_gas_volume",
        "interactive_experiment_last",
        "interactive_gc_result",
        "interactive_daq_result",
        "interactive_report_status",
    ]:
        st.session_state.pop(key, None)


def add_operation_log(action: str, message: str, level: str = "info", severity: str = "normal") -> None:
    """写入操作日志。"""
    state = get_experiment_state()
    state["operation_logs"].insert(
        0,
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "action": action,
            "message": message,
            "level": level,
            "severity": severity,
        },
    )


def add_score(delta: int, reason: str) -> None:
    """调整评分。"""
    state = get_experiment_state()
    state["score"] = max(0, min(100, int(state.get("score", 100)) + int(delta)))
    if delta < 0:
        state["error_count"] = int(state.get("error_count", 0)) + 1
        add_operation_log("score", f"{reason}，扣 {abs(delta)} 分。", "error")


def _deny(action: str, message: str, severity: str = "normal") -> tuple[bool, str]:
    delta = score_action(action, False, severity)
    state = get_experiment_state()
    state["score"] = max(0, int(state.get("score", 100)) + delta)
    state["error_count"] = int(state.get("error_count", 0)) + 1
    add_operation_log(action, f"{message}（教学提示：请按实验链条完成前置条件。）", "error", severity)
    return False, message


def can_perform_action(action: str) -> tuple[bool, str]:
    """判断动作是否可执行。"""
    s = get_experiment_state()
    if action == "select_soc" and s.get("battery_loaded"):
        return False, "电池已装入，本轮实验不能再更改 SOC。"
    if action == "load_battery" and not s.get("selected_soc"):
        return False, "未选择 SOC，不能装入电池。"
    if action == "load_battery" and s.get("battery_loaded"):
        return False, "电池已装入，请继续完成舱门、气密性和置换流程。"
    if action == "close_arc_door" and not s.get("battery_loaded"):
        return False, "未装入电池，不能关闭 ARC 舱门。"
    if action == "close_arc_door" and s.get("arc_door_closed"):
        return False, "ARC 舱门已关闭，请继续进行气密性检测。"
    if action == "start_leak_test" and not s.get("arc_door_closed"):
        return False, "ARC 舱门未关闭，不能进行气密性检测。"
    if action == "start_leak_test" and s.get("leak_test_passed"):
        return False, "气密性检测已通过，请进入 20 L 罐置换准备。"
    if action in {"open_vacuum_valve", "start_vacuum_pump"} and not s.get("leak_test_passed"):
        return False, "未完成气密性检测，不能开始抽真空。"
    if action == "open_vacuum_valve" and s.get("vacuum_valve_open"):
        return False, "真空阀已经打开，请启动真空泵或关闭真空阀。"
    if action == "open_vacuum_valve" and s.get("nitrogen_valve_open"):
        return False, "氮气阀未关闭，不能打开真空阀。"
    if action == "start_vacuum_pump" and not s.get("vacuum_valve_open"):
        return False, "未打开真空阀，不能启动真空泵。"
    if action == "start_vacuum_pump" and s.get("vacuum_pump_on"):
        return False, "真空泵已启动，请观察压力下降后关闭真空阀。"
    if action == "close_vacuum_valve" and not s.get("vacuum_valve_open"):
        return False, "真空阀未打开，不能执行关闭真空阀。"
    if action == "open_nitrogen_valve" and s.get("vacuum_valve_open"):
        return False, "真空阀未关闭，不能打开氮气阀。"
    if action == "open_nitrogen_valve" and not s.get("cycle_vacuum_done"):
        return False, "本轮尚未完成抽真空，不能打开氮气阀。"
    if action == "open_nitrogen_valve" and s.get("nitrogen_valve_open"):
        return False, "氮气阀已经打开，请完成压力恢复后关闭氮气阀。"
    if action == "close_nitrogen_valve" and not s.get("nitrogen_valve_open"):
        return False, "氮气阀未打开，不能执行关闭氮气阀。"
    if action == "complete_replacement_cycle" and (
        not s.get("cycle_vacuum_done") or not s.get("cycle_nitrogen_done")
    ):
        return False, "本轮抽真空和氮气回填未完整完成，不能计入置换次数。"
    if action == "start_arc" and s.get("replacement_count", 0) < 3:
        return False, "抽真空 / 氮气置换不足三次，不能启动 ARC。"
    if action == "start_arc" and not (s.get("arc_door_closed") and s.get("leak_test_passed")):
        return False, "ARC 舱门和气密性检测未完成，不能启动 ARC。"
    if action == "start_arc" and s.get("current_state") != "arc_ready":
        return False, "当前状态不是 ARC 就绪，不能启动 ARC。"
    if action == "finish_arc_heating" and s.get("current_state") != "arc_heating":
        return False, "ARC 尚未处于升温阶段，不能完成升温。"
    if action == "trigger_thermal_runaway" and s.get("current_state") != "arc_heating":
        return False, "未完成 ARC 升温阶段，不能进入热失控演示。"
    if action == "finish_cooling" and s.get("current_state") != "thermal_runaway":
        return False, "未进入热失控演示阶段，不能直接完成冷却。"
    if action in {"connect_gas_bag", "open_sampling_valve"} and s.get("current_state") not in {"cooling", "gas_sampling"}:
        return False, "未冷却完成，不能采样。"
    if action == "connect_gas_bag" and s.get("gas_bag_connected"):
        return False, "集气袋已连接，请继续打开采样阀。"
    if action == "open_sampling_valve" and not s.get("gas_bag_connected"):
        return False, "未连接集气袋，不能打开采样阀。"
    if action == "open_sampling_valve" and s.get("sampling_valve_open"):
        return False, "采样阀已打开，请完成采样后关闭采样阀。"
    if action == "close_sampling_valve" and not s.get("sampling_valve_open"):
        return False, "采样阀未打开，不能完成采样。"
    if action == "start_gc" and not s.get("gas_bag_filled"):
        return False, "未完成采样，不能进行 GC 分析。"
    if action == "start_gc" and s.get("gc_started"):
        return False, "GC 分析已启动，请等待完成分析。"
    if action == "finish_gc" and not s.get("gc_started"):
        return False, "GC 尚未启动，不能完成 GC。"
    if action == "finish_gc" and s.get("gc_finished"):
        return False, "GC 分析已完成，请进入产气量计算状态记录。"
    if action == "calculate_gas_volume" and not s.get("gc_finished"):
        return False, "未完成 GC 分析，不能计算产气量。"
    if action == "calculate_gas_volume" and s.get("gas_volume_calculated"):
        return False, "产气量计算状态已记录，请继续进行可燃风险评价。"
    if action == "calculate_lel" and not s.get("gas_volume_calculated"):
        return False, "未完成产气量计算，不能进行可燃风险评价。"
    if action == "calculate_lel" and s.get("lel_calculated"):
        return False, "可燃风险评价已完成，请生成报告。"
    if action == "generate_report" and not s.get("lel_calculated"):
        return False, "未完成可燃风险评价，不能生成完整实验报告。"
    if action == "generate_report" and s.get("current_state") == "report_generated":
        return False, "实验报告已生成，本轮流程已完成。"
    return True, "可以执行。"


def perform_action(action: str, payload: dict | None = None) -> tuple[bool, str]:
    """执行动作并推进状态。"""
    payload = payload or {}
    ok, message = can_perform_action(action)
    if not ok:
        severity = "normal"
        if action == "start_arc":
            severity = "replacement"
        elif action == "open_sampling_valve":
            severity = "cooling"
        elif action in {"open_vacuum_valve", "start_vacuum_pump"}:
            severity = "leak_test"
        return _deny(action, message, severity)

    s = get_experiment_state()
    if action == "select_soc":
        s["selected_soc"] = payload.get("soc", s.get("selected_soc"))
        message = f"已选择 SOC：{s['selected_soc']}%。"
    elif action == "load_battery":
        s["battery_loaded"] = True
        s["current_state"] = "battery_loaded"
        message = "电池样品已装入虚拟 ARC 实验腔。"
    elif action == "close_arc_door":
        s["arc_door_closed"] = True
        message = "ARC 舱门已关闭。"
    elif action == "start_leak_test":
        s["leak_test_passed"] = True
        s["current_state"] = "leak_test"
        message = "气密性检测通过。"
    elif action == "open_vacuum_valve":
        s["vacuum_valve_open"] = True
        s["current_state"] = "vacuuming"
        message = "真空阀已打开。"
    elif action == "start_vacuum_pump":
        s["vacuum_pump_on"] = True
        s["cycle_vacuum_done"] = True
        s["pressure"] = 12.0
        message = "真空泵已启动，压力下降为教学模拟低压。"
    elif action == "close_vacuum_valve":
        s["vacuum_valve_open"] = False
        s["vacuum_pump_on"] = False
        message = "真空阀已关闭。"
    elif action == "open_nitrogen_valve":
        s["nitrogen_valve_open"] = True
        s["current_state"] = "nitrogen_filling"
        s["pressure"] = 101.3
        message = "氮气阀已打开，压力恢复至教学模拟常压。"
    elif action == "close_nitrogen_valve":
        s["nitrogen_valve_open"] = False
        s["cycle_nitrogen_done"] = True
        s["current_state"] = "atmosphere_replacement"
        message = "氮气阀已关闭。"
    elif action == "complete_replacement_cycle":
        if s.get("nitrogen_valve_open") or s.get("vacuum_valve_open"):
            return _deny(action, "阀门未关闭，不能完成本轮置换。", "critical")
        s["replacement_count"] = int(s.get("replacement_count", 0)) + 1
        s["cycle_vacuum_done"] = False
        s["cycle_nitrogen_done"] = False
        s["current_state"] = "arc_ready" if s["replacement_count"] >= 3 else "atmosphere_replacement"
        message = f"已完成第 {s['replacement_count']} 轮抽真空 / 氮气置换。"
    elif action == "start_arc":
        s["current_state"] = "arc_heating"
        s["temperature"] = 120.0
        s["heating_rate"] = 1.8
        message = "ARC 虚拟升温阶段已启动。"
    elif action == "finish_arc_heating":
        s["current_state"] = "arc_heating"
        s["temperature"] = 180.0
        s["heating_rate"] = 3.2
        message = "ARC 虚拟升温阶段完成。"
    elif action == "trigger_thermal_runaway":
        s["current_state"] = "thermal_runaway"
        s["temperature"] = 260.0
        s["pressure"] = 135.0
        s["heating_rate"] = 9.5
        message = "已进入热失控高亮演示阶段。"
    elif action == "finish_cooling":
        s["current_state"] = "cooling"
        s["temperature"] = 35.0
        s["pressure"] = 103.0
        s["heating_rate"] = 0.0
        message = "冷却完成，可进入采样教学环节。"
    elif action == "connect_gas_bag":
        s["gas_bag_connected"] = True
        s["current_state"] = "gas_sampling"
        message = "集气袋已连接。"
    elif action == "open_sampling_valve":
        s["sampling_valve_open"] = True
        s["sampling_started"] = True
        message = "采样阀已打开，采样管路高亮。"
    elif action == "close_sampling_valve":
        s["sampling_valve_open"] = False
        s["gas_bag_filled"] = True
        message = "采样阀已关闭，集气袋采样完成。"
    elif action == "start_gc":
        s["current_state"] = "gc_analysis"
        s["gc_started"] = True
        message = "GC 教学分析已启动。"
    elif action == "finish_gc":
        s["gc_finished"] = True
        s["ms_started"] = True
        s["ms_finished"] = True
        s["computer_result_ready"] = True
        message = "GC-MS 分析完成，色谱峰、质谱识别和电脑组分结果可查看。"
    elif action == "calculate_gas_volume":
        s["gas_volume_calculated"] = True
        s["current_state"] = "gas_volume_calculation"
        message = "产气量计算状态已记录为待补充文献公式。"
    elif action == "calculate_lel":
        s["lel_calculated"] = True
        s["current_state"] = "lel_risk_evaluation"
        message = "LFL_mix 与可燃风险评价已完成。"
    elif action == "generate_report":
        s["current_state"] = "report_generated"
        message = "实验报告记录已生成。"
    else:
        return _deny(action, "未知动作，无法执行。", "normal")
    add_operation_log(action, message, "info")
    return True, message
