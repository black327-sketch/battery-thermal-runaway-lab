from app.utils.ui_components import _instrument_assessment_values


def test_instrument_panel_uses_assessment_summary_as_score_source() -> None:
    view = _instrument_assessment_values(
        {"score": 97, "safety_status": "规范"},
        {
            "score": 88,
            "grade": "良好",
            "safety_status": "需复核",
            "deductions": [{"points": 10, "reason": "未完成氮气置换即启动 ARC"}],
        },
    )

    assert view["score"] == 88
    assert view["grade"] == "良好"
    assert view["safety_status"] == "需复核"
    assert view["latest_reason"] == "未完成氮气置换即启动 ARC"


def test_instrument_panel_returns_recent_deduction_reasons() -> None:
    view = _instrument_assessment_values(
        {},
        {
            "score": 82,
            "deductions": [
                {"reason": "第三次采气过早。"},
                {"reason": "未完成氮气置换。"},
                {"reason": "未检查压力传感器。"},
                {"reason": "未选择 SOC。"},
            ],
        },
    )

    assert "第三次采气过早。" in view["latest_reason"]
    assert "未完成氮气置换。" in view["latest_reason"]
    assert "未检查压力传感器。" in view["latest_reason"]
    assert "未选择 SOC。" not in view["latest_reason"]
