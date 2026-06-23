"""Objective learning evaluation for the AI pet companion."""

from __future__ import annotations

from typing import Any, Mapping

from app.utils.learning_trace import ensure_trace


SAFETY_FOOTER = (
    "本平台为虚拟仿真教学平台，不提供真实危险实验操作建议。真实锂离子电池热失控实验必须由"
    "具备资质的实验室、专业人员和安全规范保障。教学风险等级、LFL_mix 和报警理由不能直接作为"
    "真实工程防爆、消防处置或事故预测依据。"
)


def _count_done(state: Mapping[str, Any], keys: list[str]) -> int:
    return sum(1 for key in keys if bool(state.get(key)))


def _level_by_ratio(done: int, total: int, labels: tuple[str, str, str, str]) -> str:
    if total <= 0 or done == 0:
        return labels[0]
    ratio = done / total
    if ratio < 0.45:
        return labels[1]
    if ratio < 0.85:
        return labels[2]
    return labels[3]


def build_learning_metrics(trace: Mapping[str, Any] | None) -> dict[str, Any]:
    data = ensure_trace(trace)
    ops = data["operation_events"]
    qas = data["qa_events"]
    warnings = data["warning_events"]
    state = data["learning_state"]

    sampling_keys = [
        "sample_t2_100_done",
        "sample_venting_done",
        "sample_temperature_peak_done",
        "sample_pressure_stable_done",
    ]
    flow_keys = [
        "sample_prepared",
        "leak_test_done",
        "nitrogen_replacement_done",
        "t2_100_reached",
        *sampling_keys,
        "gc_finished",
        "lfl_mix_finished",
        "report_generated",
    ]
    invalid_ops = [op for op in ops if not op.get("is_flow_compliant", True)]
    safety_warning_count = sum(
        1
        for item in warnings
        if any(term in (item.get("warning_category", "") + item.get("reason", "")) for term in ("安全", "置换", "采样", "LFL", "风险", "防爆"))
    )
    corrected_warning_count = sum(1 for item in warnings if item.get("corrected_by_user"))
    experiment_qas = [qa for qa in qas if qa.get("is_experiment_related")]
    safety_qas = [qa for qa in qas if qa.get("is_safety_boundary_related")]

    return {
        "total_operations": len(ops),
        "valid_operations": len(ops) - len(invalid_ops),
        "invalid_operations": len(invalid_ops),
        "warning_count": len(warnings),
        "safety_warning_count": safety_warning_count,
        "corrected_warning_count": corrected_warning_count,
        "sampling_done": _count_done(state, sampling_keys),
        "sampling_total": len(sampling_keys),
        "flow_done": _count_done(state, flow_keys),
        "flow_total": len(flow_keys),
        "qa_count": len(qas),
        "experiment_qa_count": len(experiment_qas),
        "safety_qa_count": len(safety_qas),
        "gc_finished": bool(state.get("gc_finished")),
        "lfl_mix_finished": bool(state.get("lfl_mix_finished")),
        "report_generated": bool(state.get("report_generated")),
        "current_soc": state.get("current_soc", "未选择"),
        "learning_state": dict(state),
        "invalid_action_names": [str(op.get("action_name", "")) for op in invalid_ops],
        "warning_reasons": [str(item.get("reason", "")) for item in warnings],
        "qa_categories": [str(item.get("question_category", "")) for item in qas],
    }


def _suggestions(metrics: Mapping[str, Any]) -> list[str]:
    suggestions: list[str] = []
    invalid_names = set(metrics.get("invalid_action_names", []))
    warning_text = "；".join(metrics.get("warning_reasons", []))
    qa_categories = set(metrics.get("qa_categories", []))

    if metrics.get("sampling_done", 0) < metrics.get("sampling_total", 4) or any(name.startswith("sample_") for name in invalid_names):
        suggestions.append("复习四次采气节点：T2=100℃、安全阀喷阀、温度峰值、压力稳定/反应结束。")
    if "0%SOC" in warning_text or "喷阀" in warning_text or "SOC与喷阀" in qa_categories:
        suggestions.append("巩固“喷阀不等于热失控”，尤其是 0%SOC 可喷阀但文献实验中未发生热失控。")
    if "LFL_mix与模型边界" in qa_categories or "LFL" in warning_text or "防爆" in warning_text:
        suggestions.append("复习 LFL_mix 的教学估算边界，不要把它写成工程防爆设计或消防处置依据。")
    if not metrics.get("gc_finished"):
        suggestions.append("完成 GC 分析后再进入气体组分解释和 LFL_mix 教学估算。")
    if not metrics.get("report_generated"):
        suggestions.append("生成报告前检查数据来源、模型局限、采样记录和安全边界声明。")
    if not suggestions:
        suggestions.append("流程记录较完整，可以尝试比较 25%、50%、75%、100%SOC 下的产气和风险差异。")
    return suggestions


