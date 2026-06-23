"""
tests/test_data_quality.py —— 数据质量检查工具测试

测试数据质量工具对缺字段、空值、重复键、范围异常和空表的兼容性。
"""

import pandas as pd

from app.utils.data_quality import (
    check_duplicate_keys,
    check_missing_values,
    check_numeric_range,
    check_required_columns,
    check_source_completeness,
    summarize_data_quality,
    validate_lfl_constants,
    validate_literature_samples,
    validate_virtual_scenarios,
)


def test_required_columns_missing_detected():
    df = pd.DataFrame({"source": ["sample_a"]})
    issues = check_required_columns(df, ["source", "SOC_pct"])
    assert any(issue["column"] == "SOC_pct" for issue in issues)


def test_duplicate_keys_detected():
    df = pd.DataFrame({"source": ["sample_a", "sample_a", "sample_b"]})
    issues = check_duplicate_keys(df, "source")
    assert len(issues) == 2
    assert all(issue["check"] == "duplicate_keys" for issue in issues)


def test_numeric_range_outlier_detected():
    df = pd.DataFrame({"SOC_pct": [50, 120, -1]})
    issues = check_numeric_range(df, "SOC_pct", min_value=0, max_value=100)
    assert len(issues) == 2
    assert any("大于最大值" in issue["message"] for issue in issues)
    assert any("小于最小值" in issue["message"] for issue in issues)


def test_source_missing_detected():
    df = pd.DataFrame({"source": ["sample_a", ""], "DOI": [None, None]})
    issues = check_source_completeness(df, ["source", "DOI", "reliability_level"])
    assert any(issue["column"] == "source" for issue in issues)
    assert any(issue["column"] == "DOI" for issue in issues)
    assert any(issue["column"] == "reliability_level" for issue in issues)


def test_empty_dataframe_does_not_crash():
    df = pd.DataFrame(columns=["source", "SOC_pct"])
    assert check_missing_values(df, ["source"]) == []
    assert check_duplicate_keys(df, "source") == []
    assert check_numeric_range(df, "SOC_pct", 0, 100) == []
    summary = summarize_data_quality([])
    assert summary["total_issues"] == 0


def test_validate_lfl_constants_handles_missing_columns():
    df = pd.DataFrame({"gas_name": ["氢气"]})
    issues = validate_lfl_constants(df)
    assert any(issue["severity"] == "error" for issue in issues)
    assert any("LFL 常数表缺少字段" in issue["message"] for issue in issues)


def test_validate_literature_samples_handles_missing_columns():
    df = pd.DataFrame({"H2_pct": [10.0]})
    issues = validate_literature_samples(df)
    assert any(issue["column"] == "source" for issue in issues)
    assert any(issue["column"] == "SOC_pct" for issue in issues)


def test_validate_virtual_scenarios_handles_missing_columns():
    df = pd.DataFrame({"scenario_id": ["S001"]})
    issues = validate_virtual_scenarios(df)
    assert any(issue["column"] == "room_volume_m3" for issue in issues)
    assert any(issue["column"] == "ventilation" for issue in issues)


def test_validate_lfl_constants_accepts_template_columns():
    df = pd.DataFrame(
        {
            "formula": ["H2", "H2"],
            "is_flammable": [True, True],
            "LFL_vol_percent": [4.0, 4.0],
            "UFL_vol_percent": [75.0, 75.0],
        }
    )
    issues = validate_lfl_constants(df)
    assert any(issue["check"] == "duplicate_keys" for issue in issues)

