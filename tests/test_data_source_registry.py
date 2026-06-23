from pathlib import Path

import pandas as pd

from app.utils.data_loader import EXPERIMENT_TEMPLATE_COLUMNS


TEMPLATE_FILES = [
    "literature_metadata_template.csv",
    "battery_sample_template.csv",
    "arc_key_points_template.csv",
    "arc_curve_template.csv",
    "pressure_curve_template.csv",
    "gc_composition_template.csv",
    "gc_peaks_template.csv",
    "gas_volume_formula_template.csv",
    "lel_constants_reference_template.csv",
]


def test_data_source_registry_source_type_allowed():
    path = Path("data/experiment/data_source_registry.csv")
    df = pd.read_csv(path)
    allowed = {"literature", "teaching_interpolation", "teaching_simulation", "pending_user_input", "reference", "calculated_label"}
    assert set(df["source_type"]).issubset(allowed)
    assert {"data_id", "data_file", "data_type", "source_type", "source_description", "is_literature", "notes"}.issubset(df.columns)
    assert not df[(df["source_type"] == "teaching_simulation") & (df["is_literature"].astype(str).str.lower() == "true")].any(axis=None)


def test_experiment_csv_source_type_allowed_when_present():
    allowed = {"literature", "teaching_interpolation", "teaching_simulation", "pending_user_input", "reference", "calculated_label"}
    for path in Path("data/experiment").glob("*.csv"):
        df = pd.read_csv(path)
        if "source_type" in df.columns:
            assert set(df["source_type"].dropna()).issubset(allowed), path


def test_new_literature_template_files_exist_and_have_required_columns():
    for file_name in TEMPLATE_FILES:
        path = Path("data/experiment") / file_name
        assert path.exists(), file_name
        df = pd.read_csv(path)
        for col in EXPERIMENT_TEMPLATE_COLUMNS[file_name]:
            assert col in df.columns, f"{file_name} missing {col}"


def test_registry_covers_core_and_template_files():
    registry = pd.read_csv("data/experiment/data_source_registry.csv")
    covered = set(registry["data_file"])
    expected = {
        "data/normalized_gas_data.csv",
        "data/gas_lfl_constants.csv",
        "data/virtual_scenarios.csv",
        "data/experiment/arc_curve_demo.csv",
        "data/experiment/pressure_curve_demo.csv",
        "data/experiment/gc_peaks_demo.csv",
        "data/experiment/gas_volume_params.csv",
        *{f"data/experiment/{name}" for name in TEMPLATE_FILES},
    }
    assert expected.issubset(covered)
