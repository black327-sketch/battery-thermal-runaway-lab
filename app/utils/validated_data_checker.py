"""
app/utils/validated_data_checker.py —— 真实文献数据模板校验工具。

对所有 validated/ 目录下的 CSV 模板进行列完整性、source_type 合法性
和文献数据来源规则校验。空模板产生 warnings，不产生崩溃。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATED_DIR = PROJECT_ROOT / "data" / "experiment" / "validated"

ALLOWED_SOURCE_TYPES = {
    "literature",
    "teaching_interpolation",
    "teaching_simulation",
    "pending_user_input",
    "reference",
    "calculated_label",
}

# ── 各模板必填列 ──────────────────────────────────────────
VALIDATED_REQUIRED_COLUMNS: dict[str, list[str]] = {
    "literature_metadata_validated.csv": [
        "literature_id", "title", "source_type",
    ],
    "battery_sample_validated.csv": [
        "sample_id", "literature_id", "soc_pct", "source_type",
    ],
    "thermal_runaway_stage_validated.csv": [
        "stage_id", "stage_order", "stage_name",
    ],
    "reaction_mechanism_validated.csv": [
        "mechanism_id", "stage_id", "mechanism_name",
    ],
    "gas_generation_reaction_validated.csv": [
        "reaction_id", "mechanism_id", "stage_id", "gas_component",
    ],
    "gc_composition_validated.csv": [
        "composition_id", "gas_component", "source_type",
    ],
    "lel_constants_reference_validated.csv": [
        "component", "lfl_vol_pct", "source_type",
    ],
    "mechanism_visual_assets.csv": [
        "asset_id", "asset_title", "scene_description", "visual_style",
    ],
    "mechanism_video_assets.csv": [
        "video_id", "segment_title", "duration_s",
    ],
}

# ── 每个模板的标准列名全集 ────────────────────────────────
VALIDATED_TEMPLATE_COLUMNS: dict[str, list[str]] = {
    "literature_metadata_validated.csv": [
        "literature_id", "title", "authors", "journal", "year", "doi",
        "document_type", "experiment_type", "source_status",
        "source_type", "source_location", "notes",
    ],
    "battery_sample_validated.csv": [
        "sample_id", "literature_id", "battery_type", "cell_format",
        "chemistry", "cathode", "anode", "electrolyte", "capacity_ah",
        "nominal_voltage_v", "soc_pct", "mass_g", "dimensions_mm",
        "source_location", "source_type", "notes",
    ],
    "thermal_runaway_stage_validated.csv": [
        "stage_id", "stage_order", "stage_name", "temperature_range_c",
        "main_event", "observable_phenomenon", "key_risk",
        "teaching_explanation", "source_location", "source_type", "notes",
    ],
    "reaction_mechanism_validated.csv": [
        "mechanism_id", "stage_id", "mechanism_name",
        "temperature_range_c", "material_region", "main_process",
        "gas_products", "heat_effect", "teaching_summary",
        "source_location", "source_type", "notes",
    ],
    "gas_generation_reaction_validated.csv": [
        "reaction_id", "mechanism_id", "stage_id", "gas_component",
        "reaction_equation", "reactants", "products",
        "temperature_range_c", "risk_meaning", "visual_hint",
        "source_location", "source_type", "notes",
    ],
    "gc_composition_validated.csv": [
        "composition_id", "literature_id", "sample_id", "soc_pct",
        "stage_id", "gas_component", "concentration_ppm",
        "volume_fraction_pct", "measurement_basis", "instrument",
        "detector", "source_location", "source_type", "notes",
    ],
    "lel_constants_reference_validated.csv": [
        "component", "lfl_vol_pct", "ufl_vol_pct",
        "standard_or_source", "source_title", "year", "doi_or_url",
        "temperature_c", "pressure_kpa", "applicability",
        "source_type", "notes",
    ],
    "mechanism_visual_assets.csv": [
        "asset_id", "stage_id", "asset_title", "visual_type",
        "target_page", "scene_description", "key_labels",
        "reaction_equations", "visual_style", "status",
        "file_path", "source_type", "notes",
    ],
    "mechanism_video_assets.csv": [
        "video_id", "asset_id", "segment_title", "duration_s",
        "input_image_path", "animation_goal", "narration_text",
        "transition_to_next", "status", "output_video_path", "notes",
    ],
}


def _load_validated_csv(file_name: str) -> pd.DataFrame:
    """加载 validated 目录下的 CSV，文件不存在时返回空模板 DataFrame。"""
    path = VALIDATED_DIR / file_name
    columns = VALIDATED_TEMPLATE_COLUMNS.get(file_name, [])
    if not path.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path)
    # 补全缺失列
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df


# ═══════════════════════════════════════════════════════════════
# 校验函数
# ═══════════════════════════════════════════════════════════════

def validate_required_columns(df: pd.DataFrame, required_columns: list[str]) -> dict[str, Any]:
    """检查 DataFrame 是否包含必要列。

    Returns
    -------
    dict
        {"ok": bool, "missing": list[str], "message": str}
    """
    if df is None:
        return {"ok": False, "missing": required_columns, "message": "DataFrame 为 None。"}
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        return {"ok": False, "missing": missing, "message": f"缺少列: {missing}"}
    return {"ok": True, "missing": [], "message": "所有必要列存在。"}


def validate_source_type(df: pd.DataFrame) -> dict[str, Any]:
    """校验 source_type 取值合法性。

    Returns
    -------
    dict
        {"ok": bool, "invalid_values": list[str], "message": str, "warnings": list[str]}
    """
    warnings: list[str] = []
    if df is None or df.empty or "source_type" not in df.columns:
        return {"ok": True, "invalid_values": [], "message": "无 source_type 列或无数据，跳过校验。", "warnings": warnings}
    source_values = df["source_type"].fillna("").astype(str).str.strip()
    non_empty = source_values[source_values != ""]
    if non_empty.empty:
        warnings.append("所有行的 source_type 为空，待填写。")
        return {"ok": True, "invalid_values": [], "message": "所有 source_type 待填写。", "warnings": warnings}
    invalid = sorted(set(non_empty) - ALLOWED_SOURCE_TYPES)
    if invalid:
        return {"ok": False, "invalid_values": invalid,
                "message": f"source_type 非法取值: {invalid}；允许值: {sorted(ALLOWED_SOURCE_TYPES)}",
                "warnings": warnings}
    return {"ok": True, "invalid_values": [], "message": f"source_type 取值合法。共 {len(non_empty)} 行有值。",
            "warnings": warnings}


def validate_literature_rows(df: pd.DataFrame) -> dict[str, Any]:
    """校验 source_type=literature 的行必须填写 source_location。

    Returns
    -------
    dict
        {"ok": bool, "issues": list[str], "message": str, "warnings": list[str]}
    """
    warnings: list[str] = []
    issues: list[str] = []
    if df is None or df.empty:
        return {"ok": True, "issues": [], "message": "无数据，跳过文献行校验。", "warnings": warnings}
    if "source_type" not in df.columns:
        return {"ok": True, "issues": [], "message": "无 source_type 列，跳过文献行校验。", "warnings": warnings}
    lit_rows = df[df["source_type"].astype(str).str.strip().eq("literature")]
    if lit_rows.empty:
        return {"ok": True, "issues": [], "message": "无 source_type=literature 的行。", "warnings": warnings}
    if "source_location" in df.columns:
        missing_loc = lit_rows["source_location"].fillna("").astype(str).str.strip().eq("")
        if missing_loc.any():
            row_indices = lit_rows.index[missing_loc].tolist()
            issues.append(f"文献行缺少 source_location: 行索引 {row_indices}")
    if "literature_id" in df.columns:
        missing_lid = lit_rows["literature_id"].fillna("").astype(str).str.strip().eq("")
        if missing_lid.any():
            row_indices = lit_rows.index[missing_lid].tolist()
            issues.append(f"文献行缺少 literature_id: 行索引 {row_indices}")
    ok = len(issues) == 0
    return {"ok": ok, "issues": issues,
            "message": "文献行校验通过。" if ok else f"文献行校验发现问题: {'; '.join(issues)}",
            "warnings": warnings}


def validate_visual_assets(df: pd.DataFrame) -> dict[str, Any]:
    """校验 visual_assets 建议必填字段。

    Returns
    -------
    dict
        {"ok": bool, "issues": list[str], "warnings": list[str]}
    """
    warnings: list[str] = []
    issues: list[str] = []
    if df is None or df.empty:
        warnings.append("mechanism_visual_assets.csv 为空，暂无视觉素材。")
        return {"ok": True, "issues": [], "warnings": warnings}
    suggested_required = ["asset_id", "asset_title", "scene_description", "visual_style"]
    missing = [c for c in suggested_required if c not in df.columns]
    if missing:
        issues.append(f"缺少建议必填列: {missing}")
    # 检查非空行是否填写了这些字段
    if "asset_id" in df.columns:
        has_id = df["asset_id"].fillna("").astype(str).str.strip().ne("")
        for col in suggested_required:
            if col in df.columns and col != "asset_id":
                blanks = has_id & df[col].fillna("").astype(str).str.strip().eq("")
                if blanks.any():
                    warnings.append(f"有 {blanks.sum()} 行的 {col} 为空，建议补填。")
    return {"ok": len(issues) == 0, "issues": issues, "warnings": warnings}


def validate_video_assets(df: pd.DataFrame) -> dict[str, Any]:
    """校验 video_assets 建议必填字段。

    Returns
    -------
    dict
        {"ok": bool, "issues": list[str], "warnings": list[str]}
    """
    warnings: list[str] = []
    issues: list[str] = []
    if df is None or df.empty:
        warnings.append("mechanism_video_assets.csv 为空，暂无视频素材。")
        return {"ok": True, "issues": [], "warnings": warnings}
    suggested_required = ["video_id", "segment_title", "duration_s"]
    missing = [c for c in suggested_required if c not in df.columns]
    if missing:
        issues.append(f"缺少建议必填列: {missing}")
    if "video_id" in df.columns:
        has_id = df["video_id"].fillna("").astype(str).str.strip().ne("")
        for col in suggested_required:
            if col in df.columns and col != "video_id":
                blanks = has_id & df[col].fillna("").astype(str).str.strip().eq("")
                if blanks.any():
                    warnings.append(f"有 {blanks.sum()} 行的 {col} 为空，建议补填。")
    return {"ok": len(issues) == 0, "issues": issues, "warnings": warnings}


def validate_all_validated_data() -> dict[str, Any]:
    """对所有 validated 模板文件进行全面校验。

    Returns
    -------
    dict
        {
            "ok": bool,
            "files_checked": int,
            "files_present": int,
            "files_missing": list[str],
            "results": {file_name: {check_name: result_dict}},
        }
    """
    all_files = sorted(VALIDATED_TEMPLATE_COLUMNS.keys())
    missing: list[str] = []
    results: dict[str, dict] = {}

    for fname in all_files:
        path = VALIDATED_DIR / fname
        if not path.exists():
            missing.append(fname)
            results[fname] = {"file_exists": False, "warnings": [f"文件 {fname} 不存在于 validated/ 目录。"]}
            continue

        df = _load_validated_csv(fname)
        file_results: dict[str, Any] = {
            "file_exists": True,
            "row_count": len(df),
            "empty": df.dropna(how="all").empty,
        }

        # 1. 必填列检查
        required = VALIDATED_REQUIRED_COLUMNS.get(fname, [])
        file_results["required_columns"] = validate_required_columns(df, required)

        # 2. source_type 校验
        if "source_type" in df.columns or "source_type" in VALIDATED_TEMPLATE_COLUMNS.get(fname, []):
            file_results["source_type"] = validate_source_type(df)

        # 3. 文献行校验
        file_results["literature_rows"] = validate_literature_rows(df)

        # 4. 专项校验
        if fname == "mechanism_visual_assets.csv":
            file_results["visual_assets"] = validate_visual_assets(df)
        if fname == "mechanism_video_assets.csv":
            file_results["video_assets"] = validate_video_assets(df)

        # 5. 反应方程式类型校验
        if fname == "gas_generation_reaction_validated.csv" and "reaction_equation" in df.columns:
            non_empty = df["reaction_equation"].fillna("").astype(str).str.strip().ne("")
            bad = non_empty & ~df["reaction_equation"].apply(lambda x: isinstance(x, str))
            if bad.any():
                file_results["reaction_equation_type"] = {
                    "ok": False, "message": f"有 {bad.sum()} 行 reaction_equation 不是字符串类型。"
                }
            else:
                file_results["reaction_equation_type"] = {"ok": True, "message": "reaction_equation 类型检查通过。"}

        # 空模板 warning
        file_warnings: list[str] = []
        if df.dropna(how="all").empty and not df.empty:
            file_warnings.append(f"{fname} 仅有表头，暂无数据行。待填写。")
        elif df.empty:
            file_warnings.append(f"{fname} 为空（含列名）。待填写。")
        file_results["warnings"] = file_warnings

        results[fname] = file_results

    ok = len(missing) == 0 and all(
        not any(
            isinstance(v, dict) and not v.get("ok", True)
            for v in r.values()
        )
        for r in results.values()
    )

    return {
        "ok": ok,
        "files_checked": len(all_files),
        "files_present": len(all_files) - len(missing),
        "files_missing": missing,
        "results": results,
    }
