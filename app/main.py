"""Streamlit 多页面应用首页：实验平台总览。"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from app.components.teaching_ai_widget import render_teaching_ai_widget
from app.utils.app_config import (
    APP_NAME,
    APP_POSITIONING,
    APP_SHORT_NAME,
    APP_SUBTITLE,
    APP_VERSION,
    EXTENDED_SAFETY_NOTICE,
    FEATURE_TAGS,
    FLAMMABLE_GASES,
    FLOW_STEPS,
    PAGE_MODULES,
)
from app.utils.asset_utils import render_asset_image
from app.utils.chart_utils import plot_flammable_ratio, plot_gas_composition_bar
from app.utils.data_loader import load_gas_data, load_lfl_constants_data, load_virtual_scenarios
from app.utils.ui_components import (
    render_feature_card,
    render_info_card,
    render_kpi_grid,
    render_page_header,
    render_section_title,
    render_stepper,
    render_warning_banner,
)
from app.utils.ui_theme import apply_global_style, render_global_footer, render_tablet_demo_entry, render_theme_toggle


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


@st.cache_data
def _load_dashboard_assets() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    """加载首页驾驶舱所需数据，返回数据表和错误列表。"""
    errors: list[str] = []
    gas_df = pd.DataFrame()
    lfl_df = pd.DataFrame()
    scenarios_df = pd.DataFrame()

    try:
        gas_df = load_gas_data(DATA_DIR / "normalized_gas_data.csv")
    except Exception as exc:  # pragma: no cover - Streamlit 页面兜底
        errors.append(f"文献数据加载失败：{exc}")
    try:
        lfl_df = load_lfl_constants_data(DATA_DIR / "gas_lfl_constants.csv")
    except Exception as exc:  # pragma: no cover
        errors.append(f"LFL 常数加载失败：{exc}")
    try:
        scenarios_df = load_virtual_scenarios(DATA_DIR / "virtual_scenarios.csv")
    except Exception as exc:  # pragma: no cover
        errors.append(f"虚拟场景加载失败：{exc}")

    return gas_df, lfl_df, scenarios_df, errors


def _extract_average_composition(gas_df: pd.DataFrame) -> dict[str, float]:
    """提取样本平均气体组成，用于首页概览图。"""
    composition: dict[str, float] = {}
    if gas_df.empty:
        return composition
    for col in gas_df.columns:
        if col.endswith("_pct") and col != "SOC_pct":
            values = pd.to_numeric(gas_df[col], errors="coerce").dropna()
            if not values.empty:
                composition[col.replace("_pct", "")] = float(values.mean())
    return composition


def main() -> None:
    """渲染 Streamlit 首页。"""
    st.set_page_config(
        page_title=f"{APP_SHORT_NAME} · {APP_VERSION}",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_global_style()

    gas_df, lfl_df, scenarios_df, errors = _load_dashboard_assets()

    top_left, top_right = st.columns([5, 1])
    with top_right:
        render_theme_toggle("昼夜模式", key="main_theme_toggle")
        render_tablet_demo_entry()

    render_page_header(
        title=APP_NAME,
        description=(
            "本平台以两个实验部分组织学习路径：先完成热失控产气成分探究，再基于组分结果完成"
            "混合气体可燃下限 LFL_mix、空间浓度 C 和风险比值 R = C / LFL_mix 的虚拟仿真教学估算。"
        ),
        eyebrow=f"实验平台总览 · {APP_VERSION}",
        tags=FEATURE_TAGS + ["二维实验台"],
    )

    if errors:
        for error in errors:
            st.warning(error)

    render_warning_banner(EXTENDED_SAFETY_NOTICE)
    render_teaching_ai_widget(page_name="首页", key_prefix="home_page")

    render_section_title("两个实验部分", "全站围绕实验一和实验二的先后承接关系展开。")
    c_intro1, c_intro2, c_intro3 = st.columns(3)
    with c_intro1:
        render_info_card(
            "实验一：产气成分探究",
            "认识热失控阶段与产气机理，通过虚拟 ARC / 防爆舱完成产气采集，使用气相色谱仪 / 质谱仪分析 H₂、CO、CO₂、CH₄、C₂H₄、C₂H₆ 等典型气体。",
            accent="var(--app-primary-light)",
        )
    with c_intro2:
        render_info_card(
            "实验二：可燃极限测法",
            "读取实验一的产气组分，比较 10.0 m³ / 50.0 m³ 实验舱和通风状态对空间浓度 C、LFL_mix 与 R 的影响。",
            accent="var(--app-cyan)",
        )
    with c_intro3:
        render_info_card(
            "安全边界",
            "本平台结果仅用于虚拟仿真教学和实验创新设计展示，不作为真实工程安全判断或消防应急处置依据。",
            accent="var(--app-green)",
        )

    render_section_title("推荐学习路径", "先完成实验一的产气组分分析，再进入实验二的 LFL_mix 与可燃风险评价。")
    render_stepper(FLOW_STEPS)

    render_section_title("数据集状态入口", "平台支持教学演示数据和已校验文献数据两类数据集。")
    ds1, ds2 = st.columns(2)
    with ds1:
        render_info_card(
            "教学演示数据",
            "默认用于课堂演示和功能验证，包含教学模拟、教学插值和待补充来源数据，非文献原始数据。",
            accent="var(--app-orange)",
        )
    with ds2:
        render_info_card(
            "已校验文献数据",
            "请先在“文献数据导入”页面上传并校验论文整理数据，再在二维实验台选择该数据集。",
            accent="var(--app-cyan)",
        )
    st.page_link("pages/2_文献数据导入.py", label="进入文献数据导入与校验", icon="📄")
    st.page_link("pages/5_二维交互实验台.py", label="进入二维交互实验台", icon="🔬")

    render_section_title("设备总览", "二维实验台包含 ARC、20 L 密封罐、氮气瓶、真空泵、采样袋、气相色谱仪、质谱仪、电脑和 DAQ 数据采集仪。")
    c_eq1, c_eq2, c_eq3 = st.columns(3)
    with c_eq1:
        render_asset_image(
            "assets/mechanism/01_thermal_runaway_overview.png",
            "平台机理总览图，仅用于虚拟仿真教学理解。",
            "热失控产气机理总览",
        )
        render_info_card("ARC 加速量热仪", "展示虚拟升温、热失控高亮、温度传感器、加热系统和安全指示状态。")
        render_info_card("20 L 密封气体收集罐", "展示压力表、置换次数、氮气入口、真空出口和采样阀状态。")
    with c_eq2:
        render_info_card("氮气瓶与真空泵", "用于三轮抽真空 / 氮气置换教学流程，压力变化为教学模拟数据。", accent="var(--app-cyan)")
        render_info_card("集气袋采样", "仅允许冷却后连接和采样，集气袋随采样状态膨胀。", accent="var(--app-orange)")
    with c_eq3:
        render_info_card("GC-MS-电脑链路", "采样气体进入气相色谱仪分离，经质谱仪识别后在电脑端显示组分结果。", accent="var(--app-green)")
        render_info_card("可燃风险评价", "复用 LFL 和 risk_model 模块，计算 LFL_mix、空间浓度 C 与风险比值 R = C / LFL_mix。", accent="var(--app-red)")

    # ── 实验装备总览图 ──
    _sumf_dir = PROJECT_ROOT / "assets" / "sumf"
    _sumf_images: list = []
    if _sumf_dir.exists():
        _sumf_images = sorted(
            [p for p in _sumf_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
        )
    if _sumf_images:
        render_section_title(
            "实验装备总览",
            "实验装备总览图用于帮助学生建立虚拟实验流程、真实装置结构与气体分析系统之间的整体对应关系。",
        )
        _sumf_cols = st.columns(min(len(_sumf_images), 2))
        for _idx, _img in enumerate(_sumf_images):
            with _sumf_cols[_idx % len(_sumf_cols)]:
                _label = _img.stem.replace("_", " ")
                try:
                    st.image(str(_img), width="stretch")
                except Exception:
                    st.info(f"图片加载失败：{_img.name}")
                st.caption(_label if _label else "实验装备总览图")
    else:
        pass  # sumf 目录不存在时不显示额外提示，避免页面杂乱

    # ── 真实装置图 ──
    render_section_title(
        "真实装置对照",
        "真实装置图用于帮助学生建立虚拟流程与实验系统之间的对应关系。",
    )
    facility_dir = PROJECT_ROOT / "assets" / "facility"
    if facility_dir.exists():
        facility_images = sorted(
            [p for p in facility_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
        )
        if facility_images:
            _FACILITY_LABELS: dict[str, str] = {
                "arc": "加速量热仪（ARC）实物图",
                "gc": "气相色谱仪（GC）实物图",
            }
            fc1, fc2 = st.columns(2)
            for idx, img_path in enumerate(facility_images):
                stem_lower = img_path.stem.lower()
                label = ""
                for key, title in _FACILITY_LABELS.items():
                    if key in stem_lower:
                        label = title
                        break
                if not label:
                    label = img_path.stem
                col = fc1 if idx % 2 == 0 else fc2
                with col:
                    try:
                        st.image(str(img_path), width="stretch")
                    except Exception:
                        st.info(f"图片加载失败：{img_path.name}")
                    st.caption(label)
        else:
            st.info("assets/facility 目录下未找到图片文件。")
    else:
        st.info("assets/facility 目录不存在，真实装置图待补充。")

    render_section_title("数据资产概览", "基于当前 CSV 数据文件自动统计，便于演示时说明软件数据基础。")

    gas_cols = [c for c in gas_df.columns if c.endswith("_pct") and c != "SOC_pct"] if not gas_df.empty else []
    combustible_count = 0
    if not lfl_df.empty and "is_combustible" in lfl_df.columns:
        combustible_count = int(
            lfl_df["is_combustible"].astype(str).str.lower().eq("true").sum()
        )

    render_kpi_grid(
        [
            {"label": "文献样本数量", "value": len(gas_df), "unit": "条", "help": "当前归一化产气组成样本"},
            {"label": "气体组分数量", "value": len(gas_cols), "unit": "类", "help": "CSV 中可识别的气体组成字段"},
            {"label": "可燃组分数量", "value": combustible_count, "unit": "类", "help": "LFL 常数表中标记为可燃"},
            {"label": "虚拟场景数量", "value": len(scenarios_df), "unit": "个", "help": "用于空间浓度估算的教学场景"},
            {"label": "功能模块数量", "value": len(PAGE_MODULES), "unit": "个", "help": "多页面教学闭环模块"},
        ],
        columns=5,
    )

    avg_composition = _extract_average_composition(gas_df)
    if avg_composition:
        col_chart, col_note = st.columns([2, 1])
        with col_chart:
            st.plotly_chart(
                plot_gas_composition_bar(
                    avg_composition,
                    flammable_gases=set(FLAMMABLE_GASES),
                    title="样本平均气体组成概览",
                ),
                width="stretch",
            )
        with col_note:
            flammable_avg = sum(avg_composition.get(gas, 0.0) for gas in FLAMMABLE_GASES)
            st.plotly_chart(
                plot_flammable_ratio(flammable_avg, title="平均可燃组分占比"),
                width="stretch",
            )

    render_section_title("核心功能模块入口", "左侧导航栏可进入各模块，首页展示模块定位和演示闭环。")
    module_cols = st.columns(7)
    for idx, module in enumerate(PAGE_MODULES):
        with module_cols[idx % 7]:
            render_feature_card(
                index=str(module["icon"]),
                title=str(module["name"]),
                description=str(module["description"]),
            )

    render_section_title("文献数据说明", "模拟、插值和待补充内容必须显式标注。")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_info_card(
            "数据来源分级",
            "平台区分文献数据、教学插值、教学模拟和待补充文献数据；当前示例数据不得表述为真实文献原始数据。",
        )
        render_info_card(
            "安全边界清晰",
            "平台所有页面和报告均声明仅用于虚拟仿真教学，不用于真实事故预测、消防应急或工程防爆设计。",
            accent="#e69500",
        )
    with c2:
        render_info_card(
            "计算过程透明",
            "可燃组分识别、可燃组分归一化、y_i / LFL_i 贡献和 R 值评价均可在页面中查看。",
            accent="#00838f",
        )
        render_info_card(
            "二维交互闭环",
            "电池准备、ARC、20 L 罐、集气袋、GC、可燃风险评价、评分和报告生成串联为完整教学路径。",
            accent="#2e7d32",
        )
    with c3:
        render_info_card(
            "模块化可扩展",
            "公共配置、UI 组件、图表工具和报告生成器已拆分，便于后续补充实验仿真、数据管理和教学评价。",
            accent="#1565c0",
        )
        render_info_card(
            "适合材料整理",
            "界面、模块说明、版本信息和项目文档均围绕软件作品形态组织，便于截图、录屏和材料归档。",
            accent="#6b46c1",
        )

    render_section_title("运行方式", "本项目保持轻量化 Streamlit 多页面结构，无数据库和重型前端框架。")
    st.code(
        "cd digital_and_intelligent_platform2\n"
        "pip install -r requirements.txt\n"
        "streamlit run app/main.py",
        language="bash",
    )

    render_global_footer()


if __name__ == "__main__":
    main()
