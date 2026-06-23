"""
app/utils/data_loader.py —— 数据加载与预处理

核心功能：
- 从 CSV 文件加载归一化产气组成样本
- 加载气体可燃极限常数
- 加载虚拟实验场景参数
- 按条件筛选文献样本

当前 CSV 中可能包含教学示例整理或待补充可核验来源的数据。
本模块只负责加载和基础筛选，不替任何样本补写文献来源。
"""

import pandas as pd
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DATA_DIR = PROJECT_ROOT / "data" / "experiment"
VALIDATED_DATA_DIR = EXPERIMENT_DATA_DIR / "validated"

ALLOWED_SOURCE_TYPES = {
    "literature",
    "teaching_interpolation",
    "teaching_simulation",
    "pending_user_input",
    "reference",
    "calculated_label",
}

ALLOWED_LITERATURE_DATA_STATUS = {
    "pending_extraction",
    "partially_extracted",
    "verified",
    "excluded",
}

EXPERIMENT_TEMPLATE_COLUMNS = {
    "literature_metadata_template.csv": [
        "literature_id",
        "title",
        "authors",
        "journal",
        "year",
        "doi",
        "experiment_type",
        "battery_type",
        "cell_format",
        "chemistry",
        "nominal_capacity",
        "notes",
        "data_status",
    ],
    "battery_sample_template.csv": [
        "sample_id",
        "literature_id",
        "battery_type",
        "cell_format",
        "chemistry",
        "cathode",
        "anode",
        "electrolyte",
        "nominal_capacity_ah",
        "nominal_voltage_v",
        "soc_pct",
        "mass_g",
        "energy_wh",
        "source_location",
        "source_type",
        "notes",
    ],
    "arc_key_points_template.csv": [
        "point_id",
        "literature_id",
        "sample_id",
        "soc_pct",
        "phase",
        "time_s",
        "temperature_c",
        "heating_rate_c_per_min",
        "pressure_kpa",
        "description",
        "source_location",
        "source_type",
        "notes",
    ],
    "arc_curve_template.csv": [
        "curve_id",
        "literature_id",
        "sample_id",
        "soc_pct",
        "time_s",
        "temperature_c",
        "heating_rate_c_per_min",
        "phase",
        "source_type",
        "source_location",
        "notes",
    ],
    "pressure_curve_template.csv": [
        "curve_id",
        "literature_id",
        "sample_id",
        "soc_pct",
        "time_s",
        "pressure_kpa",
        "phase",
        "source_type",
        "source_location",
        "notes",
    ],
    "gc_composition_template.csv": [
        "composition_id",
        "literature_id",
        "sample_id",
        "soc_pct",
        "gas_component",
        "volume_fraction_pct",
        "measurement_basis",
        "instrument",
        "detector",
        "source_location",
        "source_type",
        "notes",
    ],
    "gc_peaks_template.csv": [
        "peak_id",
        "literature_id",
        "sample_id",
        "soc_pct",
        "retention_time_min",
        "signal_intensity",
        "component",
        "detector",
        "source_location",
        "source_type",
        "notes",
    ],
    "gas_volume_formula_template.csv": [
        "formula_id",
        "literature_id",
        "sample_id",
        "soc_pct",
        "formula_name",
        "formula_expression",
        "parameter_name",
        "parameter_symbol",
        "parameter_value",
        "parameter_unit",
        "source_location",
        "source_type",
        "notes",
    ],
    "lel_constants_reference_template.csv": [
        "component",
        "lfl_vol_pct",
        "ufl_vol_pct",
        "standard_or_source",
        "source_title",
        "year",
        "doi_or_url",
        "temperature_c",
        "pressure_kpa",
        "applicability",
        "source_type",
        "notes",
    ],
    "data_source_registry.csv": [
        "data_id",
        "data_file",
        "data_type",
        "source_type",
        "source_description",
        "is_literature",
        "notes",
    ],
}


def _empty_template_df(file_name: str) -> pd.DataFrame:
    """按模板名返回空 DataFrame。"""
    return pd.DataFrame(columns=EXPERIMENT_TEMPLATE_COLUMNS[file_name])


def _default_template_path(file_name: str) -> Path:
    """返回项目内实验模板默认路径。"""
    return EXPERIMENT_DATA_DIR / file_name


def _read_template_csv(path, file_name: str) -> pd.DataFrame:
    """读取模板 CSV；文件不存在时返回带标准字段的空表。"""
    path = Path(path)
    if not path.exists():
        return _empty_template_df(file_name)
    df = pd.read_csv(path)
    required = EXPERIMENT_TEMPLATE_COLUMNS[file_name]
    for col in required:
        if col not in df.columns:
            df[col] = ""
    df = df[required + [c for c in df.columns if c not in required]]
    validate_source_type_table(df)
    if "data_status" in df.columns:
        invalid = set(df["data_status"].dropna().astype(str).str.strip()) - ALLOWED_LITERATURE_DATA_STATUS
        invalid.discard("")
        if invalid:
            raise ValueError(f"data_status 存在非法取值: {sorted(invalid)}")
    return df


