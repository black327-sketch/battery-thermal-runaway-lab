from pathlib import Path

from app.utils.app_config import FLOW_STEPS, PAGE_MODULES


def test_page_modules_follow_required_sidebar_order():
    assert [module["name"] for module in PAGE_MODULES] == [
        "实验导学",
        "文献数据导入",
        "文献数据库",
        "虚拟实验",
        "二维交互实验台",
        "可燃极限计算",
        "实验报告生成",
    ]


def test_page_module_paths_exist():
    for module in PAGE_MODULES:
        assert Path("app", module["path"]).exists(), module["path"]


def test_flow_steps_put_arc_after_atmosphere_replacement():
    assert FLOW_STEPS.index("实验一：热失控产气成分探究实验") < FLOW_STEPS.index("样品准备与 SOC 设置")
    assert FLOW_STEPS.index("抽真空与氮气置换") < FLOW_STEPS.index("ARC 热失控触发与监测")
    assert FLOW_STEPS.index("ARC 热失控触发与监测") < FLOW_STEPS.index("采样与 GC-MS 分析")
    assert FLOW_STEPS.index("采样与 GC-MS 分析") < FLOW_STEPS.index("实验二：热失控可燃极限实验测法")
    assert FLOW_STEPS.index("虚拟场景选择") < FLOW_STEPS.index("LFL_mix 计算与风险比值 R")
