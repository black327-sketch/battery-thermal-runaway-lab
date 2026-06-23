"""文献数据 CSV 导入与校验工具。"""

from __future__ import annotations

from io import BytesIO, StringIO
from typing import Callable

import pandas as pd

from app.utils.data_loader import ALLOWED_SOURCE_TYPES, EXPERIMENT_TEMPLATE_COLUMNS


VALIDATION_SHAPE = {
    "valid": False,
    "errors": [],
    "warnings": [],
    "row_count": 0,
    "field_count": 0,
    "source_type_counts": {},
}


TYPE_TO_TEMPLATE = {
    "literature_metadata": "literature_metadata_template.csv",
    "battery_sample": "battery_sample_template.csv",
    "arc_key_points": "arc_key_points_template.csv",
    "arc_curve": "arc_curve_template.csv",
    "pressure_curve": "pressure_curve_template.csv",
    "gc_composition": "gc_composition_template.csv",
    "gc_peaks": "gc_peaks_template.csv",
    "gas_volume_formula": "gas_volume_formula_template.csv",
    "lel_constants_reference": "lel_constants_reference_template.csv",
}


def _base_result(df: pd.DataFrame | None) -> dict:
    df = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
    source_counts = {}
    if "source_type" in df.columns:
        source_counts = df["source_type"].fillna("").astype(str).str.strip().value_counts().to_dict()
    return {
        "valid": True,
        "errors": [],
        "warnings": [],
        "row_count": int(len(df)),
        "field_count": int(len(df.columns)),
        "source_type_counts": source_counts,
    }


def _finish(result: dict) -> dict:
    result["valid"] = not result["errors"]
    return result


def load_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """读取 Streamlit 上传 CSV；空文件或 None 返回空 DataFrame。"""
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        if hasattr(uploaded_file, "getvalue"):
            raw = uploaded_file.getvalue()
        else:
            raw = uploaded_file.read()
        if raw is None or raw == b"" or raw == "":
            return pd.DataFrame()
        if isinstance(raw, str):
            return pd.read_csv(StringIO(raw))
        return pd.read_csv(BytesIO(raw))
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _validate_required_columns(df: pd.DataFrame, template_name: str, result: dict) -> None:
    required = EXPERIMENT_TEMPLATE_COLUMNS[template_name]
    missing = [col for col in required if col not in df.columns]
    if missing:
        result["errors"].append(f"缺少必需字段: {', '.join(missing)}")


def validate_source_type_rules(df: pd.DataFrame) -> dict:
    """校验 source_type 取值和基础来源规则。"""
    result = _base_result(df)
    if df.empty:
        result["warnings"].append("上传数据为空。")
        return _finish(result)
    if "source_type" not in df.columns:
        result["errors"].append("缺少 source_type 字段。")
        return _finish(result)

    source_values = df["source_type"].fillna("").astype(str).str.strip()
    invalid = sorted(set(source_values[source_values != ""]) - ALLOWED_SOURCE_TYPES)
    if invalid:
        result["errors"].append(f"source_type 存在非法取值: {invalid}")

    if "is_literature" in df.columns:
        is_lit = df["is_literature"].fillna("").astype(str).str.lower().str.strip()
        bad = df[source_values.eq("teaching_simulation") & is_lit.eq("true")]
        if not bad.empty:
            result["errors"].append("teaching_simulation 不允许 is_literature=True。")

    if (source_values == "pending_user_input").any():
        result["warnings"].append("pending_user_input 记录不能进入正式计算，只能作为待补充项。")

    if "notes" in df.columns:
        interpolation = df[source_values.eq("teaching_interpolation")]
        if not interpolation.empty:
            missing_notes = interpolation["notes"].fillna("").astype(str).str.strip().eq("")
            if missing_notes.any():
                result["warnings"].append("teaching_interpolation 记录应在 notes 中说明插值依据。")
    return _finish(result)


def validate_literature_required_location(df: pd.DataFrame) -> dict:
    """校验 source_type=literature 的文献定位信息。"""
    result = _base_result(df)
    if df.empty:
        result["warnings"].append("上传数据为空。")
        return _finish(result)
    if "source_type" not in df.columns:
        result["errors"].append("缺少 source_type 字段，无法判断文献定位要求。")
        return _finish(result)
    source_values = df["source_type"].fillna("").astype(str).str.strip()
    literature_rows = df[source_values.eq("literature")]
    if literature_rows.empty:
        return _finish(result)

    has_lit_id = (
        "literature_id" in literature_rows.columns
        and ~literature_rows["literature_id"].fillna("").astype(str).str.strip().eq("")
    )
    has_source_location = (
        "source_location" in literature_rows.columns
        and ~literature_rows["source_location"].fillna("").astype(str).str.strip().eq("")
    )
    has_doi = (
        "doi" in literature_rows.columns
        and ~literature_rows["doi"].fillna("").astype(str).str.strip().eq("")
    )
    ok = has_doi if isinstance(has_doi, pd.Series) else pd.Series(False, index=literature_rows.index)
    if isinstance(has_lit_id, pd.Series) and isinstance(has_source_location, pd.Series):
        ok = ok | (has_lit_id & has_source_location)
    if (~ok).any():
        result["errors"].append("source_type=literature 的记录必须填写 literature_id + source_location，或提供 doi。")
    return _finish(result)


def _validate_common(df: pd.DataFrame, template_name: str) -> dict:
    result = _base_result(df)
    if df.empty:
        result["warnings"].append("上传数据为空。")
        return _finish(result)
    _validate_required_columns(df, template_name, result)
    source_result = validate_source_type_rules(df)
    location_result = validate_literature_required_location(df)
    result["errors"].extend(source_result["errors"])
    result["warnings"].extend(source_result["warnings"])
    result["errors"].extend(location_result["errors"])
    result["warnings"].extend(location_result["warnings"])
    return _finish(result)


