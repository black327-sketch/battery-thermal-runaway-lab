from app.utils.literature_device_svg import render_explosion_chamber_heating_platform_svg
from app.utils.literature_experiment_state import (
    get_literature_experiment_state,
    initial_literature_experiment_state,
    perform_literature_action,
    reset_literature_experiment,
)
from app.utils.report_generator import generate_report


REQUIRED_GROUP_IDS = {
    "explosion-chamber",
    "prismatic-lfp-cell",
    "heating-plate",
    "insulation-board",
    "thermocouple-t1",
    "thermocouple-t2",
    "thermocouple-t3",
    "voltage-leads",
    "pressure-sensor",
    "vacuum-line",
    "nitrogen-line",
    "sampling-line",
    "gas-bag",
    "gc-device",
    "daq-computer",
}


def _run_ok(state, action, payload=None):
    new_state, ok, message = perform_literature_action(state, action, payload)
    assert ok, message
    return new_state


def _prepare_until_heating():
    state = initial_literature_experiment_state()
    state = _run_ok(state, "select_soc", {"soc": 100})
    state = _run_ok(state, "load_prismatic_cell")
    state = _run_ok(state, "place_thermocouples")
    state = _run_ok(state, "connect_voltage_leads")
    state = _run_ok(state, "check_pressure_sensor")
    state = _run_ok(state, "close_chamber_door")
    state = _run_ok(state, "start_vacuum")
    state = _run_ok(state, "fill_nitrogen")
    state = _run_ok(state, "start_heating")
    return state


def test_literature_device_svg_contains_required_group_ids():
    state = initial_literature_experiment_state()
    svg = render_explosion_chamber_heating_platform_svg(state)
    for group_id in REQUIRED_GROUP_IDS:
        assert f'id="{group_id}"' in svg
    assert 'viewBox="0 0 1180 760"' in svg


def test_literature_device_svg_keeps_logical_device_connections():
    state = initial_literature_experiment_state()
    svg = render_explosion_chamber_heating_platform_svg(state)

    for connection_id in [
        "connection-lit-vacuum",
        "connection-lit-n2",
        "connection-lit-sample",
        "connection-lit-bag-gc",
        "connection-lit-gc-ms",
        "connection-lit-ms-computer",
        "connection-lit-voltage",
        "connection-lit-pressure",
        "connection-lit-arc-monitor",
    ]:
        assert f'id="{connection_id}"' in svg
    assert "GC 组成 → LFL" not in svg


def test_literature_state_blocks_close_door_before_thermocouples():
    state = initial_literature_experiment_state()
    state = _run_ok(state, "select_soc", {"soc": 50})
    state = _run_ok(state, "load_prismatic_cell")
    new_state, ok, message = perform_literature_action(state, "close_chamber_door")
    assert not ok
    assert "热电偶" in message
    assert new_state["score"] < state["score"]


def test_literature_svg_uses_active_warning_only():
    state = initial_literature_experiment_state()
    state["_assessment_summary"] = {
        "latest_severe_warning": {"active": False, "message": "旧告警"},
        "last_alert": None,
    }

    svg = render_explosion_chamber_heating_platform_svg(state)

    assert "literature-risk-overlay" not in svg
    assert "旧告警" not in svg


def test_literature_state_blocks_vacuum_before_door_closed():
    state = initial_literature_experiment_state()
    new_state, ok, message = perform_literature_action(state, "start_vacuum")
    assert not ok
    assert "舱门" in message
    assert new_state["error_count"] == 1


def test_literature_state_blocks_heating_before_nitrogen_replacement():
    state = initial_literature_experiment_state()
    state = _run_ok(state, "select_soc", {"soc": 75})
    state = _run_ok(state, "load_prismatic_cell")
    state = _run_ok(state, "place_thermocouples")
    state = _run_ok(state, "connect_voltage_leads")
    state = _run_ok(state, "check_pressure_sensor")
    state = _run_ok(state, "close_chamber_door")
    state = _run_ok(state, "start_vacuum")
    new_state, ok, message = perform_literature_action(state, "start_heating")
    assert not ok
    assert "氮气" in message
    assert new_state["heating_started"] is False


def test_literature_sampling_stages_cannot_skip_prerequisites():
    state = _prepare_until_heating()

    blocked, ok, message = perform_literature_action(state, "sample_t2_100")
    assert not ok
    assert "T2" in message

    state = _run_ok(state, "observe_t2_100")
    state = _run_ok(state, "sample_t2_100")

    blocked, ok, message = perform_literature_action(state, "sample_venting")
    assert not ok
    assert "喷阀" in message

    state = _run_ok(state, "observe_venting")
    state = _run_ok(state, "sample_venting")

    blocked, ok, message = perform_literature_action(state, "sample_temperature_peak")
    assert not ok
    assert "温度峰值" in message

    state = _run_ok(state, "observe_temperature_peak")
    state = _run_ok(state, "sample_temperature_peak")

    blocked, ok, message = perform_literature_action(state, "sample_pressure_stable")
    assert not ok
    assert "压力" in message


def test_literature_gc_and_risk_require_sampling_and_gc_completion():
    state = _prepare_until_heating()
    new_state, ok, message = perform_literature_action(state, "start_gc")
    assert not ok
    assert "采气" in message

    state = _run_ok(state, "observe_t2_100")
    state = _run_ok(state, "sample_t2_100")
    state = _run_ok(state, "observe_venting")
    state = _run_ok(state, "sample_venting")
    state = _run_ok(state, "observe_temperature_peak")
    state = _run_ok(state, "sample_temperature_peak")
    state = _run_ok(state, "observe_pressure_stable")
    state = _run_ok(state, "sample_pressure_stable")
    state = _run_ok(state, "start_gc")

    new_state, ok, message = perform_literature_action(state, "evaluate_lel_risk")
    assert not ok
    assert "GC" in message

    state = _run_ok(state, "finish_gc")
    state = _run_ok(state, "evaluate_lel_risk")
    state = _run_ok(state, "generate_report")
    assert state["current_state"] == "report_generated"


def test_literature_report_contains_boundary_statement():
    state = _prepare_until_heating()
    report = generate_report(
        experiment_params={
            "interactive_state": state,
            "experiment_mode": "literature_explosion_chamber_heating",
            "score_summary": {"final_score": 100, "error_count": 0, "completion_pct": 50.0},
        },
        literature_data={"sample_info": {}, "gas_composition": {}, "flammable_composition": {}},
        calculation_results={"risk_info": {"level": "无法评价", "description": "测试"}},
    )
    assert "文献装置模式：防爆舱-加热模块产气教学演示" in report
    assert "10.19799/j.cnki.2095-4239.2026.0036" in report
    assert "二维教学仿真边界说明" in report
    assert "不用于真实事故预测、消防应急或工程防爆设计" in report


def test_literature_reset_clears_mode_specific_derived_results():
    import streamlit as st

    st.session_state["literature_lel_result"] = {"risk": "demo"}
    st.session_state["literature_gas_volume"] = {"volume": 1}
    st.session_state["interactive_experiment_last"] = {"mode": "literature"}
    reset_literature_experiment()
    state = get_literature_experiment_state()
    assert state["current_state"] == "soc_selection"
    assert "literature_lel_result" not in st.session_state
    assert "literature_gas_volume" not in st.session_state
    assert "interactive_experiment_last" not in st.session_state
