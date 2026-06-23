from app.utils.scoring import calculate_final_score, score_action


def test_score_action_rules():
    assert score_action("anything", True) == 0
    assert score_action("normal_error", False) == -3
    assert score_action("start_arc", False, "replacement") == -10
    assert score_action("open_sampling_valve", False, "cooling") == -10
    assert score_action("critical", False, "critical") == -8
    assert score_action("open_vacuum_valve", False, "leak_test") == -10


def test_calculate_final_score_summary():
    state = {
        "current_state": "lel_risk_evaluation",
        "score": 82,
        "error_count": 2,
        "operation_logs": [
            {"level": "error", "severity": "critical", "message": "x"},
            {"level": "info", "severity": "normal", "message": "y"},
        ],
    }
    result = calculate_final_score(state)
    assert result["final_score"] == 82
    assert result["error_count"] == 2
    assert result["critical_errors"]
    assert result["completion_pct"] > 80


def test_final_score_clamped_to_zero():
    result = calculate_final_score(
        {
            "current_state": "sample_preparation",
            "score": -20,
            "error_count": 4,
            "operation_logs": [],
        }
    )
    assert result["final_score"] == 0
