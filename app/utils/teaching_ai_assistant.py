"""Rule-based local teaching assistant for the virtual experiment."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.utils.teaching_ai_knowledge import KNOWLEDGE_BASE, QUICK_QUESTIONS, SAFETY_BOUNDARY, KnowledgeEntry


STATE_LABELS = {
    "soc_selection": "SOC 选择",
    "sample_preparation": "样品准备",
    "battery_loaded": "电池已装入",
    "cell_loaded": "方壳电池已装入",
    "sensors_placed": "测点布置",
    "leak_test": "气密性检测",
    "vacuuming": "抽真空",
    "nitrogen_filled": "氮气置换完成",
    "nitrogen_filling": "氮气置换",
    "atmosphere_replacement": "气氛置换",
    "arc_ready": "ARC 就绪",
    "arc_heating": "ARC 升温",
    "heating": "加热观察",
    "t2_100": "T2=100℃",
    "venting": "安全阀喷阀",
    "thermal_runaway": "热失控教学演示",
    "temperature_peak": "温度峰值",
    "cooling": "冷却",
    "pressure_stable": "压力稳定",
    "sampling_complete": "采样完成",
    "gas_sampling": "气体采样",
    "gc_analysis": "GC 分析",
    "gas_volume_calculation": "产气量记录",
    "lel_risk_evaluation": "LFL_mix 可燃风险评价",
    "report_generated": "报告生成",
}


@dataclass(frozen=True)
class AssistantContext:
    page_name: str = "未记录页面"
    current_soc: str = "未选择"
    current_stage: str = "未记录"
    nitrogen_ready: bool = False
    t2_reached: bool = False
    vented: bool = False
    thermal_runaway: bool = False
    temperature_peak: bool = False
    pressure_stable: bool = False
    gc_finished: bool = False
    lfl_finished: bool = False
    alarm_message: str = ""
    alarm_reason: str = ""
    alarm_action: str = ""


def _truthy(mapping: Mapping[str, Any], *keys: str) -> bool:
    return any(bool(mapping.get(key)) for key in keys)


def _stage_text(stage: object) -> str:
    return STATE_LABELS.get(str(stage), str(stage or "未记录"))


def build_assistant_context(
    *,
    page_name: str,
    experiment_state: Mapping[str, Any] | None = None,
    assessment: Mapping[str, Any] | None = None,
) -> AssistantContext:
    """Build a compact assistant context from Streamlit session state objects."""

    state = experiment_state or {}
    sampled = state.get("sampling_completed", {}) if isinstance(state.get("sampling_completed"), Mapping) else {}
    alert = None
    if assessment:
        alert = assessment.get("last_alert") or assessment.get("latest_severe_warning") or assessment.get("latest_violation")
    alert = alert if isinstance(alert, Mapping) else {}

    soc = state.get("selected_soc", "未选择")
    if soc is None or soc == "":
        soc = "未选择"

    return AssistantContext(
        page_name=page_name,
        current_soc=str(soc),
        current_stage=_stage_text(state.get("current_state")),
        nitrogen_ready=_truthy(state, "nitrogen_filled") or int(state.get("replacement_count", 0) or 0) >= 3,
        t2_reached=_truthy(state, "t2_reached_100") or bool(sampled.get("t2_100")),
        vented=_truthy(state, "venting_detected") or bool(sampled.get("venting")),
        thermal_runaway=_truthy(state, "thermal_runaway_triggered") or state.get("current_state") == "thermal_runaway",
        temperature_peak=_truthy(state, "temperature_peak_reached") or bool(sampled.get("temperature_peak")),
        pressure_stable=_truthy(state, "pressure_stable") or bool(sampled.get("pressure_stable")),
        gc_finished=_truthy(state, "gc_finished"),
        lfl_finished=_truthy(state, "lel_calculated", "lel_risk_evaluated"),
        alarm_message=str(alert.get("message", "") or ""),
        alarm_reason=str(alert.get("reason", "") or ""),
        alarm_action=str(alert.get("correct_action", "") or alert.get("correction", "") or ""),
    )


def quick_questions() -> tuple[str, ...]:
    return QUICK_QUESTIONS


def stage_tip(context: AssistantContext) -> str:
    """Return a concise stage-aware hint."""

    if context.alarm_reason:
        return f"当前有报警：{context.alarm_reason} 建议：{context.alarm_action or '先补齐前置步骤。'}"
    if context.current_soc == "未选择":
        return "先选择 SOC，再进入装样和测点确认。"
    if not context.nitrogen_ready and context.current_stage not in {"报告生成", "LFL_mix 可燃风险评价"}:
        return "当前重点是完成密封、抽真空和氮气置换，之后再加热或采样。"
    if not context.t2_reached:
        return "下一项关键观察是 T2=100℃，它对应第一次采气节点。"
    if not context.vented:
        return "下一项关键观察是安全阀喷阀，它对应第二次采气节点，但不等于必然热失控。"
    if not context.temperature_peak and context.current_soc != "0":
        return "继续观察温度峰值并记录第三次采气节点。"
    if not context.pressure_stable:
        return "等待压力稳定或反应结束后，记录第四次采气。"
    if not context.gc_finished:
        return "四次采样完成后进入 GC 分析，查看气体组成。"
    if not context.lfl_finished:
        return "GC 完成后可进行 LFL_mix 和 R = C / LFL_mix 教学评价。"
    return "实验链条已接近完整，可以进入报告生成并检查数据来源和教学边界声明。"


def assistant_status(context: AssistantContext) -> str:
    if context.alarm_reason:
        return "alert"
    if context.current_stage in {"安全阀喷阀", "热失控教学演示", "温度峰值"}:
        return "warning"
    return "idle"


def _score_entry(question: str, entry: KnowledgeEntry) -> int:
    q = question.lower().replace(" ", "")
    return sum(1 for trigger in entry.triggers if trigger.lower().replace(" ", "") in q)


def _best_entry(question: str) -> KnowledgeEntry | None:
    scored = sorted(((_score_entry(question, entry), entry) for entry in KNOWLEDGE_BASE), key=lambda item: item[0], reverse=True)
    if not scored or scored[0][0] <= 0:
        return None
    return scored[0][1]


def _contextual_next_step(context: AssistantContext) -> str:
    tip = stage_tip(context)
    return f"{tip} 当前页面：{context.page_name}；当前阶段：{context.current_stage}；SOC：{context.current_soc}。"


def answer_question(question: str, context: AssistantContext | None = None) -> str:
    """Answer a student question using local rules and project knowledge."""

    context = context or AssistantContext()
    clean_question = (question or "").strip()
    if not clean_question:
        return "请先输入一个与本实验有关的问题，例如“四次采样分别代表什么？”或“LFL_mix 怎么理解？”。"

    if any(word in clean_question.lower() for word in ("灭火", "消防", "真实处置", "实际操作", "工程设计", "事故预测", "危险化学品")):
        entry = next(item for item in KNOWLEDGE_BASE if item.key == "boundary")
    elif "下一步" in clean_question or "应该做" in clean_question or "怎么继续" in clean_question:
        return (
            f"结论：{stage_tip(context)}\n\n"
            f"原因：平台按顺序检查 SOC、气氛准备、四次采样、GC、LFL_mix 和报告链条，跳步会导致数据待补充或无效。\n\n"
            f"当前实验该怎么做：{_contextual_next_step(context)}\n\n"
            f"{SAFETY_BOUNDARY}"
        )
    elif "报警" in clean_question or "告警" in clean_question:
        if context.alarm_reason:
            return (
                f"结论：当前报警来自教学流程或数据链条校验。\n\n"
                f"原因：{context.alarm_reason}\n\n"
                f"当前实验该怎么做：{context.alarm_action or '回到当前步骤提示，补齐前置条件后重试。'}\n\n"
                f"{SAFETY_BOUNDARY}"
            )
        entry = next(item for item in KNOWLEDGE_BASE if item.key == "alarm")
    else:
        entry = _best_entry(clean_question)

    if entry is None:
        return (
            "结论：当前项目资料不足，不能可靠回答这个问题。\n\n"
            "原因：助手只使用项目已有实验逻辑、报告上下文和参考文献整理事实，不扩展编造工程结论。\n\n"
            "当前实验该怎么做：请把问题限定在 SOC、四次采样、GC 组分、LFL_mix、报警理由或报告数据来源范围内。\n\n"
            f"{SAFETY_BOUNDARY}"
        )

    return (
        f"结论：{entry.conclusion}\n\n"
        f"原因：{entry.reason}\n\n"
        f"当前实验该怎么做：{entry.next_step} {_contextual_next_step(context)}\n\n"
        f"依据：{entry.basis}\n\n"
        f"{SAFETY_BOUNDARY}"
    )
