import pandas as pd

from app.utils.lfl_calculator import calculate_lfl_mix
from app.utils.risk_model import VENTILATION_FACTOR_MAP, calculate_risk_ratio, estimate_space_concentration


def test_virtual_scenarios_are_exact_four_new_options():
    df = pd.read_csv("data/virtual_scenarios.csv")

    assert df["scenario_id"].tolist() == [
        "S01 小型实验舱 · 10.0立方米 · 通风不良",
        "S02 小型实验舱 · 10.0立方米 · 通风良好",
        "S03 大型实验舱 · 50.0立方米 · 通风不良",
        "S04 大型实验舱 · 50.0立方米 · 通风良好",
    ]


def test_default_scene_risk_order_reflects_volume_and_ventilation():
    df = pd.read_csv("data/virtual_scenarios.csv")
    lfl_mix = calculate_lfl_mix({"H2": 20.0, "CO": 20.0, "CH4": 10.0}, {"H2": 4.0, "CO": 12.5, "CH4": 5.0})
    risks = []
    for _, row in df.iterrows():
        c = estimate_space_concentration(200.0, float(row["room_volume_m3"]), VENTILATION_FACTOR_MAP[row["ventilation"]])
        risks.append(calculate_risk_ratio(c, lfl_mix))

    assert risks == sorted(risks, reverse=True)
    assert all(risk is not None and risk >= 0 for risk in risks)
