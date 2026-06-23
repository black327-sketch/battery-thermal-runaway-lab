"""Process-aware advice for the floating AI study companion."""

from __future__ import annotations

from typing import Any, Mapping


def _truthy(state: Mapping[str, Any], *keys: str) -> bool:
    return any(bool(state.get(key)) for key in keys)


def _sampled(state: Mapping[str, Any], key: str) -> bool:
    sampled = state.get("sampling_completed", {})
    return isinstance(sampled, Mapping) and bool(sampled.get(key))


def _warning_text(assessment: Mapping[str, Any] | None = None, trace: Mapping[str, Any] | None = None) -> str:
    parts: list[str] = []
    assessment = assessment or {}
    for key in ("last_alert", "latest_severe_warning", "latest_violation"):
        item = assessment.get(key)
        if isinstance(item, Mapping):
            parts.append(str(item.get("reason") or item.get("message") or ""))
    for item in (trace or {}).get("warning_events", []) or []:
        if isinstance(item, Mapping):
            parts.append(str(item.get("reason") or item.get("warning_category") or ""))
    return "；".join(part for part in parts if part)


def build_process_advice(
    *,
    page_name: str,
    experiment_state: Mapping[str, Any] | None = None,
    trace: Mapping[str, Any] | None = None,
    assessment: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Return a compact advice object derived only from objective progress."""

    state = experiment_state or {}
    stage = str(state.get("current_state") or "未记录")
    soc = state.get("selected_soc", "未选择")
    if soc is None or soc == "":
        soc = "未选择"
    warning = _warning_text(assessment, trace)

    if warning:
        return {
            "next_step_suggestion": "先处理当前流程提醒，再继续推进实验。",
            "safety_hint": warning,
            "learning_hint": "把报警理由和正确操作写入实验记录，有助于后续评价。",
            "risk_hint": "安全相关提示优先于流程推进。",
            "suggestion_level": "alert",
        }

    if "报告" in page_name or stage == "report_generated" or state.get("report_generated"):
        if not (_truthy(state, "gc_finished") and (_truthy(state, "lel_calculated", "lel_risk_evaluated") or state.get("lel_result"))):
            next_step = "报告生成前建议确认 GC 数据、LFL_mix 和采样记录是否完整。"
        else:
            next_step = "可以检查报告中的参考文献数据、教学演示数据和用户输入数据是否区分清楚。"
        return {
            "next_step_suggestion": next_step,
            "safety_hint": "报告中的风险等级和 LFL_mix 只能作为虚拟仿真教学估算。",
            "learning_hint": "重点复核数据来源、模型局限和安全边界声明。",
            "risk_hint": "不要把教学风险评价改写成真实工程结论。",
            "suggestion_level": "info",
        }

    if soc == "未选择":
        return {
            "next_step_suggestion": "我还没有足够操作记录，可以先从选择 SOC 和样品准备开始。",
            "safety_hint": "未选择 SOC 前不要进入装样或加热流程。",
            "learning_hint": "选择 SOC 后再观察其对产气和热失控强度的影响。",
            "risk_hint": "SOC 越高，教学数据中热失控和可燃气体风险通常更突出。",
            "suggestion_level": "idle",
        }

    if not _truthy(state, "battery_loaded", "cell_loaded"):
        next_step = "已选择 SOC，下一步可以完成样品放置，并确认测温、压力和电压采集条件。"
    elif not _truthy(state, "leak_test_passed", "chamber_door_closed"):
        next_step = "样品已准备，下一步应关闭舱门并完成气密性检查。"
    elif not (_truthy(state, "nitrogen_filled") or int(state.get("replacement_count", 0) or 0) >= 3):
        next_step = "当前还未完成真空-充氮置换，不建议进入加热步骤。"
    elif not (_truthy(state, "heating_started") or stage in {"arc_ready", "arc_heating", "heating"}):
        next_step = "你已完成氮气置换，下一步可以开始加热教学演示，并关注 T2 是否达到 100℃。"
    elif not (_truthy(state, "t2_reached_100") or _sampled(state, "t2_100")):
        next_step = "下一步关注 T2 是否达到 100℃，这是第一次采样节点。"
    elif not _sampled(state, "t2_100"):
        next_step = "T2=100℃ 已达到，下一步应完成第一次采气。"
    elif not (_truthy(state, "venting_detected") or _sampled(state, "venting")):
        next_step = "第一次采气后，继续观察安全阀喷阀节点。"
    elif not _sampled(state, "venting"):
        next_step = "已到喷阀节点，下一步应完成第二次采样。"
    elif not (_truthy(state, "temperature_peak_reached") or _sampled(state, "temperature_peak")):
        next_step = "已完成喷阀节点采样，下一步应等待温度峰值并完成第三次采样。"
    elif not _sampled(state, "temperature_peak"):
        next_step = "温度峰值已出现，下一步应完成第三次采样。"
    elif not (_truthy(state, "pressure_stable") or _sampled(state, "pressure_stable")):
        next_step = "继续等待压力稳定或反应结束，这是第四次采样的依据。"
    elif not _sampled(state, "pressure_stable"):
        next_step = "压力已稳定，下一步应完成第四次采样。"
    elif not _truthy(state, "gc_finished"):
        next_step = "四次采样完成后，下一步进入 GC 分析并查看气体组成。"
    elif not _truthy(state, "lel_calculated", "lel_risk_evaluated"):
        next_step = "GC 完成后，可以进行 LFL_mix 和 R = C / LFL_mix 教学评价。"
    else:
        next_step = "实验链条已较完整，可以进入报告生成并检查数据来源和教学边界声明。"

    return {
        "next_step_suggestion": next_step,
        "safety_hint": "所有建议仅服务虚拟仿真教学，不是真实实验操作指导。",
        "learning_hint": f"当前页面：{page_name}；当前阶段：{stage}；SOC：{soc}。",
        "risk_hint": "涉及 LFL_mix 或风险等级时，保持教学估算边界。",
        "suggestion_level": "warning" if "不建议" in next_step else "info",
    }
