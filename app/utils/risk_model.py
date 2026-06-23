"""
app/utils/risk_model.py —— 可燃风险评价模型（教学用）

核心功能：
- 估算虚拟空间中的气体体积分数浓度
- 计算风险比值 R = C_current / LFL_mix
- 根据 R 值判定教学风险等级

风险等级划分标准（教学参考用，非工程安全标准）：

    R < 0.25         → 低风险
    0.25 ≤ R < 0.50  → 关注
    0.50 ≤ R < 1.00  → 较高风险
    R ≥ 1.00         → 高风险

注意：
- 以上阈值仅用于教学演示和虚拟仿真，不适用于真实工程安全判定。
- 实际情况中可燃极限受温度、压力、惰性气体、通风等多因素影响。
- 本模型所有结论仅供化学实验教学参考。
"""

from typing import Optional, Dict


# ---- 风险等级常量 ----

RISK_THRESHOLDS: list = [
    (0.00, 0.25, "教学模型下低风险",
     "气体浓度远低于教学模型下的混合气体可燃下限，适合继续观察变量影响。"),
    (0.25, 0.50, "教学模型下关注",
     "气体浓度有所升高，接近教学模型下可燃下限的半数水平，建议关注通风与气体累积趋势。"),
    (0.50, 1.00, "教学模型下较高风险",
     "气体浓度已超过教学模型可燃下限的一半，在虚拟空间中需引起重视。"),
    (1.00, float("inf"), "教学模型下高风险",
     "气体浓度达到或超过教学模型下的混合气体可燃下限，仅表示虚拟仿真教学中的可燃性评价结果，不作为真实工程或消防应急判据。"),
]

# 通风因子映射（用于场景描述中的通风条件转换）。
# 数值表示教学稀释因子，越大表示滞留比例越低。
VENTILATION_FACTOR_MAP = {
    "none": 1.0,
    "poor": 1.0,
    "normal": 2.5,
    "good": 3.0,
}


def estimate_space_concentration(
    total_gas_l: float,
    space_volume_m3: float,
    ventilation_factor: float = 1.0,
) -> float:
    """
    估算虚拟空间中的总气体体积分数浓度（教学估算模型）。

    计算逻辑：
        space_volume_l = space_volume_m3 * 1000
        concentration_vol_pct = total_gas_l / space_volume_l * 100 / ventilation_factor

    Parameters
    ----------
    total_gas_l : float
        总产气量，单位 L。
    space_volume_m3 : float
        虚拟空间体积，单位 m³。
    ventilation_factor : float
        通风稀释因子。1.0 表示无额外稀释（密闭空间）；数值越大，稀释越强。

    Returns
    -------
    float
        当前空间总气体浓度（% vol）。

    Raises
    ------
    ValueError
        total_gas_l < 0、space_volume_m3 <= 0 或 ventilation_factor <= 0 时抛出。
    """
    if total_gas_l < 0:
        raise ValueError(f"总产气量不能为负数，当前值: {total_gas_l} L")
    if space_volume_m3 <= 0:
        raise ValueError(f"虚拟空间体积必须大于 0，当前值: {space_volume_m3} m³")
    if ventilation_factor <= 0:
        raise ValueError(f"通风稀释因子必须大于 0，当前值: {ventilation_factor}")

    if total_gas_l == 0.0:
        return 0.0

    space_volume_l = space_volume_m3 * 1000.0
    concentration_vol_pct = total_gas_l / space_volume_l * 100.0 / ventilation_factor

    return concentration_vol_pct


def calculate_risk_ratio(
    space_concentration: float,
    lfl_mix: Optional[float],
) -> Optional[float]:
    """
    计算风险比值 R（教学评价指标，非真实安全判据）。

    R = space_concentration / lfl_mix

    Parameters
    ----------
    space_concentration : float
        当前虚拟空间中可燃气体的总浓度（% vol）。
    lfl_mix : float or None
        混合气体可燃下限 LFL_mix（% vol），由 lfl_calculator.calculate_lfl_mix() 返回。
        如果为 None，表示无可燃气体或无法计算 LFL。

    Returns
    -------
    float or None
        风险比值 R。如果 lfl_mix 为 None 或 lfl_mix <= 0，返回 None。

    Raises
    ------
    ValueError
        space_concentration < 0 时抛出。
    """
    if space_concentration < 0:
        raise ValueError(f"空间气体浓度不能为负数，当前值: {space_concentration}")

    if lfl_mix is None:
        return None

    if lfl_mix <= 0:
        return None

    return space_concentration / lfl_mix


def classify_risk_level(risk_ratio: Optional[float]) -> Dict[str, str]:
    """
    根据教学风险比值 R 输出风险等级和解释文本。

    本分级仅用于虚拟仿真教学中的风险认知训练，
    不作为真实工程安全判据。

    分级标准（教学参考用）：
        R < 0.25          → 低风险
        0.25 ≤ R < 0.50   → 关注
        0.50 ≤ R < 1.00   → 较高风险
        R ≥ 1.00          → 高风险

    Parameters
    ----------
    risk_ratio : float or None
        风险比值 R，由 calculate_risk_ratio() 返回。
        如果为 None，表示缺少有效的 LFL 数据。

    Returns
    -------
    dict
        风险评价结果，格式为：
        {
            "level": "低风险" | "关注" | "较高风险" | "高风险" | "无法评价",
            "description": "对应的教学解释文本"
        }

    Raises
    ------
    ValueError
        risk_ratio 不是 None 但值 < 0 时抛出。
    """
    if risk_ratio is None:
        return {
            "level": "无法评价",
            "description": "缺少有效 LFL 或风险比值，无法进行教学风险分级。请检查输入的气体组成数据。",
            "model_boundary": "虚拟仿真教学模型，非真实事故预测、消防应急或工程防爆设计依据。",
        }

    if risk_ratio < 0:
        raise ValueError(f"风险比值 R 不能为负数，当前值: {risk_ratio}")

    for low, high, level, description in RISK_THRESHOLDS:
        if low <= risk_ratio < high:
            return {
                "level": level,
                "description": description,
                "model_boundary": "虚拟仿真教学模型，非真实事故预测、消防应急或工程防爆设计依据。",
            }

    # 兜底（理论上不会到达这里）
    return {
        "level": "教学模型下高风险",
        "description": "气体浓度已达到教学模型下的高风险水平，不作为真实工程安全判据。",
        "model_boundary": "虚拟仿真教学模型，非真实事故预测、消防应急或工程防爆设计依据。",
    }
