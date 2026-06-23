import streamlit as st

from app.utils.experiment_state import (
    get_experiment_state,
    perform_action,
    reset_experiment,
)
from app.utils.literature_experiment_state import (
    initial_literature_experiment_state,
    perform_literature_action,
)


def setup_function():
    reset_experiment()


def test_initial_state_correct():
    state = get_experiment_state()
    assert state["current_state"] == "sample_preparation"
    assert state["score"] == 100
    assert state["replacement_count"] == 0


def test_reset_clears_arc_derived_session_results():
    st.session_state["interactive_lel_result"] = {"risk_ratio": 1.2}
    st.session_state["interactive_gas_volume"] = {"total": 1.0}
    st.session_state["interactive_experiment_last"] = {"report": True}
    reset_experiment()
    assert "interactive_lel_result" not in st.session_state
    assert "interactive_gas_volume" not in st.session_state
    assert "interactive_experiment_last" not in st.session_state


def test_cannot_load_battery_without_soc():
    ok, msg = perform_action("load_battery")
    assert not ok
    assert "SOC" in msg
    assert get_experiment_state()["score"] < 100


def test_cannot_vacuum_without_leak_test():
    perform_action("select_soc", {"soc": 100})
    perform_action("load_battery")
    perform_action("close_arc_door")
    ok, msg = perform_action("open_vacuum_valve")
    assert not ok
    assert "气密性" in msg


def test_cannot_start_arc_before_three_replacements():
    perform_action("select_soc", {"soc": 100})
    perform_action("load_battery")
    perform_action("close_arc_door")
    perform_action("start_leak_test")
    ok, msg = perform_action("start_arc")
    assert not ok
    assert "不足三次" in msg


def test_cannot_sample_before_cooling():
    ok, msg = perform_action("connect_gas_bag")
    assert not ok
    assert "冷却" in msg


def test_cannot_gc_before_sampling():
    ok, msg = perform_action("start_gc")
    assert not ok
    assert "采样" in msg


def test_cannot_calculate_gas_volume_before_gc():
    ok, msg = perform_action("calculate_gas_volume")
    assert not ok
    assert "GC" in msg


def test_cannot_calculate_lel_before_gas_volume():
    ok, msg = perform_action("calculate_lel")
    assert not ok
    assert "产气量" in msg


def test_error_operation_deducts_score_and_logs():
    ok, _ = perform_action("start_gc")
    state = get_experiment_state()
    assert not ok
    assert state["score"] == 97
    assert state["error_count"] == 1
    assert state["operation_logs"][0]["level"] == "error"


def _prepare_until_leak_test():
    assert perform_action("select_soc", {"soc": 100})[0]
    assert perform_action("load_battery")[0]
    assert perform_action("close_arc_door")[0]
    assert perform_action("start_leak_test")[0]


def _one_replacement_cycle():
    assert perform_action("open_vacuum_valve")[0]
    assert perform_action("start_vacuum_pump")[0]
    assert perform_action("close_vacuum_valve")[0]
    assert perform_action("open_nitrogen_valve")[0]
    assert perform_action("close_nitrogen_valve")[0]
    assert perform_action("complete_replacement_cycle")[0]


def _prepare_until_arc_ready():
    _prepare_until_leak_test()
    _one_replacement_cycle()
    _one_replacement_cycle()
    _one_replacement_cycle()


def test_complete_correct_flow_reaches_report_generated():
    _prepare_until_arc_ready()
    assert get_experiment_state()["current_state"] == "arc_ready"
    assert perform_action("start_arc")[0]
    assert perform_action("finish_arc_heating")[0]
    assert perform_action("trigger_thermal_runaway")[0]
    assert perform_action("finish_cooling")[0]
    assert perform_action("connect_gas_bag")[0]
    assert perform_action("open_sampling_valve")[0]
    assert perform_action("close_sampling_valve")[0]
    assert perform_action("start_gc")[0]
    assert perform_action("finish_gc")[0]
    assert perform_action("calculate_gas_volume")[0]
    assert perform_action("calculate_lel")[0]
    assert perform_action("generate_report")[0]
    state = get_experiment_state()
    assert state["current_state"] == "report_generated"
    assert state["score"] == 100
    assert state["error_count"] == 0


def test_sampling_valve_open_remains_completed_after_closing():
    _prepare_until_arc_ready()
    assert perform_action("start_arc")[0]
    assert perform_action("finish_arc_heating")[0]
    assert perform_action("trigger_thermal_runaway")[0]
    assert perform_action("finish_cooling")[0]
    assert perform_action("connect_gas_bag")[0]
    assert perform_action("open_sampling_valve")[0]
    state = get_experiment_state()
    assert state["sampling_valve_open"] is True
    assert state["sampling_started"] is True
    assert perform_action("close_sampling_valve")[0]
    state = get_experiment_state()
    assert state["sampling_valve_open"] is False
    assert state["sampling_started"] is True
    assert state["gas_bag_filled"] is True


