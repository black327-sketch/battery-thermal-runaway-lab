"""
tests/test_data_loader.py —— 数据加载模块单元测试

测试覆盖：
- load_gas_data 正常读取 + 文件不存在 / 空文件异常
- load_lfl_constants_data 正常读取 + 异常
- load_virtual_scenarios 正常读取 + 异常
- filter_literature_samples 按 cathode / soc / trigger_method 筛选
- filter_literature_samples 不存在的列名 → ValueError
- filter_literature_samples 不影响原 DataFrame
"""

import pytest
import tempfile
from pathlib import Path

import pandas as pd

from app.utils.data_loader import (
    EXPERIMENT_TEMPLATE_COLUMNS,
    load_gas_data,
    load_lfl_constants_data,
    load_virtual_scenarios,
    load_literature_metadata_template,
    load_battery_sample_template,
    load_arc_key_points_template,
    load_arc_curve_template,
    load_pressure_curve_template,
    load_gc_composition_template,
    load_gc_peaks_template,
    load_gas_volume_formula_template,
    load_lel_constants_reference_template,
    load_data_source_registry,
    validate_source_type_table,
    validate_data_source_registry,
    filter_literature_samples,
)


# ---- 测试用的 fixture 数据 ----

GAS_DATA_CSV_CONTENT = """source,SOC_pct,H2_pct,CO_pct,CO2_pct,CH4_pct,C2H4_pct,C2H6_pct,others_pct,notes
示例文献A_NCM111_100SOC,100,30.2,25.1,20.3,8.5,5.2,3.1,7.6,NCM111 体系 100% SOC 过充热失控
示例文献B_NCM523_100SOC,100,28.5,22.3,24.1,9.2,6.0,2.8,7.1,NCM523 体系 100% SOC 过热热失控
示例文献C_LFP_50SOC,50,22.0,18.5,30.2,10.1,7.5,4.2,7.5,LFP 体系 50% SOC 过热热失控
"""

LFL_CONSTANTS_CSV = """gas_name,gas_formula,LFL_vol_pct,UFL_vol_pct,is_combustible,notes
氢气,H2,4.0,75.0,true,最易点燃的热失控产气之一
一氧化碳,CO,12.5,74.0,true,有毒且可燃
"""

SCENARIOS_CSV = """scenario_id,room_volume_m3,temp_c,pressure_kpa,ventilation,gas_total_vol_pct,description
S001_实验室通风橱,2.0,25,101.3,poor,0.5,模拟实验室通风橱内微量气体累积
S002_小型实验舱,10.0,25,101.3,none,2.0,模拟小型密闭实验舱气体释放
"""


@pytest.fixture
def gas_data_path():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(GAS_DATA_CSV_CONTENT)
        temp_path = f.name
    yield Path(temp_path)
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def lfl_constants_path():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(LFL_CONSTANTS_CSV)
        temp_path = f.name
    yield Path(temp_path)
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def scenarios_path():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(SCENARIOS_CSV)
        temp_path = f.name
    yield Path(temp_path)
    Path(temp_path).unlink(missing_ok=True)


# ---- 测试 load_gas_data ----

