from app.utils.ai_process_advisor import build_process_advice


def test_process_advisor_unstarted_suggests_soc_and_sample_preparation():
    advice = build_process_advice(page_name="二维交互实验台", experiment_state={"current_state": "sample_preparation"})

    assert "选择 SOC" in advice["next_step_suggestion"]
    assert advice["suggestion_level"] == "idle"


def test_process_advisor_blocks_heating_before_nitrogen_replacement():
    advice = build_process_advice(
        page_name="二维交互实验台",
        experiment_state={"selected_soc": 100, "battery_loaded": True, "leak_test_passed": True, "current_state": "leak_test"},
    )

    assert "未完成真空-充氮置换" in advice["next_step_suggestion"]
    assert "不建议进入加热" in advice["next_step_suggestion"]


def test_process_advisor_t2_reached_suggests_first_sampling():
    advice = build_process_advice(
        page_name="二维交互实验台",
        experiment_state={
            "selected_soc": 100,
            "battery_loaded": True,
            "leak_test_passed": True,
            "replacement_count": 3,
            "heating_started": True,
            "t2_reached_100": True,
        },
    )

    assert "第一次采气" in advice["next_step_suggestion"]


def test_process_advisor_venting_suggests_second_sampling():
    advice = build_process_advice(
        page_name="二维交互实验台",
        experiment_state={
            "selected_soc": 100,
            "battery_loaded": True,
            "leak_test_passed": True,
            "replacement_count": 3,
            "heating_started": True,
            "t2_reached_100": True,
            "venting_detected": True,
            "sampling_completed": {"t2_100": True},
        },
    )

    assert "第二次采样" in advice["next_step_suggestion"]


def test_process_advisor_temperature_peak_suggests_third_sampling():
    advice = build_process_advice(
        page_name="二维交互实验台",
        experiment_state={
            "selected_soc": 100,
            "battery_loaded": True,
            "leak_test_passed": True,
            "replacement_count": 3,
            "heating_started": True,
            "t2_reached_100": True,
            "venting_detected": True,
            "temperature_peak_reached": True,
            "sampling_completed": {"t2_100": True, "venting": True},
        },
    )

    assert "第三次采样" in advice["next_step_suggestion"]


def test_process_advisor_pressure_stable_suggests_fourth_sampling():
    advice = build_process_advice(
        page_name="二维交互实验台",
        experiment_state={
            "selected_soc": 100,
            "battery_loaded": True,
            "leak_test_passed": True,
            "replacement_count": 3,
            "heating_started": True,
            "t2_reached_100": True,
            "venting_detected": True,
            "temperature_peak_reached": True,
            "pressure_stable": True,
            "sampling_completed": {"t2_100": True, "venting": True, "temperature_peak": True},
        },
    )

    assert "第四次采样" in advice["next_step_suggestion"]


def test_process_advisor_report_page_suggests_data_check():
    advice = build_process_advice(page_name="实验报告生成", experiment_state={"current_state": "report_generated"})

    assert "GC 数据" in advice["next_step_suggestion"]
    assert "LFL_mix" in advice["next_step_suggestion"]
    assert "采样记录" in advice["next_step_suggestion"]
