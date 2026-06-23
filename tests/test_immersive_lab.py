from app.utils.immersive_lab import latest_safety_alert, recent_deductions, score_tone


def test_score_tone_maps_danger_when_safety_requires_redo() -> None:
    tone, label = score_tone({"score": 82, "valid_data": False, "safety_status": "需重做"})

    assert tone == "danger"
    assert label == "需重做"


def test_score_tone_maps_warning_for_visible_violation() -> None:
    tone, label = score_tone({"score": 68, "valid_data": False, "safety_status": "需复核"})

    assert tone == "warning"
    assert "违规" in label


def test_recent_deductions_limits_to_three_items() -> None:
    summary = {"deductions": [{"points": i, "reason": str(i)} for i in range(5)]}

    assert len(recent_deductions(summary)) == 3


def test_latest_safety_alert_prefers_last_alert() -> None:
    summary = {
        "last_alert": {
            "message": "未完成氮气置换。",
            "consequence": "风险层变红。",
            "severity": "critical",
        },
        "events": [],
    }

    alert = latest_safety_alert(summary)

    assert alert is not None
    assert alert["reason"] == "未完成氮气置换。"
    assert alert["severity"] == "critical"
