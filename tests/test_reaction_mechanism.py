from app.utils.reaction_mechanism import (
    collect_completed_mechanisms,
    format_mechanism_markdown,
    mechanism_for_action,
    mechanism_for_state,
)


def test_mechanism_loads_stage_equations_from_docs_json():
    stage = mechanism_for_action("trigger_thermal_runaway")

    assert "热失控" in stage["title"]
    assert stage["equations"]
    assert "H₂" in stage["main_gases"]


def test_failed_action_uses_natural_no_update_message():
    stage = mechanism_for_action("open_sampling_valve", ok=False)

    assert "未更新反应机理" in stage["display_message"]
    assert "待补充" not in format_mechanism_markdown(stage)


def test_collect_completed_mechanisms_includes_sampling_and_lfl():
    stages = collect_completed_mechanisms(
        {
            "selected_soc": 100,
            "battery_loaded": True,
            "arc_door_closed": True,
            "leak_test_passed": True,
            "replacement_count": 3,
            "current_state": "lel_risk_evaluation",
            "sampling_started": True,
            "gas_bag_filled": True,
            "gc_finished": True,
            "lel_calculated": True,
        }
    )
    titles = [stage["title"] for stage in stages]

    assert any("气体采样完成" in title for title in titles)
    assert any("混合气体可燃下限" in title for title in titles)


def test_state_mapping_has_non_reaction_fallback_without_pending_word():
    stage = mechanism_for_state({"current_state": "sample_preparation"})
    text = format_mechanism_markdown(stage)

    assert "未触发新的化学反应方程式" in text
    assert "待补充" not in text