def test_load_gas_data_success(gas_data_path):
    """正常读取产气数据。"""
    df = load_gas_data(gas_data_path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    expected_cols = ["source", "SOC_pct", "H2_pct", "CO_pct", "CO2_pct",
                     "CH4_pct", "C2H4_pct", "C2H6_pct", "others_pct", "notes"]
    for col in expected_cols:
        assert col in df.columns


def test_load_gas_data_file_not_found():
    """文件不存在抛出 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_gas_data("nonexistent.csv")


def test_load_gas_data_empty_csv():
    """空 CSV 抛出 ValueError。"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write("source,SOC_pct,H2_pct\n")  # 仅有表头
        temp_path = f.name
    try:
        with pytest.raises(ValueError, match="为空"):
            load_gas_data(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


# ---- 测试 load_lfl_constants_data ----

def test_load_lfl_constants_data_success(lfl_constants_path):
    """正常读取 LFL 常数表。"""
    df = load_lfl_constants_data(lfl_constants_path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2  # H2 + CO
    assert "gas_formula" in df.columns
    assert "LFL_vol_pct" in df.columns


def test_load_lfl_constants_data_file_not_found():
    """文件不存在抛出 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_lfl_constants_data("nonexistent.csv")


# ---- 测试 load_virtual_scenarios ----

def test_load_virtual_scenarios_success(scenarios_path):
    """正常读取虚拟场景数据。"""
    df = load_virtual_scenarios(scenarios_path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "scenario_id" in df.columns
    assert "room_volume_m3" in df.columns


def test_load_virtual_scenarios_file_not_found():
    """文件不存在抛出 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_virtual_scenarios("nonexistent.csv")


# ---- 测试 filter_literature_samples ----

def test_filter_by_cathode_source_column(gas_data_path):
    """通过 source 列中关键字筛选 cathode。"""
    df = load_gas_data(gas_data_path)
    result = filter_literature_samples(df, cathode="NCM111")
    assert len(result) == 1
    assert "NCM111" in result.iloc[0]["source"]


def test_filter_by_cathode_case_insensitive(gas_data_path):
    """cathode 筛选应大小写不敏感。"""
    df = load_gas_data(gas_data_path)
    result = filter_literature_samples(df, cathode="ncm523")
    assert len(result) == 1
    assert "NCM523" in result.iloc[0]["source"]


def test_filter_by_soc(gas_data_path):
    """按 SOC 筛选。"""
    df = load_gas_data(gas_data_path)
    result = filter_literature_samples(df, soc="100")
    assert len(result) == 2  # 两条 100% SOC 数据


def test_filter_by_soc_with_percent_sign(gas_data_path):
    """SOC="100%" 与 SOC="100" 应兼容。"""
    df = load_gas_data(gas_data_path)
    result = filter_literature_samples(df, soc="100%")
    assert len(result) == 2


def test_filter_by_soc_50(gas_data_path):
    """按 SOC=50 筛选。"""
    df = load_gas_data(gas_data_path)
    result = filter_literature_samples(df, soc="50")
    assert len(result) == 1
    assert "LFP" in result.iloc[0]["source"]


def test_filter_by_trigger_method(gas_data_path):
    """按触发方式筛选（notes 列子串匹配）。"""
    df = load_gas_data(gas_data_path)
    result = filter_literature_samples(df, trigger_method="过充")
    assert len(result) == 1
    assert "过充" in result.iloc[0]["notes"]


def test_filter_combined(gas_data_path):
    """组合筛选：cathode + soc。"""
    df = load_gas_data(gas_data_path)
    result = filter_literature_samples(df, cathode="NCM523", soc="100")
    assert len(result) == 1
    assert "NCM523" in result.iloc[0]["source"]


def test_filter_no_match(gas_data_path):
    """无匹配时返回空 DataFrame。"""
    df = load_gas_data(gas_data_path)
    result = filter_literature_samples(df, cathode="LCO")
    assert len(result) == 0


def test_filter_does_not_modify_original(gas_data_path):
    """筛选不修改原 DataFrame。"""
    df = load_gas_data(gas_data_path)
    original_len = len(df)
    _ = filter_literature_samples(df, cathode="NCM111")
    assert len(df) == original_len


def test_filter_none_params(gas_data_path):
    """所有参数为 None 时返回全部数据。"""
    df = load_gas_data(gas_data_path)
    result = filter_literature_samples(df)
    assert len(result) == len(df)


def test_filter_empty_string_params(gas_data_path):
    """空字符串参数等同于不筛选。"""
    df = load_gas_data(gas_data_path)
    result = filter_literature_samples(df, cathode="", soc="", trigger_method="")
    assert len(result) == len(df)


def test_filter_soc_column_not_found():
    """SOC 列不存在时抛出 ValueError 并列出可用列名。"""
    df = pd.DataFrame({"name": ["A", "B"], "value": [1, 2]})
    with pytest.raises(ValueError, match="SOC"):
        filter_literature_samples(df, soc="100")


def test_filter_trigger_column_not_found():
    """trigger_method 列不存在时抛出 ValueError。"""
    df = pd.DataFrame({"source": ["A", "B"]})
    with pytest.raises(ValueError, match="trigger_method"):
        filter_literature_samples(df, trigger_method="过充")


def test_template_loaders_default_paths():
    """新增文献接入模板可通过默认路径加载。"""
    loaders = [
        ("literature_metadata_template.csv", load_literature_metadata_template),
        ("battery_sample_template.csv", load_battery_sample_template),
        ("arc_key_points_template.csv", load_arc_key_points_template),
        ("arc_curve_template.csv", load_arc_curve_template),
        ("pressure_curve_template.csv", load_pressure_curve_template),
        ("gc_composition_template.csv", load_gc_composition_template),
        ("gc_peaks_template.csv", load_gc_peaks_template),
        ("gas_volume_formula_template.csv", load_gas_volume_formula_template),
        ("lel_constants_reference_template.csv", load_lel_constants_reference_template),
        ("data_source_registry.csv", load_data_source_registry),
    ]
    for file_name, loader in loaders:
        df = loader()
        assert isinstance(df, pd.DataFrame)
        for col in EXPERIMENT_TEMPLATE_COLUMNS[file_name]:
            assert col in df.columns


def test_template_loader_missing_file_returns_empty_dataframe():
    """模板文件不存在时返回空表而不是崩溃。"""
    missing = Path("not_exists") / "arc_curve_template.csv"
    df = load_arc_curve_template(missing)
    assert df.empty
    assert list(df.columns) == EXPERIMENT_TEMPLATE_COLUMNS["arc_curve_template.csv"]


def test_template_loader_adds_missing_columns(tmp_path):
    """字段缺失时补空列，便于后续数据整理。"""
    path = tmp_path / "gc_composition_template.csv"
    path.write_text("composition_id,source_type\nrow1,pending_user_input\n", encoding="utf-8")
    df = load_gc_composition_template(path)
    assert "gas_component" in df.columns
    assert "source_location" in df.columns
    assert df.loc[0, "source_type"] == "pending_user_input"


def test_invalid_source_type_rejected():
    df = pd.DataFrame({"source_type": ["invalid"]})
    with pytest.raises(ValueError, match="source_type"):
        validate_source_type_table(df)


def test_literature_row_requires_location_and_literature_id():
    df = pd.DataFrame(
        {
            "source_type": ["literature"],
            "literature_id": [""],
            "source_location": [""],
        }
    )
    with pytest.raises(ValueError, match="source_location|literature_id"):
        validate_source_type_table(df)


def test_registry_rejects_teaching_simulation_as_literature():
    df = pd.DataFrame(
        {
            "data_id": ["demo"],
            "data_file": ["demo.csv"],
            "data_type": ["curve"],
            "source_type": ["teaching_simulation"],
            "source_description": ["demo"],
            "is_literature": ["true"],
            "notes": ["bad"],
        }
    )
    with pytest.raises(ValueError, match="teaching_simulation"):
        validate_data_source_registry(df)
