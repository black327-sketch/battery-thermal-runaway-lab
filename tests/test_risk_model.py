"""
tests/test_risk_model.py —— 风险评价模型单元测试

测试覆盖：
- estimate_space_concentration 正常计算
- space_volume_m3 / ventilation_factor 无效参数 → ValueError
- calculate_risk_ratio 正常计算
- lfl_mix 为 None 或 0 → 返回 None
- classify_risk_level 四个风险等级
- risk_ratio 为 None → "无法评价"
- risk_ratio < 0 → ValueError
"""

import pytest

from app.utils.risk_model import (
    estimate_space_concentration,
    calculate_risk_ratio,
    classify_risk_level,
)


# ---- 测试 estimate_space_concentration ----

def test_estimate_space_concentration_normal():
    """
    正常计算：
    1000 L 气体 + 100 m³ 空间 + 通风因子 1.0
    = 1000 / (100*1000) * 100 / 1.0 = 1.0 % vol
    """
    result = estimate_space_concentration(
        total_gas_l=1000.0, space_volume_m3=100.0, ventilation_factor=1.0
    )
    assert result == pytest.approx(1.0)


def test_estimate_space_concentration_zero_gas():
    """总产气量为 0 时应返回 0.0。"""
    result = estimate_space_concentration(
        total_gas_l=0.0, space_volume_m3=10.0
    )
    assert result == 0.0


def test_estimate_space_concentration_with_ventilation():
    """通风稀释：ventilation_factor=5.0 应降低浓度。"""
    result_no_vent = estimate_space_concentration(
        total_gas_l=500.0, space_volume_m3=50.0, ventilation_factor=1.0
    )
    result_with_vent = estimate_space_concentration(
        total_gas_l=500.0, space_volume_m3=50.0, ventilation_factor=5.0
    )
    assert result_no_vent == pytest.approx(1.0)
    assert result_with_vent == pytest.approx(0.2)


def test_estimate_concentration_negative_gas():
    """负数产气量抛出 ValueError。"""
    with pytest.raises(ValueError, match="总产气量不能为负数"):
        estimate_space_concentration(total_gas_l=-1.0, space_volume_m3=10.0)


def test_estimate_concentration_zero_volume():
    """空间体积为 0 抛出 ValueError。"""
    with pytest.raises(ValueError, match="虚拟空间体积必须大于 0"):
        estimate_space_concentration(total_gas_l=10.0, space_volume_m3=0.0)


def test_estimate_concentration_negative_volume():
    """空间体积为负数抛出 ValueError。"""
    with pytest.raises(ValueError, match="虚拟空间体积必须大于 0"):
        estimate_space_concentration(total_gas_l=10.0, space_volume_m3=-5.0)


def test_estimate_concentration_zero_ventilation():
    """通风因子为 0 抛出 ValueError。"""
    with pytest.raises(ValueError, match="通风稀释因子必须大于 0"):
        estimate_space_concentration(
            total_gas_l=10.0, space_volume_m3=10.0, ventilation_factor=0.0
        )


def test_estimate_concentration_negative_ventilation():
    """通风因子为负数抛出 ValueError。"""
    with pytest.raises(ValueError, match="通风稀释因子必须大于 0"):
        estimate_space_concentration(
            total_gas_l=10.0, space_volume_m3=10.0, ventilation_factor=-1.0
        )


def test_estimate_concentration_small_volume():
    """小空间：10 L 气体在 1 m³ 空间中 = 1.0%。"""
    result = estimate_space_concentration(
        total_gas_l=10.0, space_volume_m3=1.0
    )
    assert result == pytest.approx(1.0)


# ---- 测试 calculate_risk_ratio ----

def test_calculate_risk_ratio_normal():
    """浓度 2.0%，LFL_mix 5.0% → R = 0.4。"""
    result = calculate_risk_ratio(space_concentration=2.0, lfl_mix=5.0)
    assert result == pytest.approx(0.4)


def test_calculate_risk_ratio_below_lfl():
    """浓度远低于 LFL → R < 1。"""
    result = calculate_risk_ratio(space_concentration=0.1, lfl_mix=5.0)
    assert result == pytest.approx(0.02)


def test_calculate_risk_ratio_at_lfl():
    """浓度等于 LFL → R = 1.0。"""
    result = calculate_risk_ratio(space_concentration=5.0, lfl_mix=5.0)
    assert result == pytest.approx(1.0)


