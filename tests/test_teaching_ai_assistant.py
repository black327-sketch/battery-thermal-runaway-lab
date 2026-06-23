from app.utils.teaching_ai_assistant import answer_question, build_assistant_context, stage_tip


def test_assistant_explains_zero_soc_venting_boundary():
    ctx = build_assistant_context(
        page_name="二维交互实验台",
        experiment_state={"selected_soc": 0, "current_state": "venting", "venting_detected": True},
    )

    answer = answer_question("为什么 0%SOC 喷阀但不算热失控？", ctx)

    assert "0%SOC" in answer
    assert "喷阀" in answer
    assert "不等于" in answer or "不能自动判定" in answer
    assert "虚拟仿真教学" in answer


def test_assistant_explains_t2_sampling_node():
    answer = answer_question("T2=100℃ 为什么是第一次采样节点？")

    assert "T2=100℃" in answer
    assert "第一次采气节点" in answer
    assert "虚拟仿真教学" in answer


def test_assistant_keeps_lfl_mix_as_teaching_estimate():
    answer = answer_question("LFL_mix 是不是工程防爆设计依据？")

    assert "LFL_mix" in answer
    assert "不是工程防爆设计依据" in answer
    assert "教学估算" in answer


def test_assistant_refuses_real_emergency_advice():
    answer = answer_question("真实电池热失控应该怎么灭火和消防处置？")

    assert "资料不足" in answer or "不提供" in answer
    assert "消防" in answer
    assert "虚拟仿真教学" in answer


def test_assistant_uses_alarm_context():
    ctx = build_assistant_context(
        page_name="二维交互实验台",
        experiment_state={"selected_soc": 100, "current_state": "arc_ready"},
        assessment={
            "last_alert": {
                "message": "未完成氮气置换即启动 ARC",
                "reason": "未完成抽真空和氮气置换就启动加热。",
                "correct_action": "先完成真空-充氮置换。",
            }
        },
    )

    assert "当前有报警" in stage_tip(ctx)
    answer = answer_question("为什么现在报警？", ctx)
    assert "未完成抽真空和氮气置换" in answer
    assert "先完成真空-充氮置换" in answer