def validate_source_type_table(df: pd.DataFrame) -> None:
    """校验 source_type 取值和文献数据定位信息。"""
    if df.empty or "source_type" not in df.columns:
        return
    source_values = df["source_type"].fillna("").astype(str).str.strip()
    invalid = set(source_values[source_values != ""]) - ALLOWED_SOURCE_TYPES
    if invalid:
        raise ValueError(f"source_type 存在非法取值: {sorted(invalid)}")
    literature_rows = df[source_values == "literature"]
    if literature_rows.empty:
        return
    if "source_location" in df.columns:
        missing_location = literature_rows["source_location"].fillna("").astype(str).str.strip().eq("")
        if missing_location.any():
            raise ValueError("source_type=literature 的记录必须填写 source_location。")
    if "literature_id" in df.columns:
        missing_lit = literature_rows["literature_id"].fillna("").astype(str).str.strip().eq("")
        if missing_lit.any():
            raise ValueError("source_type=literature 的记录必须填写 literature_id。")


def validate_data_source_registry(df: pd.DataFrame) -> None:
    """校验数据源登记表。"""
    required = set(EXPERIMENT_TEMPLATE_COLUMNS["data_source_registry.csv"])
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"data_source_registry.csv 缺少字段: {sorted(missing)}")
    validate_source_type_table(df)
    is_lit = df["is_literature"].astype(str).str.lower().str.strip()
    invalid_lit_flag = df[df["source_type"].eq("teaching_simulation") & is_lit.eq("true")]
    if not invalid_lit_flag.empty:
        raise ValueError("teaching_simulation 记录不能标记为 is_literature=True。")
    literature_rows = df[df["source_type"].eq("literature")]
    if not literature_rows.empty:
        bad_flags = literature_rows[~is_lit.loc[literature_rows.index].eq("true")]
        if not bad_flags.empty:
            raise ValueError("source_type=literature 的 registry 记录必须 is_literature=True。")
        missing_notes = literature_rows["notes"].fillna("").astype(str).str.strip().eq("")
        missing_desc = literature_rows["source_description"].fillna("").astype(str).str.strip().eq("")
        if (missing_notes | missing_desc).any():
            raise ValueError("source_type=literature 的 registry 记录必须提供 source_description 和 notes。")


def load_gas_data(data_path) -> pd.DataFrame:
    """
    读取归一化产气组成数据（normalized_gas_data.csv）。

    Parameters
    ----------
    data_path : str or Path
        normalized_gas_data.csv 的文件路径。

    Returns
    -------
    pd.DataFrame
        包含字段：source, SOC_pct, H2_pct, CO_pct, CO2_pct, CH4_pct,
        C2H4_pct, C2H6_pct, others_pct, notes

    Raises
    ------
    FileNotFoundError
        文件不存在。
    ValueError
        CSV 文件为空。
    """
    data_path = Path(data_path)

    if not data_path.exists():
        raise FileNotFoundError(f"产气数据文件不存在: {data_path}")

    df = pd.read_csv(data_path)

    if df.empty:
        raise ValueError(f"产气数据文件为空: {data_path}")

    return df


def load_lfl_constants_data(constants_path) -> pd.DataFrame:
    """
    读取纯物质气体可燃极限常数表（gas_lfl_constants.csv）。

    注意：此函数返回 DataFrame，供数据浏览使用。
    如需用于 LFL 计算的字典格式，请使用 lfl_calculator.load_lfl_constants()。

    Parameters
    ----------
    constants_path : str or Path
        gas_lfl_constants.csv 的文件路径。

    Returns
    -------
    pd.DataFrame
        包含字段：gas_name, gas_formula, LFL_vol_pct, UFL_vol_pct,
        is_combustible, notes

    Raises
    ------
    FileNotFoundError
        文件不存在。
    ValueError
        CSV 文件为空。
    """
    constants_path = Path(constants_path)

    if not constants_path.exists():
        raise FileNotFoundError(f"LFL 常数文件不存在: {constants_path}")

    df = pd.read_csv(constants_path)

    if df.empty:
        raise ValueError(f"LFL 常数文件为空: {constants_path}")

    return df


