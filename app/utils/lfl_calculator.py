"""
app/utils/lfl_calculator.py —— 混合气体可燃下限 (LFL) 计算

核心功能：
- 基于 Le Chatelier 混合规则计算 LFL_mix
- 支持多组分混合气体（H₂, CO, CO₂, CH₄, C₂H₄, C₂H₆ 等）

计算公式（教学估算模型）：
    LFL_mix = 1 / Σ (y_i / LFL_i)

其中：
    y_i  — 组分 i 在可燃气体中的摩尔/体积分数（0–1，仅可燃组分归一化）
    LFL_i — 组分 i 的纯物质可燃下限（% vol，空气中）

注意：
- 本模块所有计算均为基于公开文献数据的教学估算，不用于真实工程安全判定。
- CO₂ 不可燃，不参与 LFL_mix 计算，但影响惰性稀释效应（本版暂不修正）。
- HF 不可燃，不参与 LFL_mix 计算。
"""

import csv
from pathlib import Path
from typing import Dict, Optional


def load_lfl_constants(constants_path) -> Dict[str, float]:
    """
    从 CSV 文件读取纯物质可燃气体 LFL 常数。

    读取 gas_lfl_constants.csv，返回以气体分子式（gas_formula）为 key、
    LFL_vol_pct 为 value 的字典。仅包含可燃气体（is_combustible=true 且 LFL_vol_pct 有效）。

    Parameters
    ----------
    constants_path : str or Path
        gas_lfl_constants.csv 的文件路径。

    Returns
    -------
    dict
        可燃气体 LFL 常数字典，格式如 {"H2": 4.0, "CO": 12.5, "CH4": 5.0, ...}。
        LFL 单位为 vol%，不转换为小数。

    Raises
    ------
    FileNotFoundError
        指定路径的文件不存在。
    ValueError
        CSV 缺少必要字段（gas_formula, LFL_vol_pct, is_combustible），
        或文件中无可燃气体数据。
    """
    constants_path = Path(constants_path)

    if not constants_path.exists():
        raise FileNotFoundError(f"LFL 常数文件不存在: {constants_path}")

    lfl_dict: Dict[str, float] = {}

    with open(constants_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required_cols = {"gas_formula", "LFL_vol_pct", "is_combustible"}
        if not required_cols.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                f"CSV 缺少必要字段，需要 {required_cols}，"
                f"实际列名: {reader.fieldnames}"
            )

        for row in reader:
            is_combustible = (row.get("is_combustible", "").strip().lower() == "true")
            if not is_combustible:
                continue

            formula = row.get("gas_formula", "").strip()
            lfl_str = row.get("LFL_vol_pct", "").strip()

            if not formula:
                continue

            if not lfl_str or lfl_str == "":
                continue

            try:
                lfl_val = float(lfl_str)
            except (ValueError, TypeError):
                continue

            if lfl_val <= 0:
                raise ValueError(
                    f"气体 {formula} 的 LFL 值无效 ({lfl_val})，必须大于 0。"
                )

            lfl_dict[formula] = lfl_val

    if not lfl_dict:
        raise ValueError("未能从 CSV 中读取到任何可燃气体 LFL 数据。")

    return lfl_dict


def calculate_flammable_fraction(
    gas_composition: Dict[str, float],
    lfl_constants: Dict[str, float],
) -> float:
    """
    计算气体组成中可燃气体的总比例。

    仅统计存在于 lfl_constants 中的可燃气体，CO₂、HF、N₂ 等非可燃气体不参与计算。

    Parameters
    ----------
    gas_composition : dict
        气体组成字典，key 为气体分子式（如 "H2", "CO", "CO2"），
        value 为体积百分比（% vol）。例如 {"H2": 30.2, "CO": 25.1, "CO2": 20.3}。
    lfl_constants : dict
        可燃气体 LFL 常数字典，由 load_lfl_constants() 返回。

    Returns
    -------
    float
        可燃气体在总气体组成中的体积百分比之和（% vol）。
        例如 H2=20, CO=10, CH4=5, CO2=65 返回 35.0。

    Raises
    ------
    ValueError
        任意气体比例为负数时抛出。
    """
    if not gas_composition:
        return 0.0

    total_flammable = 0.0

    for gas, value in gas_composition.items():
        if gas not in lfl_constants:
            continue

        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue

        try:
            val = float(value)
        except (ValueError, TypeError):
            continue

        if val < 0:
            raise ValueError(
                f"气体 {gas} 的比例不能为负数，当前值: {val}"
            )

        total_flammable += val

    return total_flammable


