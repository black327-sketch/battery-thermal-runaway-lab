from app.utils.assessment_engine import (
    ASSESSMENT_INITIAL_STATE,
    assessment_summary,
    record_assessment_event,
    reset_assessment,
)


def test_record_correct_action_keeps_score() -> None:
    reset_assessment("arc")

    state = record_assessment_event("arc", "load_battery", True, "电池已装入。")
    summary = assessment_summary("arc")

    assert state["score"] == ASSESSMENT_INITIAL_STATE["score"]
    assert summary["valid_data"] is True
    assert "装入电池" in summary["correct_actions"]


def test_wrong_heating_action_records_consequence() -> None:
    reset_assessment("literature")

    state = record_assessment_event("literature", "start_heating", False, "未完成氮气置换。")
    summary = assessment_summary("literature")

    assert state["score"] < 100
    assert summary["valid_data"] is False
    assert summary["safety_status"] == "需重做"
    assert any("GC 与 LFL_mix" in item for item in summary["consequences"])
    assert summary["deductions"][0]["points"] >= 5
    assert summary["deductions"][0]["category"] == "安全边界错误"
    assert "抽真空" in summary["deductions"][0]["reason"]
    assert "置换" in summary["deductions"][0]["correct_action"]
    assert "参考文献" in summary["deductions"][0]["basis"]
    assert summary["last_alert"]["severity"] == "critical"
    assert summary["last_alert"]["impact"]
    assert summary["latest_severe_warning"]["active"] is True
    assert summary["latest_violation"]["message"] == "未完成氮气置换。"


def test_correct_action_clears_latest_severe_warning_but_keeps_history() -> None:
    reset_assessment("literature")

    record_assessment_event("literature", "start_heating", False, "未完成氮气置换。")
    record_assessment_event("literature", "fill_nitrogen", True, "已完成氮气置换。")
    summary = assessment_summary("literature")

    assert summary["last_alert"] is None
    assert summary["latest_violation"] is None
    assert summary["latest_severe_warning"]["active"] is False
    assert "抽真空" in summary["deductions"][0]["reason"]
    assert summary["violation_history"][0]["message"] == "未完成氮气置换。"


def test_early_sampling_marks_invalid_sample() -> None:
    reset_assessment("literature")

    record_assessment_event("literature", "sample_temperature_peak", False, "温度峰值尚未达到。")
    summary = assessment_summary("literature")

    assert "第三次采气" in summary["invalid_samples"]
    assert summary["sample_status"]["sample_temperature_peak"] == "无效样本"
    assert summary["grade"] in {"良好", "合格", "需重做"}
