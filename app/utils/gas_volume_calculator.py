"""产气量计算占位模块。

当前项目尚未接入可核验的文献产气量公式，因此默认不输出正式结果。
"""

from __future__ import annotations


def calculate_gas_volume_from_params(params: dict) -> dict:
    """根据参数计算产气量；缺少文献公式时返回待补充状态。"""
    formula = (params or {}).get("literature_formula")
    if not formula:
        return {
            "status": "pending_user_input",
            "message": "待补充文献产气量计算公式和参数",
            "result": None,
        }
    return {
        "status": "pending_user_input",
        "message": "已检测到公式字段，但当前版本未启用正式文献计算。",
        "result": None,
    }
