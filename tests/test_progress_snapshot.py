from app.utils.progress_snapshot import apply_progress_snapshot_to_session, is_valid_progress_snapshot


def test_progress_snapshot_rejects_wrong_version():
    assert not is_valid_progress_snapshot({"version": 999, "soc": 100})


def test_apply_progress_snapshot_restores_minimal_state(monkeypatch):
    state = {}

    class FakeStreamlit:
        session_state = state

    monkeypatch.setattr("app.utils.progress_snapshot.st", FakeStreamlit)
    ok = apply_progress_snapshot_to_session(
        {
            "version": 1,
            "soc": 100,
            "stage": "lel_risk_evaluation",
            "completed_steps": ["battery_loaded", "arc_door_closed", "leak_test_passed"],
            "sampling": {"t2_100": True},
            "gc_done": True,
            "lfl_done": True,
            "report_done": False,
        }
    )

    assert ok is True
    experiment = state["experiment"]
    assert experiment["selected_soc"] == 100
    assert experiment["battery_loaded"] is True
    assert experiment["gc_finished"] is True
    assert experiment["lel_calculated"] is True
    assert "api_key" not in str(state).lower()