def _warn_numeric(df: pd.DataFrame, result: dict, columns: list[str]) -> None:
    for col in columns:
        if col in df.columns:
            bad = pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna() & ~df[col].astype(str).str.strip().eq("")
            if bad.any():
                result["warnings"].append(f"{col} 存在非数值内容，请核对单位和录入格式。")


def validate_literature_metadata(df: pd.DataFrame) -> dict:
    result = _base_result(df)
    if df.empty:
        result["warnings"].append("上传数据为空。")
        return _finish(result)
    _validate_required_columns(df, "literature_metadata_template.csv", result)
    if "data_status" in df.columns:
        allowed = {"pending_extraction", "partially_extracted", "verified", "excluded"}
        invalid = sorted(set(df["data_status"].dropna().astype(str).str.strip()) - allowed)
        if invalid:
            result["errors"].append(f"data_status 存在非法取值: {invalid}")
    _warn_numeric(df, result, ["year"])
    return _finish(result)


def validate_battery_sample(df: pd.DataFrame) -> dict:
    result = _validate_common(df, "battery_sample_template.csv")
    _warn_numeric(df, result, ["nominal_capacity_ah", "nominal_voltage_v", "soc_pct", "mass_g", "energy_wh"])
    return _finish(result)


def validate_arc_key_points(df: pd.DataFrame) -> dict:
    result = _validate_common(df, "arc_key_points_template.csv")
    allowed_phase = {"initial", "self_heating_onset", "venting", "thermal_runaway_onset", "max_temperature", "cooling", "end"}
    if "phase" in df.columns:
        invalid = sorted(set(df["phase"].dropna().astype(str).str.strip()) - allowed_phase - {""})
        if invalid:
            result["warnings"].append(f"phase 存在非建议取值: {invalid}")
    _warn_numeric(df, result, ["soc_pct", "time_s", "temperature_c", "heating_rate_c_per_min", "pressure_kpa"])
    return _finish(result)


def validate_arc_curve(df: pd.DataFrame) -> dict:
    result = _validate_common(df, "arc_curve_template.csv")
    _warn_numeric(df, result, ["soc_pct", "time_s", "temperature_c", "heating_rate_c_per_min"])
    if "source_type" in df.columns and "notes" in df.columns:
        literature_with_interpolation_note = df[
            df["source_type"].astype(str).str.strip().eq("literature")
            & df["notes"].fillna("").astype(str).str.contains("插值|interpolation", case=False, regex=True)
        ]
        if not literature_with_interpolation_note.empty:
            result["errors"].append("插值曲线不得标记为 source_type=literature。")
    return _finish(result)


def validate_pressure_curve(df: pd.DataFrame) -> dict:
    result = _validate_common(df, "pressure_curve_template.csv")
    _warn_numeric(df, result, ["soc_pct", "time_s", "pressure_kpa"])
    return _finish(result)


def validate_gc_composition(df: pd.DataFrame) -> dict:
    result = _validate_common(df, "gc_composition_template.csv")
    _warn_numeric(df, result, ["soc_pct", "volume_fraction_pct"])
    if "measurement_basis" in df.columns:
        allowed = {"normalized_volume_fraction", "reported_volume_fraction", ""}
        invalid = sorted(set(df["measurement_basis"].fillna("").astype(str).str.strip()) - allowed)
        if invalid:
            result["warnings"].append(f"measurement_basis 存在非建议取值: {invalid}")
    return _finish(result)


def validate_gc_peaks(df: pd.DataFrame) -> dict:
    result = _validate_common(df, "gc_peaks_template.csv")
    _warn_numeric(df, result, ["soc_pct", "retention_time_min", "signal_intensity"])
    return _finish(result)


def validate_gas_volume_formula(df: pd.DataFrame) -> dict:
    result = _validate_common(df, "gas_volume_formula_template.csv")
    _warn_numeric(df, result, ["soc_pct", "parameter_value"])
    if "source_type" in df.columns and df["source_type"].astype(str).str.strip().eq("pending_user_input").any():
        result["warnings"].append("产气量公式仍有 pending_user_input，页面和报告必须保持待补充状态。")
    return _finish(result)


def validate_lel_constants_reference(df: pd.DataFrame) -> dict:
    result = _validate_common(df, "lel_constants_reference_template.csv")
    _warn_numeric(df, result, ["lfl_vol_pct", "ufl_vol_pct", "year", "temperature_c", "pressure_kpa"])
    return _finish(result)


VALIDATORS: dict[str, Callable[[pd.DataFrame], dict]] = {
    "literature_metadata": validate_literature_metadata,
    "battery_sample": validate_battery_sample,
    "arc_key_points": validate_arc_key_points,
    "arc_curve": validate_arc_curve,
    "pressure_curve": validate_pressure_curve,
    "gc_composition": validate_gc_composition,
    "gc_peaks": validate_gc_peaks,
    "gas_volume_formula": validate_gas_volume_formula,
    "lel_constants_reference": validate_lel_constants_reference,
}


def build_import_summary(validation_results: dict) -> pd.DataFrame:
    """把一个或多个校验结果汇总为表格。"""
    if "valid" in validation_results:
        validation_results = {"uploaded": validation_results}
    rows = []
    for name, result in validation_results.items():
        rows.append(
            {
                "数据类型": name,
                "是否通过": bool(result.get("valid", False)),
                "行数": int(result.get("row_count", 0)),
                "字段数": int(result.get("field_count", 0)),
                "错误数": len(result.get("errors", [])),
                "警告数": len(result.get("warnings", [])),
                "source_type 分布": result.get("source_type_counts", {}),
            }
        )
    return pd.DataFrame(rows)
