"""实验导学页面：双实验流程基线。"""

from __future__ import annotations

import streamlit as st

from app.utils.app_config import EXTENDED_SAFETY_NOTICE, FLOW_STEPS
from app.utils.ui_components import render_info_card, render_page_header, render_section_title, render_stepper, render_warning_banner
from app.utils.ui_theme import apply_global_style, render_global_footer


st.set_page_config(page_title="实验导学", page_icon="🧭", layout="wide")
apply_global_style()

render_page_header(
    title="实验导学：从产气成分探究到可燃极限测法",
    description=(
        "本页是全站学习路径基线。学生先完成实验一，理解热失控阶段、产气机理、采样和 GC-MS 组分分析；"
        "再进入实验二，根据组分结果估算 LFL_mix、空间浓度 C 和风险比值 R = C / LFL_mix。"
    ),
    tags=["双实验流程", "实验一产气成分", "实验二可燃极限", "GC-MS", "LFL_mix"],
)
render_warning_banner(EXTENDED_SAFETY_NOTICE)

render_section_title("为什么分成两个实验部分", "产气成分是可燃极限估算的输入，两个实验前后承接。")
col1, col2 = st.columns(2)
with col1:
    render_info_card(
        "实验一：锂离子电池热失控产气成分探究实验",
        "认识热失控阶段与产气机理，通过虚拟 ARC / 防爆舱完成产气采集，并使用气相色谱仪 / 质谱仪完成 H₂、CO、CO₂、CH₄、C₂H₄、C₂H₆ 等典型组分的教学分析。",
        accent="var(--app-cyan)",
    )
with col2:
    render_info_card(
        "实验二：锂离子电池热失控可燃极限实验测法",
        "读取实验一的产气组分，选择虚拟实验舱体积和通风状态，计算混合气体可燃下限 LFL_mix、空间浓度 C 和风险比值 R = C / LFL_mix，完成可燃风险评价和报告。",
        accent="var(--app-orange)",
    )

render_section_title("推荐学习顺序", "页面之间按同一条实验主线组织，避免各模块割裂。")
render_stepper(FLOW_STEPS)

render_section_title("关键流程解释", "每一步的顺序服务于数据质量、组分识别和教学估算。")
g1, g2, g3 = st.columns(3)
with g1:
    render_info_card(
        "先装样与密封",
        "SOC 是实验一的重要对比参数。装样和密封用于建立虚拟采样系统边界，帮助学生理解气体采集与数据质量之间的关系。",
    )
    render_info_card(
        "再抽真空与氮气置换",
        "抽真空与氮气置换用于说明初始气氛控制。页面只呈现虚拟仿真教学逻辑，不提供真实危险操作步骤。",
    )
with g2:
    render_info_card(
        "再进行 ARC 热失控触发与监测",
        "ARC 画布展示温度、压力、电压和 DAQ 数据采集仪状态，帮助学生把热失控阶段与产气机理对应起来。",
        accent="var(--app-green)",
    )
    render_info_card(
        "为什么需要 GC-MS 分析",
        "气相色谱仪用于分离混合气体，质谱仪用于教学识别组分，电脑端汇总组分结果，为 LFL_mix 计算提供输入。",
        accent="var(--app-green)",
    )
with g3:
    render_info_card(
        "为什么计算 LFL_mix",
        "不同可燃组分的可燃下限不同。将 H₂、CO、CH₄、C₂H₄、C₂H₆ 等可燃组分归一化后，可用 Le Chatelier 混合规则进行教学估算。",
        accent="var(--app-red)",
    )
    render_info_card(
        "为什么比较体积和通风",
        "同等产气量下，小型实验舱空间浓度 C 更高；通风不良时滞留比例更高。四个虚拟场景用于比较体积和通风对 R 的影响。",
        accent="var(--app-red)",
    )

render_section_title("四个虚拟场景", "默认教学演示体现小空间 + 通风不良风险最高，大空间 + 通风良好风险最低。")
st.table(
    [
        {"场景": "S01 小型实验舱 · 10.0立方米 · 通风不良", "教学含义": "空间小且滞留比例高，空间浓度 C 和 R 较高"},
        {"场景": "S02 小型实验舱 · 10.0立方米 · 通风良好", "教学含义": "空间仍较小，但通风稀释降低 R"},
        {"场景": "S03 大型实验舱 · 50.0立方米 · 通风不良", "教学含义": "体积增大降低 C，但通风不良仍会保留一定风险"},
        {"场景": "S04 大型实验舱 · 50.0立方米 · 通风良好", "教学含义": "体积和通风共同降低 C 和 R"},
    ]
)

render_section_title("学习产出", "完成全流程后，报告会汇总两个实验部分。")
st.markdown(
    """
- 能说明热失控阶段、产气机理和典型气体来源。
- 能解释 GC-MS 分析如何得到产气组分。
- 能根据组分结果计算 LFL_mix、空间浓度 C 和风险比值 R = C / LFL_mix。
- 能在报告中区分虚拟仿真教学估算与真实安全判断边界。
"""
)

render_global_footer()
