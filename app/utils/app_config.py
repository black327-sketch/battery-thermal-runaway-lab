"""
app/utils/app_config.py —— 平台基础配置

集中管理软件名称、版本、安全声明、页面模块和风险颜色等配置。
"""

from __future__ import annotations


APP_NAME = "锂离子电池热失控产气数智化虚拟实验平台"
APP_SHORT_NAME = "数智化化学虚拟实验平台"
APP_VERSION = "v0.2.1"
APP_SUBTITLE = "面向化学实验教学与虚拟仿真的二维交互式产气收集、GC 分析和可燃风险评价平台"
APP_POSITIONING = (
    "基于归一化产气组成样本、Le Chatelier 混合规则和轻量虚拟空间模型，"
    "用于新能源材料安全化学方向的实验导学、数据分析、虚拟仿真和教学报告生成。"
)
AUTHOR_ORG = ""

SAFETY_NOTICE = "本平台结果仅用于虚拟仿真教学和实验创新设计展示，不作为真实工程安全判断或消防应急处置依据。"

EXTENDED_SAFETY_NOTICE = (
    "本平台结果仅用于虚拟仿真教学和实验创新设计展示，不作为真实工程安全判断或消防应急处置依据。"
    "页面内容不提供真实热失控、过充、针刺、加热、点火、制备可燃气体或混合可燃气体流程。"
)

FEATURE_TAGS = ["虚拟仿真", "文献数据", "LFL 计算", "教学评价", "报告生成"]

PAGE_MODULES = [
    {
        "name": "实验导学",
        "icon": "01",
        "path": "pages/1_实验导学.py",
        "description": "课程目标、概念速览、模型说明、风险等级和使用路径",
    },
    {
        "name": "文献数据导入",
        "icon": "02",
        "path": "pages/2_文献数据导入.py",
        "description": "上传论文整理 CSV，校验字段、来源类型和文献定位信息",
    },
    {
        "name": "文献数据库",
        "icon": "03",
        "path": "pages/3_文献数据库.py",
        "description": "归一化产气组成样本浏览、来源标注、筛选、可视化和下载",
    },
    {
        "name": "虚拟实验",
        "icon": "04",
        "path": "pages/4_虚拟实验.py",
        "description": "样本和场景选择、LFL_mix、空间浓度与风险比值计算",
    },
    {
        "name": "二维交互实验台",
        "icon": "05",
        "path": "pages/5_二维交互实验台.py",
        "description": "ARC、20 L 罐、氮气瓶、真空泵、集气袋和 GC 的二维交互流程",
    },
    {
        "name": "可燃极限计算",
        "icon": "06",
        "path": "pages/6_可燃极限计算.py",
        "description": "Le Chatelier 混合规则分步解释和贡献分析",
    },
    {
        "name": "实验报告生成",
        "icon": "07",
        "path": "pages/7_实验报告生成.py",
        "description": "生成结构化 Markdown 教学报告并支持下载",
    },
]

RISK_LEVEL_CONFIG = {
    "低风险": {
        "color": "#2e7d32",
        "bg": "#e8f5e9",
        "border": "#a5d6a7",
        "range": "R < 0.25",
    },
    "关注": {
        "color": "#b7791f",
        "bg": "#fff8db",
        "border": "#f6d365",
        "range": "0.25 ≤ R < 0.50",
    },
    "较高风险": {
        "color": "#c05621",
        "bg": "#fff3e0",
        "border": "#f6ad55",
        "range": "0.50 ≤ R < 1.00",
    },
    "高风险": {
        "color": "#c62828",
        "bg": "#ffebee",
        "border": "#ef9a9a",
        "range": "R ≥ 1.00",
    },
    "无法评价": {
        "color": "#546e7a",
        "bg": "#eceff1",
        "border": "#b0bec5",
        "range": "缺少有效 LFL",
    },
}

FLAMMABLE_GASES = ["H2", "CO", "CH4", "C2H4", "C2H6"]
NON_FLAMMABLE_GASES = ["CO2", "HF", "N2", "others"]

GAS_DISPLAY_NAMES = {
    "H2": "H₂",
    "CO": "CO",
    "CO2": "CO₂",
    "CH4": "CH₄",
    "C2H4": "C₂H₄",
    "C2H6": "C₂H₆",
    "HF": "HF",
    "N2": "N₂",
    "others": "其他",
}

FLOW_STEPS = [
    "认识热失控与产气风险",
    "实验一：热失控产气成分探究实验",
    "样品准备与 SOC 设置",
    "密封实验系统准备",
    "抽真空与氮气置换",
    "ARC 热失控触发与监测",
    "采样与 GC-MS 分析",
    "实验二：热失控可燃极限实验测法",
    "虚拟场景选择",
    "LFL_mix 计算与风险比值 R",
    "评分与报告生成",
]
