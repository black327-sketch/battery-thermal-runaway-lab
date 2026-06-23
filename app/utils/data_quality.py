"""
app/utils/data_quality.py —— 数据质量检查工具

提供 CSV 数据字段、缺失值、数值范围、重复键和来源完整性的轻量检查。
本模块只返回检查结果，不修改原始数据，也不参与核心计算逻辑。
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Any

import pandas as pd


Issue = dict[str, Any]


def _new_issue(
    check: str,
    message: str,
    severity: str = "warning",
    column: str | None = None,
    row: int | None = None,
) -> Issue:
    """构造统一的数据质量问题记录。"""
    return {
        "check": check,
        "severity": severity,
        "column": column,
        "row": row,
        "message": message,
    }


def check_required_columns(
    df: pd.DataFrame,
    required_columns: Iterable[str],
) -> list[Issue]:
    """检查必填字段是否存在。"""
    existing = set(df.columns)
    issues: list[Issue] = []
    for column in required_columns:
        if column not in existing:
            issues.append(
                _new_issue(
                    check="required_columns",
                    severity="error",
                    column=column,
                    message=f"缺少必填字段：{column}",
                )
            )
    return issues


def check_missing_values(
    df: pd.DataFrame,
    required_columns: Iterable[str],
) -> list[Issue]:
    """检查关键字段是否存在空值。缺失字段会作为问题返回。"""
    issues: list[Issue] = []
    for column in required_columns:
        if column not in df.columns:
            issues.append(
                _new_issue(
                    check="missing_values",
                    severity="error",
                    column=column,
                    message=f"无法检查空值，字段不存在：{column}",
                )
            )
            continue
        if df.empty:
            continue
        missing_mask = df[column].isna() | df[column].astype(str).str.strip().eq("")
        for row in df.index[missing_mask].tolist():
            issues.append(
                _new_issue(
                    check="missing_values",
                    severity="warning",
                    column=column,
                    row=int(row) if isinstance(row, int) else None,
                    message=f"字段 {column} 存在空值",
                )
            )
    return issues


def check_numeric_range(
    df: pd.DataFrame,
    column: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> list[Issue]:
    """检查数值字段是否在给定范围内。"""
    if column not in df.columns:
        return [
            _new_issue(
                check="numeric_range",
                severity="error",
                column=column,
                message=f"无法检查数值范围，字段不存在：{column}",
            )
        ]
    if df.empty:
        return []

    issues: list[Issue] = []
    numeric_values = pd.to_numeric(df[column], errors="coerce")
    invalid_mask = df[column].notna() & numeric_values.isna()
    for row in df.index[invalid_mask].tolist():
        issues.append(
            _new_issue(
                check="numeric_range",
                severity="error",
                column=column,
                row=int(row) if isinstance(row, int) else None,
                message=f"字段 {column} 存在非数值内容",
            )
        )

    if min_value is not None:
        low_mask = numeric_values.notna() & (numeric_values < min_value)
        for row in df.index[low_mask].tolist():
            issues.append(
                _new_issue(
                    check="numeric_range",
                    severity="warning",
                    column=column,
                    row=int(row) if isinstance(row, int) else None,
                    message=f"字段 {column} 小于最小值 {min_value}",
                )
            )
    if max_value is not None:
        high_mask = numeric_values.notna() & (numeric_values > max_value)
        for row in df.index[high_mask].tolist():
            issues.append(
                _new_issue(
                    check="numeric_range",
                    severity="warning",
                    column=column,
                    row=int(row) if isinstance(row, int) else None,
                    message=f"字段 {column} 大于最大值 {max_value}",
                )
            )
    return issues


def check_duplicate_keys(df: pd.DataFrame, key_column: str) -> list[Issue]:
    """检查主键字段是否存在重复值。"""
    if key_column not in df.columns:
        return [
            _new_issue(
                check="duplicate_keys",
                severity="error",
                column=key_column,
                message=f"无法检查重复键，字段不存在：{key_column}",
            )
        ]
    if df.empty:
        return []

    issues: list[Issue] = []
    duplicated = df[df[key_column].duplicated(keep=False)]
    for row, value in duplicated[key_column].items():
        issues.append(
            _new_issue(
                check="duplicate_keys",
                severity="warning",
                column=key_column,
                row=int(row) if isinstance(row, int) else None,
                message=f"字段 {key_column} 存在重复值：{value}",
            )
        )
    return issues


def check_source_completeness(
    df: pd.DataFrame,
    source_columns: Iterable[str],
) -> list[Issue]:
    """检查来源相关字段是否存在及其完整率。"""
    issues: list[Issue] = []
    row_count = len(df)
    for column in source_columns:
        if column not in df.columns:
            issues.append(
                _new_issue(
                    check="source_completeness",
                    severity="info",
                    column=column,
                    message=f"来源字段待补充：{column}",
                )
            )
            continue
        if row_count == 0:
            continue
        filled = df[column].notna() & ~df[column].astype(str).str.strip().eq("")
        completeness = float(filled.sum() / row_count)
        if completeness < 1.0:
            issues.append(
                _new_issue(
                    check="source_completeness",
                    severity="warning",
                    column=column,
                    message=f"字段 {column} 完整率为 {completeness:.0%}",
                )
            )
    return issues


def summarize_data_quality(issues: list[Issue]) -> dict[str, Any]:
    """汇总数据质量问题，返回结构化统计。"""
    severity_counter = Counter(issue.get("severity", "unknown") for issue in issues)
    check_counter = Counter(issue.get("check", "unknown") for issue in issues)
    return {
        "total_issues": len(issues),
        "by_severity": dict(severity_counter),
        "by_check": dict(check_counter),
        "issues": issues,
    }


def _first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    """返回第一个存在的候选字段。"""
    for column in candidates:
        if column in df.columns:
            return column
    return None


def validate_lfl_constants(df: pd.DataFrame) -> list[Issue]:
    """检查 LFL/UFL 常数数据质量，兼容当前文件和后续模板字段。"""
    issues: list[Issue] = []
    formula_col = _first_existing_column(df, ["gas_formula", "formula"])
    flammable_col = _first_existing_column(df, ["is_combustible", "is_flammable"])
    lfl_col = _first_existing_column(df, ["LFL_vol_pct", "LFL_vol_percent"])
    ufl_col = _first_existing_column(df, ["UFL_vol_pct", "UFL_vol_percent"])

    for logical_name, column in {
        "气体分子式": formula_col,
        "是否可燃": flammable_col,
        "LFL": lfl_col,
    }.items():
        if column is None:
            issues.append(
                _new_issue(
                    check="lfl_constants",
                    severity="error",
                    message=f"LFL 常数表缺少字段：{logical_name}",
                )
            )

    if formula_col:
        issues.extend(check_missing_values(df, [formula_col]))
        issues.extend(check_duplicate_keys(df, formula_col))
    if lfl_col:
        issues.extend(check_numeric_range(df, lfl_col, min_value=0.0, max_value=100.0))
    if ufl_col:
        issues.extend(check_numeric_range(df, ufl_col, min_value=0.0, max_value=100.0))

    source_cols = ["source", "source_type", "reliability_level", "CAS_number"]
    issues.extend(check_source_completeness(df, source_cols))
    return issues


def validate_literature_samples(df: pd.DataFrame) -> list[Issue]:
    """检查文献样本数据质量。"""
    required = ["source", "SOC_pct"]
    gas_columns = [column for column in df.columns if column.endswith("_pct") and column != "SOC_pct"]
    issues = check_required_columns(df, required)
    existing_required = [column for column in required if column in df.columns]
    issues.extend(check_missing_values(df, existing_required))

    if "source" in df.columns:
        issues.extend(check_duplicate_keys(df, "source"))
    if "SOC_pct" in df.columns:
        issues.extend(check_numeric_range(df, "SOC_pct", min_value=0.0, max_value=100.0))
    if not gas_columns:
        issues.append(
            _new_issue(
                check="literature_samples",
                severity="warning",
                message="未识别到气体组成字段（*_pct）",
            )
        )
    for column in gas_columns:
        issues.extend(check_numeric_range(df, column, min_value=0.0, max_value=100.0))

    issues.extend(check_source_completeness(df, ["source", "DOI", "reference", "reliability_level"]))
    return issues


def validate_virtual_scenarios(df: pd.DataFrame) -> list[Issue]:
    """检查虚拟场景数据质量。"""
    required = ["scenario_id", "room_volume_m3", "ventilation"]
    issues = check_required_columns(df, required)
    existing_required = [column for column in required if column in df.columns]
    issues.extend(check_missing_values(df, existing_required))

    if "scenario_id" in df.columns:
        issues.extend(check_duplicate_keys(df, "scenario_id"))
    if "room_volume_m3" in df.columns:
        issues.extend(check_numeric_range(df, "room_volume_m3", min_value=0.0))
    if "gas_total_vol_pct" in df.columns:
        issues.extend(check_numeric_range(df, "gas_total_vol_pct", min_value=0.0, max_value=100.0))
    if "temp_c" in df.columns:
        issues.extend(check_numeric_range(df, "temp_c"))
    if "pressure_kpa" in df.columns:
        issues.extend(check_numeric_range(df, "pressure_kpa", min_value=0.0))
    issues.extend(check_source_completeness(df, ["source", "reliability_level"]))
    return issues

