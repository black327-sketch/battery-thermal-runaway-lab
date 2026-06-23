from app.utils.learning_evaluation import evaluate_learning
from app.utils.learning_trace import new_trace, record_operation, record_qa, record_warning


def test_empty_learning_evaluation_reports_insufficient_records():
    result = evaluate_learning(new_trace())

    assert "记录不足" in result["markdown"]
    assert result["levels"]["completion"] == "待开始"
    assert "虚拟仿真教学" in result["markdown"]


def test_complete_flow_gets_positive_objective_evaluation():
    trace = new_trace()
    state = {
        "selected_soc": 100,
        "battery_loaded": True,
        "leak_test_passed": True,
        "replacement_count": 3,
        "sampling_completed": {
            "t2_100": True,
            "venting": True,
            "temperature_peak": True,
            "pressure_stable": True,
        },
        "gc_finished": True,
        "lel_calculated": True,
        "current_state": "report_generated",
    }
    for action in ["load_battery", "start_leak_test", "complete_replacement_cycle", "finish_gc", "calculate_lel", "generate_report"]:
        record_operation(page_name="二维交互实验台", action_type="experiment", action_name=action, experiment_state=state, trace=trace)
    record_qa(question="高 SOC 为什么更危险？", answer="高 SOC 下可燃气体浓度更高。", trace=trace)

    result = evaluate_learning(trace)

    assert result["metrics"]["gc_finished"] is True
    assert result["metrics"]["lfl_mix_finished"] is True
    assert result["metrics"]["report_generated"] is True
    assert "完成较好" in result["markdown"] or "基本完成" in result["markdown"]


def test_safety_and_sampling_errors_generate_specific_suggestions():
    trace = new_trace()
    record_operation(
        page_name="二维交互实验台",
        action_type="experiment",
        action_name="sample_venting",
        experiment_state={"selected_soc": 0, "current_state": "t2_100"},
        ok=False,
        error_category="采样节点错误",
        trace=trace,
    )
    record_warning(
        warning={
            "category": "采样节点错误",
            "reason": "0%SOC 可喷阀但喷阀不等于热失控。",
            "impact": "样本不能代表温度峰值阶段。",
            "correct_action": "确认喷阀后再采样。",
            "basis": "四次采样节点。",
        },
        trace=trace,
    )
    record_qa(question="LFL_mix 是不是工程防爆设计依据？", answer="LFL_mix 只是教学估算。", trace=trace)

    result = evaluate_learning(trace)

    assert "四次采气节点" in result["markdown"]
    assert "喷阀不等于热失控" in result["markdown"]
    assert "教学估算边界" in result["markdown"]
    assert "消防处置" in result["markdown"]
