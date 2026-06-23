from pathlib import Path

import pandas as pd


EXP_DIR = Path("data/experiment")


def test_zeng_2026_metadata_and_doi_present():
    df = pd.read_csv(EXP_DIR / "literature_zeng_2026_metadata.csv")
    row = df.iloc[0]
    assert row["literature_id"] == "zeng_2026_lfp_prismatic"
    assert row["doi"] == "10.19799/j.cnki.2095-4239.2026.0036"
    assert "方壳磷酸铁锂" in row["title"]
    assert row["data_status"] == "partially_extracted"


def test_zeng_2026_battery_sample_fields_complete():
    df = pd.read_csv(EXP_DIR / "literature_zeng_2026_battery_sample.csv")
    assert set(df["soc_pct"]) == {0, 25, 50, 75, 100}
    required = {
        "nominal_capacity_ah",
        "nominal_voltage_v",
        "mass_g",
        "dimensions_mm",
        "charge_current_a",
        "standard_charge_voltage_v",
        "discharge_current_a",
        "discharge_cutoff_voltage_v",
        "source_location",
        "source_type",
    }
    assert required.issubset(df.columns)
    assert (df["source_type"] == "literature").all()
    assert (df["source_location"] == "Table 1").all()
    assert (df["nominal_capacity_ah"] == 22).all()
    assert (df["nominal_voltage_v"] == 3.22).all()
    assert (df["dimensions_mm"] == "128.7×148.7×17.7").all()


def test_zeng_2026_key_points_complete_and_zero_soc_not_runaway():
    df = pd.read_csv(EXP_DIR / "literature_zeng_2026_arc_key_points.csv")
    assert set(df["soc_pct"]) == {0, 25, 50, 75, 100}
    assert (df["source_type"] == "literature").all()
    assert df["source_location"].astype(str).str.len().gt(0).all()

    zero = df[df["soc_pct"] == 0].iloc[0]
    assert zero["vent_time_s"] == 570
    assert zero["vent_temperature_c"] == 125
    assert zero["voltage_drop_start_s"] == 866
    assert zero["voltage_drop_end_s"] == 1021
    assert zero["thermal_runaway_observed"] == False
    assert pd.isna(zero["thermal_runaway_time_s"])

    expected = {
        25: (1007, 1.8, 229.6),
        50: (959, 12.0, 250.0),
        75: (930, 17.6, 282.6),
        100: (726, 24.9, 349.4),
    }
    for soc, (tr_time, max_rate, max_temp) in expected.items():
        row = df[df["soc_pct"] == soc].iloc[0]
        assert row["thermal_runaway_time_s"] == tr_time
        assert row["max_heating_rate_c_per_s"] == max_rate
        assert row["max_temperature_c"] == max_temp
        assert row["thermal_runaway_observed"] == True


def test_zeng_2026_gc_table3_placeholder_matrix_is_complete_but_pending():
    df = pd.read_csv(EXP_DIR / "literature_zeng_2026_gc_composition.csv")
    assert set(df["soc_pct"]) == {25, 50, 75, 100}
    assert set(df["sampling_stage"]) == {"T2=100℃", "喷阀", "热失控", "反应结束"}
    assert set(df["gas_component"]) == {"H2", "CO2", "CO", "hydrocarbons"}
    assert len(df) == 4 * 4 * 4
    assert df.groupby(["soc_pct", "sampling_stage"]).size().eq(4).all()
    assert df["volume_fraction_pct"].isna().all()
    assert (df["source_type"] == "pending_user_input").all()
    assert df["notes"].str.contains("具体数值未在用户请求中提供").all()


def test_zeng_2026_registry_entries_distinguish_literature_and_pending():
    registry = pd.read_csv(EXP_DIR / "data_source_registry.csv")
    rows = registry[registry["data_id"].str.startswith("literature_zeng_2026")]
    assert set(rows["data_id"]) == {
        "literature_zeng_2026_metadata",
        "literature_zeng_2026_battery_sample",
        "literature_zeng_2026_arc_key_points",
        "literature_zeng_2026_gc_composition",
    }
    literature_rows = rows[rows["source_type"] == "literature"]
    assert set(literature_rows["data_id"]) == {
        "literature_zeng_2026_metadata",
        "literature_zeng_2026_battery_sample",
        "literature_zeng_2026_arc_key_points",
    }
    gc_row = rows[rows["data_id"] == "literature_zeng_2026_gc_composition"].iloc[0]
    assert gc_row["source_type"] == "pending_user_input"
    assert str(gc_row["is_literature"]).lower() == "false"