def test_calculate_risk_ratio_above_lfl():
    """浓度大于 LFL → R > 1.0。"""
    result = calculate_risk_ratio(space_concentration=10.0, lfl_mix=5.0)
    assert result == pytest.approx(2.0)


def test_calculate_risk_ratio_lfl_none():
    """lfl_mix 为 None 时返回 None。"""
    result = calculate_risk_ratio(space_concentration=2.0, lfl_mix=None)
    assert result is None


def test_calculate_risk_ratio_lfl_zero():
    """lfl_mix 为 0 时返回 None。"""
    result = calculate_risk_ratio(space_concentration=2.0, lfl_mix=0.0)
    assert result is None


def test_calculate_risk_ratio_lfl_negative():
    """lfl_mix 为负数时返回 None。"""
    result = calculate_risk_ratio(space_concentration=2.0, lfl_mix=-1.0)
    assert result is None


def test_calculate_risk_ratio_negative_concentration():
    """负数浓度抛出 ValueError。"""
    with pytest.raises(ValueError, match="空间气体浓度不能为负数"):
        calculate_risk_ratio(space_concentration=-1.0, lfl_mix=5.0)


# ---- 测试 classify_risk_level ----

def test_classify_risk_level_low():
    """R < 0.25 → 低风险。"""
    result = classify_risk_level(0.1)
    assert result["level"] == "教学模型下低风险"
    assert "description" in result
    assert len(result["description"]) > 0
    assert "model_boundary" in result


def test_classify_risk_level_watch():
    """0.25 ≤ R < 0.50 → 关注。"""
    result = classify_risk_level(0.30)
    assert result["level"] == "教学模型下关注"


def test_classify_risk_level_elevated():
    """0.50 ≤ R < 1.00 → 较高风险。"""
    result = classify_risk_level(0.60)
    assert result["level"] == "教学模型下较高风险"


def test_classify_risk_level_high():
    """R ≥ 1.00 → 高风险。"""
    result = classify_risk_level(1.0)
    assert result["level"] == "教学模型下高风险"


def test_classify_risk_level_high_above_one():
    """R > 1.0 → 高风险。"""
    result = classify_risk_level(2.5)
    assert result["level"] == "教学模型下高风险"


def test_classify_risk_level_boundary_low_watch():
    """边界值：R=0.25 → 关注（左闭右开区间）。"""
    result = classify_risk_level(0.25)
    assert result["level"] == "教学模型下关注"


def test_classify_risk_level_boundary_watch_elevated():
    """边界值：R=0.50 → 较高风险。"""
    result = classify_risk_level(0.50)
    assert result["level"] == "教学模型下较高风险"


def test_classify_risk_level_boundary_elevated_high():
    """边界值：R=1.00 → 高风险。"""
    result = classify_risk_level(1.00)
    assert result["level"] == "教学模型下高风险"


def test_classify_risk_level_none():
    """risk_ratio 为 None → 无法评价。"""
    result = classify_risk_level(None)
    assert result["level"] == "无法评价"
    assert "description" in result


def test_classify_risk_level_negative_raises():
    """负数 risk_ratio 抛出 ValueError。"""
    with pytest.raises(ValueError, match="风险比值 R 不能为负数"):
        classify_risk_level(-0.1)


def test_classify_risk_level_zero():
    """R=0.0 → 低风险。"""
    result = classify_risk_level(0.0)
    assert result["level"] == "教学模型下低风险"


# ---- 集成测试：浓度 → R → 风险等级 ----

def test_full_risk_pipeline():
    """完整的风险评价流水线。"""
    # 虚拟空间 50 m³，产气 250 L，通风因子 1.0
    # concentration = 250/(50*1000)*100/1.0 = 0.5% vol
    conc = estimate_space_concentration(
        total_gas_l=250.0, space_volume_m3=50.0, ventilation_factor=1.0
    )
    lfl_mix = 5.0  # 假设 LFL_mix = 5.0%
    r = calculate_risk_ratio(conc, lfl_mix)
    # R = 0.5/5.0 = 0.1
    assert r == pytest.approx(0.1)
    level = classify_risk_level(r)
    assert level["level"] == "教学模型下低风险"