def test_gc_finish_records_ms_and_computer_result_chain():
    _prepare_until_arc_ready()
    assert perform_action("start_arc")[0]
    assert perform_action("finish_arc_heating")[0]
    assert perform_action("trigger_thermal_runaway")[0]
    assert perform_action("finish_cooling")[0]
    assert perform_action("connect_gas_bag")[0]
    assert perform_action("open_sampling_valve")[0]
    assert perform_action("close_sampling_valve")[0]
    assert perform_action("start_gc")[0]
    assert perform_action("finish_gc")[0]
    state = get_experiment_state()
    assert state["gc_finished"] is True
    assert state["ms_finished"] is True
    assert state["computer_result_ready"] is True


def test_cannot_close_door_before_loading_battery():
    ok, msg = perform_action("close_arc_door")
    assert not ok
    assert "未装入电池" in msg


def test_cannot_start_vacuum_pump_before_valve_open():
    _prepare_until_leak_test()
    ok, msg = perform_action("start_vacuum_pump")
    assert not ok
    assert "真空阀" in msg


def test_cannot_open_nitrogen_before_closing_vacuum_valve():
    _prepare_until_leak_test()
    assert perform_action("open_vacuum_valve")[0]
    assert perform_action("start_vacuum_pump")[0]
    ok, msg = perform_action("open_nitrogen_valve")
    assert not ok
    assert "真空阀未关闭" in msg


def test_closing_nitrogen_valve_exits_active_filling_state():
    _prepare_until_leak_test()
    assert perform_action("open_vacuum_valve")[0]
    assert perform_action("start_vacuum_pump")[0]
    assert perform_action("close_vacuum_valve")[0]
    assert perform_action("open_nitrogen_valve")[0]
    assert get_experiment_state()["current_state"] == "nitrogen_filling"
    assert perform_action("close_nitrogen_valve")[0]
    state = get_experiment_state()
    assert state["nitrogen_valve_open"] is False
    assert state["cycle_nitrogen_done"] is True
    assert state["current_state"] == "atmosphere_replacement"


def test_cannot_complete_replacement_without_full_cycle():
    _prepare_until_leak_test()
    ok, msg = perform_action("complete_replacement_cycle")
    assert not ok
    assert "未完整完成" in msg
    assert get_experiment_state()["replacement_count"] == 0


def test_arc_running_cannot_sample():
    _prepare_until_arc_ready()
    assert perform_action("start_arc")[0]
    ok, msg = perform_action("connect_gas_bag")
    assert not ok
    assert "冷却" in msg


def test_cannot_open_sampling_valve_before_connecting_bag():
    _prepare_until_arc_ready()
    assert perform_action("start_arc")[0]
    assert perform_action("finish_arc_heating")[0]
    assert perform_action("trigger_thermal_runaway")[0]
    assert perform_action("finish_cooling")[0]
    ok, msg = perform_action("open_sampling_valve")
    assert not ok
    assert "集气袋" in msg


def test_repeated_completed_step_is_blocked_and_penalized():
    assert perform_action("select_soc", {"soc": 100})[0]
    assert perform_action("load_battery")[0]
    ok, msg = perform_action("load_battery")
    state = get_experiment_state()
    assert not ok
    assert "已装入" in msg
    assert state["error_count"] == 1
    assert state["score"] == 97


def test_score_never_below_zero_after_many_errors():
    for _ in range(50):
        perform_action("start_arc")
    state = get_experiment_state()
    assert state["score"] == 0
    assert state["error_count"] == 50


def test_literature_zero_soc_venting_does_not_force_thermal_runaway():
    state = initial_literature_experiment_state()
    for action, payload in [
        ("select_soc", {"soc": 0}),
        ("load_prismatic_cell", None),
        ("place_thermocouples", None),
        ("connect_voltage_leads", None),
        ("check_pressure_sensor", None),
        ("close_chamber_door", None),
        ("start_vacuum", None),
        ("fill_nitrogen", None),
        ("start_heating", None),
        ("observe_t2_100", None),
        ("sample_t2_100", None),
        ("observe_venting", None),
        ("sample_venting", None),
    ]:
        state, ok, msg = perform_literature_action(state, action, payload)
        assert ok, msg

    state, ok, msg = perform_literature_action(state, "observe_temperature_peak")

    assert not ok
    assert "0%SOC" in msg
    assert state["thermal_runaway_triggered"] is False
