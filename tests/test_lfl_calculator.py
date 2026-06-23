"""
tests/test_lfl_calculator.py —— LFL 计算模块单元测试

测试覆盖：
- load_lfl_constants 正常读取
- calculate_flammable_fraction 计算
- normalize_flammable_gases 归一化
- calculate_lfl_mix 完整计算
- 非可燃气体 (CO₂) 不参与计算
- 无可燃气体时返回 None
- 负数比例抛出 ValueError
- 文件不存在抛出 FileNotFoundError
"""

import pytest
import tempfile
from pathlib import Path

from app.utils.lfl_calculator import (
    load_lfl_constants,
    calculate_flammable_fraction,
    normalize_flammable_gases,
    calculate_lfl_mix,
)

# ---- 测试用的 fixture 数据 ----

LFL_CONSTANTS_CSV_CONTENT = """gas_name,gas_formula,LFL_vol_pct,UFL_vol_pct,is_combustible,notes
氢气,H2,4.0,75.0,true,最易点燃的热失控产气之一
一氧化碳,CO,12.5,74.0,true,有毒且可燃
甲烷,CH4,5.0,15.0,true,典型的可燃气体
乙烯,C2H4,2.7,36.0,true,LFL 较低，易点燃
乙烷,C2H6,3.0,12.5,true,常见于电解液分解产物
二氧化碳,CO2,,,false,不可燃，作为惰性稀释剂
氟化氢,HF,,,false,不可燃但剧毒，需注意安全
"""


@pytest.fixture
def lfl_csv_path():
    """创建临时 LFL 常数 CSV 文件。"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(LFL_CONSTANTS_CSV_CONTENT)
        temp_path = f.name
    yield Path(temp_path)
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def lfl_constants(lfl_csv_path):
    """加载的 LFL 常数字典。"""
    return load_lfl_constants(lfl_csv_path)


# ---- 测试 load_lfl_constants ----

def test_load_lfl_constants_success(lfl_constants):
    """正常读取：应返回 5 种可燃气体的 LFL 字典，CO2 和 HF 不在其中。"""
    assert isinstance(lfl_constants, dict)
    assert "H2" in lfl_constants
    assert "CO" in lfl_constants
    assert "CH4" in lfl_constants
    assert "C2H4" in lfl_constants
    assert "C2H6" in lfl_constants
    # 不可燃气体不应出现
    assert "CO2" not in lfl_constants
    assert "HF" not in lfl_constants
    # 验证具体值（单位 vol%，不转换为小数）
    assert lfl_constants["H2"] == 4.0
    assert lfl_constants["CO"] == 12.5
    assert lfl_constants["CH4"] == 5.0
    assert lfl_constants["C2H4"] == 2.7
    assert lfl_constants["C2H6"] == 3.0


def test_load_lfl_constants_file_not_found():
    """文件不存在时应抛出 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_lfl_constants("nonexistent_file.csv")


def test_load_lfl_constants_missing_columns():
    """缺少必要字段时抛出 ValueError。"""
    bad_csv = "name,symbol\nH2,4.0\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(bad_csv)
        bad_path = f.name
    try:
        with pytest.raises(ValueError, match="缺少必要字段"):
            load_lfl_constants(bad_path)
    finally:
        Path(bad_path).unlink(missing_ok=True)


# ---- 测试 calculate_flammable_fraction ----

def test_calculate_flammable_fraction_normal(lfl_constants):
    """正常混合气体：应正确计算可燃气体总比例。"""
    gas_comp = {"H2": 20.0, "CO": 10.0, "CH4": 5.0, "CO2": 65.0}
    result = calculate_flammable_fraction(gas_comp, lfl_constants)
    assert result == pytest.approx(35.0)


def test_calculate_flammable_fraction_all_nonflammable(lfl_constants):
    """全部为非可燃气体时应返回 0.0。"""
    gas_comp = {"CO2": 80.0, "HF": 20.0}
    result = calculate_flammable_fraction(gas_comp, lfl_constants)
    assert result == 0.0


def test_calculate_flammable_fraction_empty(lfl_constants):
    """空组成时应返回 0.0。"""
    result = calculate_flammable_fraction({}, lfl_constants)
    assert result == 0.0


def test_calculate_flammable_fraction_none_value(lfl_constants):
    """None 值应被忽略（按 0 处理）。"""
    gas_comp = {"H2": 10.0, "CO": None, "CH4": 5.0}
    result = calculate_flammable_fraction(gas_comp, lfl_constants)
    assert result == pytest.approx(15.0)


def test_calculate_flammable_fraction_negative_raises(lfl_constants):
    """负数比例应抛出 ValueError。"""
    gas_comp = {"H2": -5.0, "CO": 10.0}
    with pytest.raises(ValueError, match="不能为负数"):
        calculate_flammable_fraction(gas_comp, lfl_constants)


def test_calculate_flammable_fraction_empty_string(lfl_constants):
    """空字符串值应被忽略。"""
    gas_comp = {"H2": 10.0, "CO": "", "CH4": 5.0}
    result = calculate_flammable_fraction(gas_comp, lfl_constants)
    assert result == pytest.approx(15.0)


# ---- 测试 normalize_flammable_gases ----