def load_virtual_scenarios(scenarios_path) -> pd.DataFrame:
    """
    读取虚拟实验场景参数（virtual_scenarios.csv）。

    Parameters
    ----------
    scenarios_path : str or Path
        virtual_scenarios.csv 的文件路径。

    Returns
    -------
    pd.DataFrame
        包含字段：scenario_id, room_volume_m3, temp_c, pressure_kpa,
        ventilation, gas_total_vol_pct, description

    Raises
    ------
    FileNotFoundError
        文件不存在。
    ValueError
        CSV 文件为空。
    """
    scenarios_path = Path(scenarios_path)

    if not scenarios_path.exists():
        raise FileNotFoundError(f"虚拟场景文件不存在: {scenarios_path}")

    df = pd.read_csv(scenarios_path)

    if df.empty:
        raise ValueError(f"虚拟场景文件为空: {scenarios_path}")

    return df


def load_literature_metadata_template(path=None) -> pd.DataFrame:
    """加载文献元数据模板。"""
    return _read_template_csv(path or _default_template_path("literature_metadata_template.csv"), "literature_metadata_template.csv")


def load_battery_sample_template(path=None) -> pd.DataFrame:
    """加载电池样品模板。"""
    return _read_template_csv(path or _default_template_path("battery_sample_template.csv"), "battery_sample_template.csv")


def load_arc_key_points_template(path=None) -> pd.DataFrame:
    """加载 ARC 关键节点模板。"""
    return _read_template_csv(path or _default_template_path("arc_key_points_template.csv"), "arc_key_points_template.csv")


def load_arc_curve_template(path=None) -> pd.DataFrame:
    """加载 ARC 曲线模板。"""
    return _read_template_csv(path or _default_template_path("arc_curve_template.csv"), "arc_curve_template.csv")


def load_pressure_curve_template(path=None) -> pd.DataFrame:
    """加载压力曲线模板。"""
    return _read_template_csv(path or _default_template_path("pressure_curve_template.csv"), "pressure_curve_template.csv")


def load_gc_composition_template(path=None) -> pd.DataFrame:
    """加载 GC 组分模板。"""
    return _read_template_csv(path or _default_template_path("gc_composition_template.csv"), "gc_composition_template.csv")


def load_gc_peaks_template(path=None) -> pd.DataFrame:
    """加载 GC 色谱峰模板。"""
    return _read_template_csv(path or _default_template_path("gc_peaks_template.csv"), "gc_peaks_template.csv")


def load_gas_volume_formula_template(path=None) -> pd.DataFrame:
    """加载产气量公式模板。"""
    return _read_template_csv(path or _default_template_path("gas_volume_formula_template.csv"), "gas_volume_formula_template.csv")


def load_lel_constants_reference_template(path=None) -> pd.DataFrame:
    """加载 LFL / UFL 常数来源模板。"""
    return _read_template_csv(path or _default_template_path("lel_constants_reference_template.csv"), "lel_constants_reference_template.csv")


def load_data_source_registry(path=None) -> pd.DataFrame:
    """加载并校验数据源登记表；文件不存在时返回空模板。"""
    df = _read_template_csv(path or _default_template_path("data_source_registry.csv"), "data_source_registry.csv")
    validate_data_source_registry(df)
    return df


def filter_literature_samples(
    df: pd.DataFrame,
    cathode: Optional[str] = None,
    soc: Optional[str] = None,
    trigger_method: Optional[str] = None,
) -> pd.DataFrame:
    """
    根据正极体系、SOC、触发方式筛选文献样本。

    筛选条件为 None 或空字符串时，不按该字段筛选。

    SOC 兼容处理：如果 SOC 列中同时存在整数值（如 100）和字符串值
    （如 "100%"），本函数会做简易兼容：将输入 SOC 去掉末尾的 "%" 后
    与列中的字符串形式和整数形式分别比对。

    Parameters
    ----------
    df : pd.DataFrame
        产气数据 DataFrame（由 load_gas_data() 返回）。
    cathode : str or None
        正极材料体系筛选关键字（如 "NCM111", "LFP"）。
        在 source 列中做子串匹配。
    soc : str or None
        SOC 筛选值，如 "100"、"50"、"100%"。
    trigger_method : str or None
        热失控触发方式筛选关键字（如 "过充", "过热"）。
        在 notes 列中做子串匹配。

    Returns
    -------
    pd.DataFrame
        筛选后的 DataFrame（副本，不修改原 DataFrame）。

    Raises
    ------
    ValueError
        指定的筛选字段在 CSV 中不存在时抛出，并列出可用列名。
    """
    result = df.copy()

    # ---- 按 cathode 筛选：在 source 列中做子串匹配 ----
    if cathode and cathode.strip():
        col = _resolve_column(df, ["cathode", "cathode_type", "正极体系"])
        if col is None:
            if "source" in df.columns:
                result = result[
                    result["source"].str.contains(
                        cathode.strip(), case=False, na=False
                    )
                ]
            else:
                raise ValueError(
                    f"未找到 cathode 对应列，当前可用列名: {list(df.columns)}。"
                    "请提供包含正极材料信息的 source 列或 cathode 列。"
                )
        else:
            result = result[
                result[col].astype(str).str.contains(cathode.strip(), case=False, na=False)
            ]

    # ---- 按 soc 筛选：兼容 "100" 和 "100%" ----
    if soc is not None and str(soc).strip():
        soc_val = str(soc).strip()
        # 去掉末尾的 %（如果存在）
        soc_normalized = soc_val.rstrip("%")

        col = _resolve_column(df, ["soc", "SOC", "SOC_pct", "soc_pct", "SOC (%)"])
        if col is None:
            raise ValueError(
                f"未找到 SOC 对应列，当前可用列名: {list(df.columns)}。"
            )

        # 兼容：列中可能为整数 100 或字符串 "100%" 两种形式
        col_as_str = result[col].astype(str).str.replace("%", "", regex=False)
        result = result[col_as_str == soc_normalized]

    # ---- 按 trigger_method 筛选：在 notes 列中做子串匹配 ----
    if trigger_method and trigger_method.strip():
        col = _resolve_column(
            df, ["trigger_method", "trigger", "触发方式", "notes"]
        )
        if col is None:
            raise ValueError(
                f"未找到 trigger_method 对应列，当前可用列名: {list(df.columns)}。"
            )

        result = result[
            result[col].astype(str).str.contains(
                trigger_method.strip(), case=False, na=False
            )
        ]

    return result


