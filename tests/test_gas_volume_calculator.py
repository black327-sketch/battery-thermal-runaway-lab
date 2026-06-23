from app.utils.gas_volume_calculator import calculate_gas_volume_from_params


def test_missing_formula_returns_pending_user_input():
    result = calculate_gas_volume_from_params({})
    assert result["status"] == "pending_user_input"
    assert result["result"] is None
    assert "待补充文献产气量计算公式和参数" in result["message"]


def test_formula_field_still_does_not_create_unverified_result():
    result = calculate_gas_volume_from_params({"literature_formula": "unverified"})
    assert result["status"] == "pending_user_input"
    assert result["result"] is None
    assert "未启用正式文献计算" in result["message"]