def normalize_flammable_gases(
    gas_composition: Dict[str, float],
    lfl_constants: Dict[str, float],
) -> Dict[str, float]:
    """
    将可燃气体归一化为"可燃组分内部体积分数"，使可燃组分之和为 1.0。

    非可燃气体（不在 lfl_constants 中的气体）不出现在结果中。

    Parameters
    ----------
    gas_composition : dict
        气体组成字典，包含可燃和不可燃组分的体积百分比。
    lfl_constants : dict
        可燃气体 LFL 常数字典，由 load_lfl_constants() 返回。

    Returns
    -------
    dict
        归一化后的可燃气体体积分数，各值之和为 1.0。
        例如 H2=20, CO=10, CH4=10 返回 {"H2": 0.5, "CO": 0.25, "CH4": 0.25}。
        如果没有可燃气体，返回空字典 {}。

    Raises
    ------
    ValueError
        任意可燃气体比例为负数时抛出。
    """
    if not gas_composition:
        return {}

    # 提取可燃气体的原始比例
    flammable_raw: Dict[str, float] = {}

    for gas, value in gas_composition.items():
        if gas not in lfl_constants:
            continue

        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue

        try:
            val = float(value)
        except (ValueError, TypeError):
            continue

        if val < 0:
            raise ValueError(
                f"气体 {gas} 的比例不能为负数，当前值: {val}"
            )

        flammable_raw[gas] = val

    if not flammable_raw:
        return {}

    total = sum(flammable_raw.values())

    if total <= 0:
        return {}

    return {gas: frac / total for gas, frac in flammable_raw.items()}


def calculate_lfl_mix(
    gas_composition: Dict[str, float],
    lfl_constants: Dict[str, float],
) -> Optional[float]:
    """
    使用 Le Chatelier 混合规则计算混合气体的可燃下限 LFL_mix。

    计算公式（教学估算模型）：
        LFL_mix = 1 / Σ (y_i / LFL_i)

    其中 y_i 为可燃组分归一化体积分数（由 normalize_flammable_gases() 计算），
    LFL_i 为纯物质可燃下限（% vol）。

    本计算为基于公开文献数据和教学规则模型的虚拟仿真，
    不用于真实工程安全判定。

    Parameters
    ----------
    gas_composition : dict
        气体组成字典，包含可燃和不可燃组分的体积百分比。
    lfl_constants : dict
        可燃气体 LFL 常数字典，由 load_lfl_constants() 返回。

    Returns
    -------
    float or None
        混合气体的可燃下限 LFL_mix（% vol）。
        如果没有可燃气体，返回 None。

    Raises
    ------
    ValueError
        任意可燃气体比例为负数时抛出。
        某个可燃气体的 LFL 值 ≤ 0 时抛出。
    """
    normalized = normalize_flammable_gases(gas_composition, lfl_constants)

    if not normalized:
        return None

    denominator = 0.0

    for gas, y_i in normalized.items():
        lfl_i = lfl_constants.get(gas)

        if lfl_i is None:
            continue

        if lfl_i <= 0:
            raise ValueError(
                f"气体 {gas} 的 LFL 值无效 ({lfl_i})，必须大于 0。"
            )

        denominator += y_i / lfl_i

    if denominator <= 0:
        return None

    lfl_mix = 1.0 / denominator

    return lfl_mix
