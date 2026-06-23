import pandas as pd
import plotly.graph_objects as go

from app.utils.chart_utils import (
    plot_risk_gauge,
    plot_zeng_key_point_comparison,
    plot_zeng_sampling_timeline,
    plot_zeng_stage_gas_trends,
)


def _valid_zeng_key_points() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "soc_pct": 25,
                "vent_time_s": 757,
                "thermal_runaway_time_s": 1007,
                "max_temperature_c": 229.6,
                "max_heating_rate_c_per_s": 1.8,
                "vent_temperature_c": 145,
                "thermal_runaway_observed": True,
            },
            {
                "soc_pct": 50,
                "vent_time_s": 780,
                "thermal_runaway_time_s": 959,
                "max_temperature_c": 250.0,
                "max_heating_rate_c_per_s": 12.0,
                "vent_temperature_c": 139,
                "thermal_runaway_observed": True,
            },
            {
                "soc_pct": 75,
                "vent_time_s": 883,
                "thermal_runaway_time_s": 930,
                "max_temperature_c": 282.6,
                "max_heating_rate_c_per_s": 17.6,
                "vent_temperature_c": 147,
                "thermal_runaway_observed": True,
            },
            {
                "soc_pct": 100,
                "vent_time_s": 705,
                "thermal_runaway_time_s": 726,
                "max_temperature_c": 349.4,
                "max_heating_rate_c_per_s": 24.9,
                "vent_temperature_c": 145,
                "thermal_runaway_observed": True,
            },
        ]
    )


def assert_figure(fig):
    assert isinstance(fig, go.Figure)


def test_plot_risk_gauge_handles_numeric_none_bad_and_themes():
    for theme in ["light", "dark"]:
        assert_figure(plot_risk_gauge(0.5, theme_mode=theme))
        assert_figure(plot_risk_gauge(None, theme_mode=theme))
        assert_figure(plot_risk_gauge("bad", theme_mode=theme))
        assert_figure(plot_risk_gauge(-1, theme_mode=theme))
        assert_figure(plot_risk_gauge(12.5, theme_mode=theme))


def test_plot_zeng_key_point_comparison_handles_empty_and_valid_data():
    assert_figure(plot_zeng_key_point_comparison(pd.DataFrame()))
    assert_figure(plot_zeng_key_point_comparison(_valid_zeng_key_points()))
    assert_figure(
        plot_zeng_key_point_comparison(
            _valid_zeng_key_points(),
            "max_temperature_c",
            "不同 SOC 最高温度对比",
            "最高温度 (℃)",
            "dark",
        )
    )


def test_plot_zeng_helpers_handle_missing_columns_without_crashing():
    assert_figure(plot_zeng_key_point_comparison(pd.DataFrame({"soc_pct": [25]})))
    assert_figure(plot_zeng_sampling_timeline(pd.DataFrame({"soc_pct": [25]})))
    assert_figure(plot_zeng_stage_gas_trends(pd.DataFrame({"sampling_stage": ["喷阀"]})))