def test_normalize_flammable_gases_normal(lfl_constants):
    """正常归一化：H2=20, CO=10, CH4=10 → H2=0.5, CO=0.25, CH4=0.25。"""
    gas_comp = {"H2": 20.0, "CO": 10.0, "CH4": 10.0}
    result = normalize_flammable_gases(gas_comp, lfl_constants)
    assert result == {"H2": 0.5, "CO": 0.25, "CH4": 0.25}


def test_normalize_flammable_gases_with_nonflammable(lfl_constants):
    """非可燃气体不应出现在结果中。"""
    gas_comp = {"H2": 40.0, "CO2": 60.0}
    result = normalize_flammable_gases(gas_comp, lfl_constants)
    assert "CO2" not in result
    assert result["H2"] == 1.0


def test_normalize_flammable_gases_no_flammable(lfl_constants):
    """无可燃气体时应返回空字典。"""
    gas_comp = {"CO2": 100.0}
    result = normalize_flammable_gases(gas_comp, lfl_constants)
    assert result == {}


def test_normalize_flammable_gases_empty(lfl_constants):
    """空气体组成时应返回空字典。"""
    result = normalize_flammable_gases({}, lfl_constants)
    assert result == {}


def test_normalize_flammable_gases_negative_raises(lfl_constants):
    """负数比例应抛出 ValueError。"""
    gas_comp = {"H2": -10.0, "CO": 10.0}
    with pytest.raises(ValueError, match="不能为负数"):
        normalize_flammable_gases(gas_comp, lfl_constants)


# ---- 测试 calculate_lfl_mix ----

def test_calculate_lfl_mix_normal(lfl_constants):
    """
    正常计算：使用已知的简化气体组成，验证 LFL_mix 输出。
    H₂=30.2, CO=25.1, CH₄=8.5, C₂H₄=5.2, C₂H₆=3.1（来自示例文献 A 的可燃部分）。

    归一化：
        total = 30.2+25.1+8.5+5.2+3.1 = 72.1
        y_H2  = 30.2/72.1 ≈ 0.4189
        y_CO  = 25.1/72.1 ≈ 0.3481
        y_CH4 = 8.5/72.1  ≈ 0.1179
        y_C2H4= 5.2/72.1  ≈ 0.0721
        y_C2H6= 3.1/72.1  ≈ 0.0430

    Σ(y_i/LFL_i) = 0.4189/4.0 + 0.3481/12.5 + 0.1179/5.0 + 0.0721/2.7 + 0.0430/3.0
                 ≈ 0.1047 + 0.0278 + 0.0236 + 0.0267 + 0.0143
                 ≈ 0.1971

    LFL_mix = 1/0.1971 ≈ 5.07 % vol
    """
    gas_comp = {
        "H2": 30.2,
        "CO": 25.1,
        "CO2": 20.3,
        "CH4": 8.5,
        "C2H4": 5.2,
        "C2H6": 3.1,
    }
    result = calculate_lfl_mix(gas_comp, lfl_constants)
    assert result is not None
    # 允许 ±0.2 的计算误差
    assert result == pytest.approx(5.07, abs=0.2)


def test_calculate_lfl_mix_no_flammable(lfl_constants):
    """无可燃气体时应返回 None。"""
    gas_comp = {"CO2": 80.0, "HF": 20.0}
    result = calculate_lfl_mix(gas_comp, lfl_constants)
    assert result is None


def test_calculate_lfl_mix_empty(lfl_constants):
    """空气体组成时应返回 None。"""
    result = calculate_lfl_mix({}, lfl_constants)
    assert result is None


def test_calculate_lfl_mix_nonflammable_ignored(lfl_constants):
    """CO₂ 不参与 LFL 计算。"""
    # 纯 H₂ 的 LFL 是 4.0
    gas_comp_1 = {"H2": 50.0, "CO2": 50.0}
    result_1 = calculate_lfl_mix(gas_comp_1, lfl_constants)
    assert result_1 is not None
    # 归一化后只有 H₂，y_H2=1.0，LFL_mix = 4.0
    assert result_1 == pytest.approx(4.0)

    # 换不同比例 CO₂，结果应相同
    gas_comp_2 = {"H2": 10.0, "CO2": 90.0}
    result_2 = calculate_lfl_mix(gas_comp_2, lfl_constants)
    assert result_2 == pytest.approx(4.0)


def test_calculate_lfl_mix_from_csv(lfl_csv_path):
    """集成测试：从 CSV 加载常数 → 计算 LFL_mix。"""
    lfl = load_lfl_constants(lfl_csv_path)
    gas_comp = {"H2": 40.0, "CO": 40.0}
    result = calculate_lfl_mix(gas_comp, lfl)
    assert result is not None
    # y_H2=0.5, y_CO=0.5 → Σ = 0.5/4.0 + 0.5/12.5 = 0.125 + 0.04 = 0.165
    # LFL_mix = 1/0.165 ≈ 6.06
    assert result == pytest.approx(6.06, abs=0.1)


def test_calculate_lfl_mix_negative_gas_raises(lfl_constants):
    """负数气体比例应抛出 ValueError。"""
    gas_comp = {"H2": -5.0, "CO": 10.0}
    with pytest.raises(ValueError, match="不能为负数"):
        calculate_lfl_mix(gas_comp, lfl_constants)
