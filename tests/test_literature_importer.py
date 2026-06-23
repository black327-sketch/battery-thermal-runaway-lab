from io import BytesIO

import pandas as pd

from app.utils.literature_importer import (
    build_import_summary,
    load_uploaded_csv,
    validate_arc_curve,
    validate_battery_sample,
    validate_gc_composition,
    validate_literature_metadata,
    validate_source_type_rules,
)


def test_load_uploaded_csv_empty_returns_empty_dataframe():
    assert load_uploaded_csv(None).empty
    assert load_uploaded_csv(BytesIO(b"")).empty


def test_valid_literature_metadata_passes():
    df = pd.DataFrame(
        [
            {
                "literature_id": "L001",
                "title": "Example title",
                "authors": "A",
                "journal": "J",
                "year": 2024,
                "doi": "10.0000/example",
                "experiment_type": "ARC",
                "battery_type": "cell",
                "cell_format": "pouch",
                "chemistry": "NCM",
                "nominal_capacity": "1 Ah",
                "notes": "",
                "data_status": "verified",
            }
        ]
    )
    result = validate_literature_metadata(df)
    assert result["valid"]


def test_missing_required_fields_fails():
    result = validate_gc_composition(pd.DataFrame({"composition_id": ["c1"]}))
    assert not result["valid"]
    assert result["errors"]


def test_invalid_source_type_fails():
    result = validate_source_type_rules(pd.DataFrame({"source_type": ["bad"]}))
    assert not result["valid"]
    assert "source_type" in result["errors"][0]


def test_teaching_simulation_literature_flag_fails():
    result = validate_source_type_rules(
        pd.DataFrame({"source_type": ["teaching_simulation"], "is_literature": ["true"]})
    )
    assert not result["valid"]
    assert "teaching_simulation" in result["errors"][0]


def test_literature_without_location_fails():
    df = pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "literature_id": "",
                "battery_type": "",
                "cell_format": "",
                "chemistry": "",
                "cathode": "",
                "anode": "",
                "electrolyte": "",
                "nominal_capacity_ah": "",
                "nominal_voltage_v": "",
                "soc_pct": 100,
                "mass_g": "",
                "energy_wh": "",
                "source_location": "",
                "source_type": "literature",
                "notes": "",
            }
        ]
    )
    result = validate_battery_sample(df)
    assert not result["valid"]
    assert any("literature" in error for error in result["errors"])


def test_teaching_interpolation_without_notes_warns():
    df = pd.DataFrame(
        [
            {
                "curve_id": "c1",
                "literature_id": "L001",
                "sample_id": "s1",
                "soc_pct": 100,
                "time_s": 0,
                "temperature_c": 25,
                "heating_rate_c_per_min": 0,
                "phase": "initial",
                "source_type": "teaching_interpolation",
                "source_location": "",
                "notes": "",
            }
        ]
    )
    result = validate_arc_curve(df)
    assert result["valid"]
    assert result["warnings"]


def test_summary_accepts_single_result():
    result = validate_source_type_rules(pd.DataFrame({"source_type": ["pending_user_input"]}))
    summary = build_import_summary(result)
    assert len(summary) == 1
    assert "是否通过" in summary.columns
