"""Assessment and consequence engine for the interactive lab."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

import streamlit as st


ASSESSMENT_INITIAL_STATE = {
    "score": 100,
    "events": [],
    "correct_actions": [],
    "deductions": [],
    "consequences": [],
    "invalid_samples": [],
    "sample_status": {},
    "last_alert": None,
    "latest_violation": None,
    "latest_severe_warning": {"active": False},
    "violation_history": [],
    "data_valid": True,
    "safety_status": "规范",
}

ACTION_LABELS = {
    "select_soc": "选择 SOC",
    "load_battery": "装入电池",
    "load_prismatic_cell": "放入方壳 LFP 电池",
    "place_thermocouples": "布置热电偶",
    "connect_voltage_leads": "连接电压采集线",
    "check_pressure_sensor": "检查压力传感器",
    "close_arc_door": "关闭 ARC 舱门",
    "close_chamber_door": "关闭防爆舱门",
    "start_leak_test": "气密性检测",
    "open_vacuum_valve": "打开真空阀",
    "start_vacuum_pump": "启动真空泵",
    "start_vacuum": "抽真空",
    "fill_nitrogen": "充入氮气",
    "start_heating": "启动加热演示",
    "start_arc": "启动 ARC",
    "trigger_thermal_runaway": "进入热失控演示",
    "sample_t2_100": "第一次采气",
    "sample_venting": "第二次采气",
    "sample_temperature_peak": "第三次采气",
    "sample_pressure_stable": "第四次采气",
    "start_gc": "启动 GC",
    "finish_gc": "完成 GC",
    "calculate_gas_volume": "记录产气量",
    "calculate_lel": "计算可燃风险",
    "evaluate_lel_risk": "计算可燃风险",
    "generate_report": "生成实验报告",
}

CONSEQUENCE_RULES = {
    "start_vacuum": (
        "舱门未锁紧导致抽真空失败，舱体状态标记为异常。",
        "先确认样品、测点、压力传感器和舱门锁紧状态。",
        "critical",
    ),
    "start_vacuum_pump": (
        "真空链条未建立，抽真空记录被判为无效。",
        "先完成气密性检测并打开真空阀。",
        "major",
    ),
    "open_vacuum_valve": (
        "气密性证据不足，气氛控制数据可信度下降。",
        "先完成舱门关闭与气密性检测。",
        "major",
    ),
    "start_heating": (
        "气氛控制不合规，风险提示上升，本轮加热数据标记为不可评价。",
        "先完成抽真空和氮气置换，再进入教学加热阶段。",
        "critical",
    ),
    "start_arc": (
        "置换次数或安全确认不足，ARC 启动被阻止。",
        "按流程完成舱门、气密性和三轮置换确认。",
        "critical",
    ),
    "sample_t2_100": (
        "过早采样，第一次集气袋标记为无效样本。",
        "到达 T2=100℃ 教学节点后再采样。",
        "major",
    ),
    "sample_venting": (
        "过早采样，第二次集气袋标记为无效样本。",
        "确认安全阀喷阀教学节点后再采样。",
        "major",
    ),
    "sample_temperature_peak": (
        "过早采样，温度峰值阶段样本标记为无效。",
        "等待热失控温度峰值教学节点被记录。",
        "major",
    ),
    "sample_pressure_stable": (
        "过早采样，反应结束阶段样本标记为无效。",
        "舱内压力稳定后再记录第四次采气。",
        "major",
    ),
    "start_gc": (
        "GC 样本链不完整，色谱结果不能进入报告。",
        "完成全部采样节点后再启动 GC。",
        "major",
    ),
    "calculate_lel": (
        "缺少产气量或 GC 组成，LFL 教学评价被阻止。",
        "先完成 GC 分析和产气量记录。",
        "major",
    ),
    "evaluate_lel_risk": (
        "缺少 GC 组成，LFL 教学评价被阻止。",
        "先完成 GC 分析并查看气体组成。",
        "major",
    ),
    "generate_report": (
        "分析链条未闭合，报告摘要标记为待补充。",
        "完成 GC、LFL 教学评价和必要记录后生成报告。",
        "normal",
    ),
}

SEVERITY_DEDUCTION = {"normal": 2, "major": 5, "critical": 8}

ALERT_CATEGORIES = {
    "start_vacuum": "安全边界错误",
    "start_vacuum_pump": "流程错误",
    "open_vacuum_valve": "流程错误",
    "start_heating": "安全边界错误",
    "start_arc": "流程错误",
    "sample_t2_100": "采样节点错误",
    "sample_venting": "采样节点错误",
    "sample_temperature_peak": "采样节点错误",
    "sample_pressure_stable": "采样节点错误",
    "start_gc": "数据缺失",
    "calculate_lel": "风险评价错误",
    "evaluate_lel_risk": "风险评价错误",
    "generate_report": "报告生成条件不足",
}

FACT_BASED_ALERTS = {
    "start_heating": {
        "reason": "未完成抽真空和氮气置换就启动加热，偏离参考文献中防爆舱抽真空后充氮至大气压、隔绝空气的实验设定。",
        "impact": "本轮加热、产气、GC 与 LFL_mix 结果不能作为报告中的有效实验链条。",
        "correct_action": "先关闭舱门并完成真空-充氮置换，再进入外部加热触发热失控教学阶段。",
        "basis": "参考文献装置流程：密闭防爆舱内抽真空后充氮至大气压，采集温度、电压、压力和气体组分。",
    },
    "sample_t2_100": {
        "reason": "T2 尚未达到 100 ℃，SEI 膜分解和电解液初期挥发节点未达到。",
        "impact": "该样本不能代表第一次采气阶段，报告需标记为无效或待补充。",
        "correct_action": "记录 T2=100 ℃ 后再执行第一次采气。",
        "basis": "四次采气逻辑：第一次采气为 T2 达到 100 ℃、热失控初期节点。",
    },
    "sample_venting": {
        "reason": "安全阀喷阀尚未记录，过早采样不能代表喷阀后大量气体释放阶段。",
        "impact": "第二次采气样本无效，不能进入 GC/LFL 报告链条。",
        "correct_action": "确认安全阀喷阀后再执行第二次采气；喷阀不等同于必然热失控。",
        "basis": "四次采气逻辑：第二次采气为安全阀喷阀节点，0%SOC 可喷阀但未必热失控。",
    },
    "sample_temperature_peak": {
        "reason": "温度峰值尚未到达，最剧烈反应阶段未被记录。",
        "impact": "该样本不能代表最大可燃气体风险阶段。",
        "correct_action": "等待热失控温度峰值记录完成后再执行第三次采气。",
        "basis": "四次采气逻辑：第三次采气为温度达到峰值、反应最剧烈阶段。",
    },
    "sample_pressure_stable": {
        "reason": "舱内压力尚未稳定，内部反应或气体扩散过程尚未结束。",
        "impact": "第四次采气不能代表反应结束阶段，报告需标记缺失或无效。",
        "correct_action": "待压力不再变化、反应趋于完成后执行第四次采气。",
        "basis": "四次采气逻辑：第四次采气为舱内压力不再变化、内部物理化学反应趋于完成。",
    },
    "start_gc": {
        "reason": "采样链条未完成就启动 GC，缺少可追溯集气袋样本。",
        "impact": "GC 组成数据不能进入正式报告，也不能用于 LFL_mix 教学估算。",
        "correct_action": "完成规定采样节点后再启动 GC 气相色谱分析。",
        "basis": "平台教学逻辑：只有采样完成后才允许启动 GC。",
    },
    "calculate_lel": {
        "reason": "缺少 GC 组成或产气量记录，不能计算空间浓度 C 与 LFL_mix 的风险比 R。",
        "impact": "风险等级只能显示为待补充，不能写成完整结论。",
        "correct_action": "先完成 GC 数据和产气量记录，再进行 Le Chatelier 教学估算。",
        "basis": "LFL_mix 使用 Le Chatelier 混合规则；R = 空间浓度 / LFL_mix，均为教学模型。",
    },
    "evaluate_lel_risk": {
        "reason": "GC 组成尚未完成，缺少参与 LFL_mix 的可燃组分输入。",
        "impact": "风险评价不能进入报告结论。",
        "correct_action": "完成 GC 气体组分查看后再进行 LFL_mix 与 R 的教学评价。",
        "basis": "H₂、CO、CH₄、C₂H₄、C₂H₆ 等可燃组分参与 LFL_mix 教学估算。",
    },
    "generate_report": {
        "reason": "GC、LFL、采样记录或流程记录不完整。",
        "impact": "报告只能展示缺失项/待补充，不能伪造完整数据链。",
        "correct_action": "补齐采样、GC、产气量和 LFL_mix 评价记录后再生成完整报告。",
        "basis": "报告必须区分参考文献原始数据、已校验 CSV、教学演示数据和用户输入数据。",
    },
}


def _key(mode: str) -> str:
    return f"assessment_{mode}"


def init_assessment_state(mode: str) -> None:
    """Initialize assessment state for a mode."""
    st.session_state.setdefault(_key(mode), deepcopy(ASSESSMENT_INITIAL_STATE))


def get_assessment_state(mode: str) -> dict[str, Any]:
    """Return the current assessment state."""
    init_assessment_state(mode)
    return st.session_state[_key(mode)]


def reset_assessment(mode: str) -> None:
    """Reset assessment state for a mode."""
    st.session_state[_key(mode)] = deepcopy(ASSESSMENT_INITIAL_STATE)


def record_assessment_event(
    mode: str,
    action: str,
    ok: bool,
    message: str,
    *,
    severity: str | None = None,
    consequence: str = "",
    correction: str = "",
) -> dict[str, Any]:
    """Record an action result and return the updated assessment state."""
    state = get_assessment_state(mode)
    label = ACTION_LABELS.get(action, action)

    inferred_consequence, inferred_correction, inferred_severity = CONSEQUENCE_RULES.get(
        action,
        ("操作顺序不符合教学流程，系统已阻止继续推进。", "返回当前步骤提示，补齐前置条件。", "normal"),
    )
    final_severity = severity or ("normal" if ok else inferred_severity)
    fact_alert = FACT_BASED_ALERTS.get(action, {})
    event = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "action": action,
        "label": label,
        "ok": ok,
        "message": message,
        "category": ALERT_CATEGORIES.get(action, "流程错误"),
        "severity": final_severity,
        "reason": "" if ok else fact_alert.get("reason", message),
        "impact": "" if ok else fact_alert.get("impact", consequence or inferred_consequence),
        "basis": "" if ok else fact_alert.get("basis", "虚拟仿真教学流程约束"),
        "correct_action": "" if ok else fact_alert.get("correct_action", correction or inferred_correction),
        "consequence": "" if ok else fact_alert.get("impact", consequence or inferred_consequence),
        "correction": "" if ok else fact_alert.get("correct_action", correction or inferred_correction),
    }
    state["events"].insert(0, event)

    if ok:
        state["latest_violation"] = None
        state["latest_severe_warning"] = {"active": False}
        state["last_alert"] = None
        if label not in state["correct_actions"]:
            state["correct_actions"].append(label)
        return state

    deduction = SEVERITY_DEDUCTION.get(final_severity, 2)
    state["score"] = max(0, int(state.get("score", 100)) - deduction)
    state["data_valid"] = False
    if final_severity == "critical":
        state["safety_status"] = "需重做"
    elif state.get("safety_status") != "需重做":
        state["safety_status"] = "需复核"
    deduction_record = {
        "action": label,
        "points": deduction,
        "category": event["category"],
        "reason": event["reason"],
        "impact": event["impact"],
        "correct_action": event["correct_action"],
        "basis": event["basis"],
        "severity": final_severity,
    }
    state["deductions"].insert(0, deduction_record)
    state["consequences"].insert(0, event["consequence"])
    violation_record = {
        "action": label,
        "message": message,
        "category": event["category"],
        "reason": event["reason"],
        "severity": final_severity,
        "impact": event["impact"],
        "basis": event["basis"],
        "consequence": event["consequence"],
        "correction": event["correction"],
        "correct_action": event["correct_action"],
    }
    state["latest_violation"] = violation_record
    state.setdefault("violation_history", []).insert(0, violation_record)
    if final_severity in {"major", "critical"}:
        warning_record = {
            "action": label,
            "message": message,
            "category": event["category"],
            "reason": event["reason"],
            "impact": event["impact"],
            "basis": event["basis"],
            "correct_action": event["correct_action"],
            "consequence": event["consequence"],
            "severity": final_severity,
            "active": True,
        }
        state["latest_severe_warning"] = warning_record
        state["last_alert"] = warning_record
    else:
        state["latest_severe_warning"] = {"active": False}
        state["last_alert"] = None
    if action.startswith("sample_"):
        state["invalid_samples"].append(label)
        state.setdefault("sample_status", {})[action] = "无效样本"
    return state


def assessment_summary(mode: str) -> dict[str, Any]:
    """Build a display-ready assessment summary."""
    state = get_assessment_state(mode)
    score = int(state.get("score", 100))
    if score >= 90 and state.get("data_valid", True):
        grade = "优秀"
    elif score >= 80:
        grade = "良好"
    elif score >= 60:
        grade = "合格"
    else:
        grade = "需重做"

    suggestions = []
    if state.get("invalid_samples"):
        suggestions.append("复核四次采样节点，报告中标记无效或缺失样本。")
    if not state.get("data_valid", True):
        suggestions.append("补齐被阻止步骤的前置条件，再重新生成分析链条。")
    if not suggestions:
        suggestions.append("继续保持按流程记录，并在报告中说明数据来源和教学边界。")

    return {
        "score": score,
        "grade": grade,
        "valid_data": bool(state.get("data_valid", True)),
        "safety_status": state.get("safety_status", "规范"),
        "correct_actions": list(state.get("correct_actions", [])),
        "deductions": list(state.get("deductions", [])),
        "events": list(state.get("events", [])),
        "consequences": list(state.get("consequences", [])),
        "latest_violation": state.get("latest_violation"),
        "latest_severe_warning": state.get("latest_severe_warning"),
        "violation_history": list(state.get("violation_history", [])),
        "invalid_samples": list(state.get("invalid_samples", [])),
        "sample_status": dict(state.get("sample_status", {})),
        "last_alert": state.get("last_alert"),
        "suggestions": suggestions,
    }
