import json

from app.utils.learning_trace import (
    export_learning_trace_json,
    new_trace,
    record_operation,
    record_qa,
    record_warning,
    update_learning_state_from_experiment,
)


def test_learning_trace_records_operation_and_updates_state():
    trace = new_trace()
    record_operation(
        page_name="二维交互实验台",
        action_type="experiment",
        action_name="select_soc",
        experiment_state={"selected_soc": 50, "current_state": "soc_selection"},
        trace=trace,
    )
    record_operation(
        page_name="二维交互实验台",
        action_type="experiment",
        action_name="finish_gc",
        experiment_state={"selected_soc": 50, "current_state": "gc_analysis", "gc_finished": True},
        trace=trace,
    )

    assert len(trace["operation_events"]) == 2
    assert trace["learning_state"]["current_soc"] == "50"
    assert trace["learning_state"]["gc_finished"] is True


def test_learning_trace_records_qa_and_warning_and_exports_json():
    trace = new_trace()
    record_qa(question="LFL_mix 是不是工程防爆设计依据？", answer="不是工程防爆设计依据。", trace=trace)
    record_warning(
        warning={
            "category": "采样节点错误",
            "reason": "安全阀喷阀尚未记录。",
            "impact": "样本无效。",
            "correct_action": "确认喷阀后再采样。",
            "basis": "四次采样节点。",
        },
        trace=trace,
    )

    data = json.loads(export_learning_trace_json(trace))
    assert data["qa_events"][0]["question_category"] == "LFL_mix与模型边界"
    assert data["qa_events"][0]["is_safety_boundary_related"] is True
    assert data["warning_events"][0]["warning_category"] == "采样节点错误"


def test_learning_trace_empty_and_snapshot_do_not_crash():
    trace = new_trace()
    update_learning_state_from_experiment(
        trace,
        {
            "selected_soc": 100,
            "battery_loaded": True,
            "replacement_count": 3,
            "sampling_completed": {"t2_100": True},
        },
    )

    assert trace["learning_state"]["sample_prepared"] is True
    assert trace["learning_state"]["nitrogen_replacement_done"] is True
    assert trace["learning_state"]["sample_t2_100_done"] is True