# ═══════════════════════════════════════════════════════════════
# validated/ 模板列名定义
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# validated/ 模板加载函数
# ═══════════════════════════════════════════════════════════════

def _empty_validated_df(file_name: str) -> pd.DataFrame:
    """返回指定 validated 模板文件的空 DataFrame（含正确列名）。"""
    cols = VALIDATED_TEMPLATE_COLUMNS.get(file_name, [])
    return pd.DataFrame(columns=cols)


def _read_validated_csv(file_name: str, path=None) -> pd.DataFrame:
    """读取 validated 目录下的 CSV 文件。

    文件不存在时返回带标准列名的空 DataFrame，不崩溃。
    """
    target = Path(path) if path else (VALIDATED_DATA_DIR / file_name)
    cols = VALIDATED_TEMPLATE_COLUMNS.get(file_name, [])
    if not target.exists():
        return pd.DataFrame(columns=cols)
    try:
        df = pd.read_csv(target)
    except Exception:
        return pd.DataFrame(columns=cols)
    # 补全缺失列
    for col in cols:
        if col not in df.columns:
            df[col] = ""
    return df


def load_validated_literature_metadata(path=None) -> pd.DataFrame:
    """加载真实文献元数据模板。"""
    return _read_validated_csv("literature_metadata_validated.csv", path)


def load_validated_battery_sample(path=None) -> pd.DataFrame:
    """加载真实电池样品模板。"""
    return _read_validated_csv("battery_sample_validated.csv", path)


def load_validated_thermal_runaway_stage(path=None) -> pd.DataFrame:
    """加载热失控阶段划分模板。"""
    return _read_validated_csv("thermal_runaway_stage_validated.csv", path)


def load_validated_reaction_mechanism(path=None) -> pd.DataFrame:
    """加载反应机理模板。"""
    return _read_validated_csv("reaction_mechanism_validated.csv", path)


def load_validated_gas_generation_reaction(path=None) -> pd.DataFrame:
    """加载产气反应方程模板。"""
    return _read_validated_csv("gas_generation_reaction_validated.csv", path)


def load_validated_gc_composition(path=None) -> pd.DataFrame:
    """加载真实 GC 气体组成模板。"""
    return _read_validated_csv("gc_composition_validated.csv", path)


def load_validated_lel_constants_reference(path=None) -> pd.DataFrame:
    """加载真实 LFL/UFL 常数来源模板。"""
    return _read_validated_csv("lel_constants_reference_validated.csv", path)


def load_mechanism_visual_assets(path=None) -> pd.DataFrame:
    """加载机理可视化素材模板。"""
    return _read_validated_csv("mechanism_visual_assets.csv", path)


def load_mechanism_video_assets(path=None) -> pd.DataFrame:
    """加载机理可视化视频素材模板。"""
    return _read_validated_csv("mechanism_video_assets.csv", path)


def _resolve_column(df: pd.DataFrame, candidates: list) -> Optional[str]:
    """
    在 DataFrame 中查找第一个存在的候选列名（大小写不敏感）。

    Parameters
    ----------
    df : pd.DataFrame
        要搜索的 DataFrame。
    candidates : list of str
        候选列名列表。

    Returns
    -------
    str or None
        找到的第一个匹配列名，或 None。
    """
    df_cols_lower = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in df_cols_lower:
            return df_cols_lower[candidate.lower()]
    return None