def evaluate_learning(trace: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = ensure_trace(trace)
    metrics = build_learning_metrics(data)
    record_count = metrics["total_operations"] + metrics["qa_count"] + metrics["warning_count"]

    if record_count == 0:
        completion = "待开始"
        safety = "需重点关注"
        understanding = "待巩固"
        report = "待补充"
        summary = "当前记录不足，暂时只能生成起步建议。完成几个实验操作或提问后，学伴会基于客观记录更新评价。"
    else:
        completion = _level_by_ratio(metrics["flow_done"], metrics["flow_total"], ("待开始", "进行中", "基本完成", "完成较好"))
        safety = "需重点关注" if metrics["safety_warning_count"] else ("表现较好" if metrics["safety_qa_count"] else "已有意识")
        understanding = _level_by_ratio(
            metrics["experiment_qa_count"] + metrics["sampling_done"],
            metrics["sampling_total"] + 3,
            ("待巩固", "待巩固", "基本理解", "理解较好"),
        )
        report = "较完整" if metrics["report_generated"] and metrics["gc_finished"] and metrics["lfl_mix_finished"] else ("基本完整" if metrics["report_generated"] else "待补充")
        summary = (
            f"你已经留下 {metrics['total_operations']} 条操作记录、{metrics['qa_count']} 条问答记录和"
            f"{metrics['warning_count']} 条报警/提醒记录。"
        )
        if metrics["invalid_operations"] > 0:
            summary += " 你已经暴露出几个关键可改进点，这是掌握实验安全流程的重要一步。"
        else:
            summary += " 当前记录显示你在按教学流程稳步推进。"

    suggestions = _suggestions(metrics)
    markdown = generate_learning_evaluation_markdown(
        metrics=metrics,
        levels={
            "完成度": completion,
            "安全意识": safety,
            "科学理解": understanding,
            "报告能力": report,
        },
        summary=summary,
        suggestions=suggestions,
    )
    return {
        "metrics": metrics,
        "levels": {
            "completion": completion,
            "safety_awareness": safety,
            "scientific_understanding": understanding,
            "report_ability": report,
        },
        "suggestions": suggestions,
        "markdown": markdown,
        "basis": "本评价仅基于当前 session 内的操作记录、问答记录、报警记录和学习状态快照。",
    }


def generate_learning_evaluation_markdown(
    *,
    metrics: Mapping[str, Any],
    levels: Mapping[str, str],
    summary: str,
    suggestions: list[str],
) -> str:
    state = metrics.get("learning_state", {})
    completed_items = []
    if state.get("sample_prepared"):
        completed_items.append("样品准备")
    if state.get("nitrogen_replacement_done"):
        completed_items.append("真空/充氮置换")
    if state.get("gc_finished"):
        completed_items.append("GC 分析")
    if state.get("lfl_mix_finished"):
        completed_items.append("LFL_mix 教学估算")
    if state.get("report_generated"):
        completed_items.append("报告生成")
    completed_text = "、".join(completed_items) if completed_items else "暂无完整流程节点"

    suggestion_text = "\n".join(f"- {item}" for item in suggestions)
    return f"""## 电池实验 AI 学伴学习评价清单

### 1. 总体鼓励评价

{summary}

已完成的客观事项：{completed_text}。

### 2. 客观指标

| 指标 | 数值 |
| --- | --- |
| 总操作数 | {metrics['total_operations']} |
| 有效操作数 | {metrics['valid_operations']} |
| 报警/提醒次数 | {metrics['warning_count']} |
| 已修正报警数 | {metrics['corrected_warning_count']} |
| 四次采样完成度 | {metrics['sampling_done']} / {metrics['sampling_total']} |
| 问答总数 | {metrics['qa_count']} |
| 实验相关问答 | {metrics['experiment_qa_count']} |
| 安全/边界相关问答 | {metrics['safety_qa_count']} |
| GC 是否完成 | {'是' if metrics['gc_finished'] else '否'} |
| LFL_mix 是否完成 | {'是' if metrics['lfl_mix_finished'] else '否'} |
| 报告是否生成 | {'是' if metrics['report_generated'] else '否'} |

### 3. 等级标签

| 维度 | 标签 |
| --- | --- |
| 完成度 | {levels['完成度']} |
| 安全意识 | {levels['安全意识']} |
| 科学理解 | {levels['科学理解']} |
| 报告能力 | {levels['报告能力']} |

### 4. 实验流程掌握度

流程评价只依据是否完成准备、置换、加热观察、四次采样、GC、LFL_mix 和报告节点。当前完成 {metrics['flow_done']} / {metrics['flow_total']} 个关键节点。

### 5. 安全意识评价

重点关注未完成氮气置换前加热、跳过采样节点、混淆喷阀与热失控、误把 LFL_mix 或教学风险等级当作真实工程判据等问题。当前安全相关报警/提醒数为 {metrics['safety_warning_count']}。

### 6. 科学理解评价

建议围绕 T2=100℃、安全阀喷阀、温度峰值、压力稳定四个节点，以及 SOC 升高导致热失控更剧烈、H₂/CO₂/CO/碳氢化合物变化继续复习。

### 7. 数据与报告能力

报告需要区分参考文献数据、教学演示数据和用户输入数据，并保留模型局限。当前 GC：{'已完成' if metrics['gc_finished'] else '未完成'}；LFL_mix：{'已完成' if metrics['lfl_mix_finished'] else '未完成'}；报告：{'已生成' if metrics['report_generated'] else '未生成'}。

### 8. 问答参与度

当前共有 {metrics['qa_count']} 条问答，其中实验相关 {metrics['experiment_qa_count']} 条，安全/边界相关 {metrics['safety_qa_count']} 条。本项不评价态度，只记录参与和问题类别。

### 9. 个性化建议

{suggestion_text}

### 10. 安全提醒

{SAFETY_FOOTER}
"""
