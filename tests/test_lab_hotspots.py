from app.utils.lab_hotspots import ARC_HOTSPOTS, hotspot_button_label, hotspot_status


def test_arc_hotspots_cover_required_device_actions() -> None:
    actions = {hotspot.action for hotspot in ARC_HOTSPOTS}

    assert {
        "close_arc_door",
        "start_vacuum_pump",
        "open_vacuum_valve",
        "open_nitrogen_valve",
        "start_arc",
        "open_sampling_valve",
        "start_gc",
        "calculate_lel",
        "generate_report",
    }.issubset(actions)


def test_hotspot_status_and_label_follow_state() -> None:
    door = next(hotspot for hotspot in ARC_HOTSPOTS if hotspot.key == "door")

    assert hotspot_status(door, {"arc_door_closed": False}) == "idle"
    assert "点击" in hotspot_button_label(door, {"arc_door_closed": False})
    assert hotspot_status(door, {"arc_door_closed": True}) == "done"
    assert "已完成" in hotspot_button_label(door, {"arc_door_closed": True})
