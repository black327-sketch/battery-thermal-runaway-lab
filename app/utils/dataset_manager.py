"""实验数据集选择与加载工具。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
EXP_DIR = DATA_DIR / "experiment"
VALIDATED_DIR = EXP_DIR / "validated"

DATASET_LABELS = {
    "teaching_demo": "教学演示数据",
    "validated_literature": "已校验文献数据",
}

TEACHING_FILES = {
    "arc_curve": EXP_DIR / "arc_curve_demo.csv",
    "pressure_curve": EXP_DIR / "pressure_curve_demo.csv",
    "gc_peaks": EXP_DIR / "gc_peaks_demo.csv",
    "gc_composition": DATA_DIR / "normalized_gas_data.csv",
    "gas_volume_formula": EXP_DIR / "gas_volume_params.csv",
}

VALIDATED_FILES = {
    "literature_metadata": VALIDATED_DIR / "literature_metadata_validated.csv",
    "battery_sample": VALIDATED_DIR / "battery_sample_validated.csv",
    "arc_curve": VALIDATED_DIR / "arc_curve_validated.csv",
    "arc_key_points": VALIDATED_DIR / "arc_key_points_validated.csv",
    "pressure_curve": VALIDATED_DIR / "pressure_curve_validated.csv",
    "gc_composition": VALIDATED_DIR / "gc_composition_validated.csv",
    "gc_peaks": VALIDATED_DIR / "gc_peaks_validated.csv",
    "gas_volume_formula": VALIDATED_DIR / "gas_volume_formula_validated.csv",
    "lel_constants_reference": VALIDATED_DIR / "lel_constants_reference_validated.csv",
}


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _source_type_counts(path: Path) -> dict:
    df = _read_csv_if_exists(path)
    if df.empty or "source_type" not in df.columns:
        return {}
    return df["source_type"].fillna("").astype(str).str.strip().value_counts().to_dict()


def list_available_datasets() -> pd.DataFrame:
    """列出教学演示和已校验文献数据集状态。"""
    validated_exists = VALIDATED_DIR.exists()
    validated_files_present = {key: path.exists() for key, path in VALIDATED_FILES.items()}
    critical = ["literature_metadata", "battery_sample", "arc_curve", "pressure_curve", "gc_composition", "gas_volume_formula", "lel_constants_reference"]
    missing_critical = [key for key in critical if not validated_files_present.get(key)]
    return pd.DataFrame(
        [
            {
                "dataset_name": "teaching_demo",
                "label": DATASET_LABELS["teaching_demo"],
                "available": True,
                "description": "使用当前教学演示、模拟和插值数据，非文献原始数据。",
                "missing_items": "",
            },
            {
                "dataset_name": "validated_literature",
                "label": DATASET_LABELS["validated_literature"],
                "available": validated_exists and not missing_critical,
                "description": "使用 data/experiment/validated 下已校验 CSV；缺失时不回退伪装。",
                "missing_items": "，".join(missing_critical),
            },
        ]
    )


def get_active_dataset_config() -> dict:
    """返回当前 session 的活动数据集配置。"""
    if "active_dataset" not in st.session_state:
        st.session_state["active_dataset"] = "teaching_demo"
    name = st.session_state.get("active_dataset", "teaching_demo")
    if name not in DATASET_LABELS:
        name = "teaching_demo"
        st.session_state["active_dataset"] = name
    is_validated = name == "validated_literature"
    files = VALIDATED_FILES if is_validated else TEACHING_FILES
    missing = [key for key, path in files.items() if not path.exists()]
    source_type_counts = {key: _source_type_counts(path) for key, path in files.items()}
    return {
        "dataset_name": name,
        "label": DATASET_LABELS[name],
        "is_teaching_demo": name == "teaching_demo",
        "is_validated_literature": is_validated,
        "files": {key: str(path) for key, path in files.items()},
        "missing_items": missing,
        "source_type_counts": source_type_counts,
        "message": (
            "当前使用：教学演示数据，非文献原始数据。"
            if name == "teaching_demo"
            else ("当前使用：已校验文献数据，来源见文献数据接入状态。" if not missing else "当前文献数据集不完整，缺失项仍显示为待补充。")
        ),
    }


def set_active_dataset(dataset_name: str) -> None:
    """设置活动数据集。"""
    if dataset_name not in DATASET_LABELS:
        dataset_name = "teaching_demo"
    st.session_state["active_dataset"] = dataset_name


def _active_path(key: str) -> Path:
    name = st.session_state.get("active_dataset", "teaching_demo")
    files = VALIDATED_FILES if name == "validated_literature" else TEACHING_FILES
    return files[key]


def load_active_arc_curve() -> pd.DataFrame:
    return _read_csv_if_exists(_active_path("arc_curve"))


def load_active_pressure_curve() -> pd.DataFrame:
    return _read_csv_if_exists(_active_path("pressure_curve"))


def load_active_gc_composition() -> pd.DataFrame:
    return _read_csv_if_exists(_active_path("gc_composition"))


def load_active_gc_peaks() -> pd.DataFrame:
    return _read_csv_if_exists(_active_path("gc_peaks"))


def load_active_gas_volume_formula() -> pd.DataFrame:
    return _read_csv_if_exists(_active_path("gas_volume_formula"))


def get_validated_status() -> pd.DataFrame:
    """返回 validated 目录下各关键文件状态。"""
    rows = []
    for key, path in VALIDATED_FILES.items():
        df = _read_csv_if_exists(path)
        rows.append(
            {
                "数据项": key,
                "文件": str(path.relative_to(PROJECT_ROOT)),
                "是否存在": path.exists(),
                "行数": len(df),
                "source_type 分布": _source_type_counts(path),
                "状态": "可用" if path.exists() and not df.empty else "待补充",
            }
        )
    return pd.DataFrame(rows)
