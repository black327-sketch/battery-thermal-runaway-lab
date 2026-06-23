"""
app/pages/4_虚拟实验.py —— 虚拟实验操作台

将文献样本、虚拟场景、总产气量、LFL_mix、空间浓度、R 值和教学风险等级串联。
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.utils.app_config import EXTENDED_SAFETY_NOTICE, FLAMMABLE_GASES
from app.utils.chart_utils import (
    plot_gas_composition_bar,
    plot_risk_gauge,
    plot_scenario_comparison,
)
from app.utils.data_loader import load_gas_data, load_virtual_scenarios
from app.utils.lfl_calculator import calculate_lfl_mix, load_lfl_constants
from app.utils.risk_model import (
    VENTILATION_FACTOR_MAP,
    calculate_risk_ratio,
    classify_risk_level,
    estimate_space_concentration,
)
from app.utils.ui_components import (
    render_info_card,
    render_kpi_grid,
    render_model_notice,
    render_page_header,
    render_risk_badge,
    render_section_title,
    render_warning_banner,
)
from app.utils.ui_theme import apply_global_style, render_global_footer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

apply_global_style()


@st.cache_data
def _load_assets() -> tuple[pd.DataFrame, dict[str, float], pd.DataFrame, list[str]]:
    """加载虚拟实验所需数据。"""
    errors: list[str] = []
    gas_df = pd.DataFrame()
    lfl_dict: dict[str, float] = {}
    scenes_df = pd.DataFrame()
    try:
        gas_df = load_gas_data(DATA_DIR / "normalized_gas_data.csv")
    except Exception as exc:
        errors.append(f"产气数据加载失败：{exc}")
    try:
        lfl_dict = load_lfl_constants(DATA_DIR / "gas_lfl_constants.csv")
    except Exception as exc:
        errors.append(f"LFL 常数加载失败：{exc}")
    try:
        scenes_df = load_virtual_scenarios(DATA_DIR / "virtual_scenarios.csv")
    except Exception as exc:
        errors.append(f"虚拟场景加载失败：{exc}")
    return gas_df, lfl_dict, scenes_df, errors


def _build_sample_label(idx: int, row: pd.Series) -> str:
    """构造样本选择标签。"""
    label = str(row.get("source", f"样本 {idx + 1}"))
    for col in ["SOC_pct", "soc", "SOC"]:
        if col in row.index and pd.notna(row.get(col)):
            label += f" · SOC={row[col]}%"
            break
    if "notes" in row.index and pd.notna(row.get("notes")):
        label += f" · {row['notes']}"
    return label


def _extract_gas_composition(row: pd.Series, formulas: list[str]) -> dict[str, float]:
    """从样本中提取参与 LFL 计算的可燃气体组成。"""
    composition: dict[str, float] = {}
    col_lower_map = {c.lower(): c for c in row.index}
    for formula in formulas:
        for candidate in [f"{formula}_pct", f"{formula.lower()}_pct", formula, formula.lower()]:
            matched_col = col_lower_map.get(candidate.lower())
            if not matched_col:
                continue
            try:
                value = float(row[matched_col])
            except (TypeError, ValueError):
                continue
            if pd.isna(value) or value < 0:
                continue
            composition[formula] = value
            break
    return composition


def _extract_display_composition(row: pd.Series) -> dict[str, float]:
    """从样本中提取所有气体组成字段。"""
    composition: dict[str, float] = {}
    for col in row.index:
        if not col.endswith("_pct") or col == "SOC_pct":
            continue
        try:
            value = float(row[col])
        except (TypeError, ValueError):
            continue
        if pd.isna(value) or value < 0:
            continue
        composition[col.replace("_pct", "")] = value
    return composition


def _ventilation_factor(label: object) -> float:
    """将场景通风标签转换为稀释因子。"""
    if not isinstance(label, str):
        return 1.0
    return VENTILATION_FACTOR_MAP.get(label.strip().lower(), 1.0)


def _ventilation_display(label: object) -> str:
    """返回通风条件中文展示。"""
    text = str(label)
    return {"none": "通风不良", "poor": "通风不良", "normal": "通风良好", "good": "通风良好"}.get(text.lower(), text)


def _scenario_label(row: pd.Series) -> str:
    """构造场景选择标签。"""
    scenario_id = str(row.get("scenario_id", "未知场景"))
    if "·" in scenario_id:
        return scenario_id
    return f"{scenario_id} · {float(row.get('room_volume_m3', 0.0)):.1f}立方米 · {_ventilation_display(row.get('ventilation', 'good'))}"


def _calculate_result(
    gas_composition: dict[str, float],
    lfl_dict: dict[str, float],
    scene_row: pd.Series,
    total_gas_l: float,
) -> dict[str, object]:
    """执行虚拟实验核心计算，保持底层计算函数不变。"""
    lfl_mix = calculate_lfl_mix(gas_composition, lfl_dict) if gas_composition else None
    space_volume = float(scene_row["room_volume_m3"])
    ventilation = _ventilation_factor(scene_row.get("ventilation", "normal"))
    space_conc = estimate_space_concentration(total_gas_l, space_volume, ventilation)
    risk_ratio = calculate_risk_ratio(space_conc, lfl_mix)
    risk_info = classify_risk_level(risk_ratio)
    return {
        "lfl_mix": lfl_mix,
        "space_concentration": space_conc,
        "risk_ratio": risk_ratio,
        "risk_info": risk_info,
        "space_volume_m3": space_volume,
        "ventilation_factor": ventilation,
    }


gas_df, lfl_dict, scenes_df, load_errors = _load_assets()

render_page_header(
    title="虚拟实验：实验二场景模拟与可燃风险评价",
    description=(
        "承接实验一得到的产气组分，选择四类实验舱体积和通风状态，计算空间浓度 C、"
        "混合气体可燃下限 LFL_mix、风险比值 R = C / LFL_mix 和可燃风险评价结果。"
    ),
    tags=["实验二", "四个虚拟场景", "空间浓度 C", "LFL_mix", "R = C / LFL_mix"],
)
render_warning_banner(EXTENDED_SAFETY_NOTICE)

if load_errors:
    for error in load_errors:
        st.error(error)
    st.stop()
if gas_df.empty or not lfl_dict or scenes_df.empty:
    st.warning("缺少必要数据，无法运行虚拟实验。")
    st.stop()

sample_labels = [_build_sample_label(idx, row) for idx, (_, row) in enumerate(gas_df.iterrows())]
scene_labels = [_scenario_label(row) for _, row in scenes_df.iterrows()]

left, right = st.columns([0.92, 1.55], gap="large")

with left:
    render_section_title("实验参数控制区", "所有输入均为虚拟教学参数。")
    with st.container(border=True):
        selected_idx = st.selectbox(
            "文献样本选择",
            options=range(len(gas_df)),
            format_func=lambda idx: sample_labels[idx],
        )
        selected_scene_idx = st.selectbox(
            "虚拟场景选择（仅四个教学场景）",
            options=range(len(scenes_df)),
            format_func=lambda idx: scene_labels[idx],
        )
        default_total = float(scenes_df.iloc[selected_scene_idx].get("gas_total_vol_pct", 1.0)) * 20.0
        total_gas_l = st.number_input(
            "虚拟总产气量 (L)",
            min_value=0.0,
            max_value=10000.0,
            value=max(1.0, default_total),
            step=1.0,
            help="教学参数，不代表真实电池产气量预测。",
        )
        run_calc = st.button("执行虚拟计算", type="primary", width="stretch")

    selected_row = gas_df.iloc[selected_idx]
    scene_row = scenes_df.iloc[selected_scene_idx]
    gas_composition = _extract_gas_composition(selected_row, list(lfl_dict.keys()))
    display_composition = _extract_display_composition(selected_row)

    render_model_notice(
        "本页不提供真实热失控实验流程。虚拟总产气量、空间体积和通风因子仅用于均匀混合模型演示。",
        title="安全提示",
    )

    render_section_title("样本气体组成", "蓝色表示参与 LFL 计算的可燃组分。")
    st.plotly_chart(
        plot_gas_composition_bar(
            display_composition,
            flammable_gases=set(lfl_dict.keys()),
            title="当前样本气体组成",
        ),
        width="stretch",
    )

with right:
    render_section_title("结果看板与解释区", "执行计算后展示关键指标、仪表盘和教学解释。")

    if "virtual_experiment_last" in st.session_state and not run_calc:
        st.info("当前显示页面参数的即时计算结果；点击“执行虚拟计算”可保存为最近一次实验记录。")

    if not gas_composition:
        st.warning("所选样本未能提取可燃组分，无法计算 LFL_mix。")
        result = _calculate_result({}, lfl_dict, scene_row, total_gas_l)
    else:
        try:
            result = _calculate_result(gas_composition, lfl_dict, scene_row, total_gas_l)
        except Exception as exc:
            st.error(f"计算失败：{exc}")
            st.stop()

    if run_calc:
        st.session_state["virtual_experiment_last"] = {
            "sample_index": int(selected_idx),
            "sample_label": sample_labels[selected_idx],
            "sample_data": selected_row.to_dict(),
            "scene_index": int(selected_scene_idx),
            "scene_label": scene_labels[selected_scene_idx],
            "scene_data": scene_row.to_dict(),
            "total_gas_l": float(total_gas_l),
            "gas_composition": gas_composition,
            "display_composition": display_composition,
            "result": result,
        }
        st.success("已保存本次虚拟实验记录，可在“实验报告生成”页面自动读取。")

    lfl_mix = result["lfl_mix"]
    space_conc = result["space_concentration"]
    risk_ratio = result["risk_ratio"]
    risk_info = result["risk_info"]

    render_kpi_grid(
        [
            {
                "label": "LFL_mix",
                "value": "无法计算" if lfl_mix is None else f"{lfl_mix:.2f}",
                "unit": "" if lfl_mix is None else "% vol",
                "help": "Le Chatelier 混合规则教学估算",
            },
            {
                "label": "空间浓度 C",
                "value": f"{space_conc:.4f}",
                "unit": "% vol",
                "help": "均匀混合假设下的总气体浓度",
            },
            {
                "label": "风险比值 R",
                "value": "—" if risk_ratio is None else f"{risk_ratio:.4f}",
                "help": "R = C / LFL_mix",
            },
            {
                "label": "教学风险等级",
                "value": risk_info["level"],
                "help": "仅用于虚拟仿真教学评价",
            },
        ],
        columns=4,
    )

    render_risk_badge(str(risk_info["level"]))
    st.write("")
    st.plotly_chart(plot_risk_gauge(risk_ratio), width="stretch")

    if lfl_mix is None:
        st.info("该样本缺少有效可燃组分或 LFL 数据，无法计算混合可燃下限。")
    else:
        render_info_card(
            "结果解释",
            f"当前空间浓度 C 为 {space_conc:.4f}% vol，混合气体可燃下限 LFL_mix 为 {lfl_mix:.2f}% vol，"
            f"因此教学风险比值 R = {risk_ratio:.4f}。{risk_info['description']}",
            accent="#00838f",
        )

    render_model_notice(
        "计算采用可燃组分归一化、Le Chatelier 混合规则和虚拟空间均匀混合假设。"
        "未考虑温度、压力、惰性稀释修正、动态产气速率、空间分层和局部积聚。",
        title="模型假设",
    )

render_section_title("四个场景风险排序", "同一样本和总产气量下，小空间与通风不良会提高空间浓度 C 和风险比值 R。")
comparison_rows = []
for _, row in scenes_df.iterrows():
    try:
        scene_result = _calculate_result(gas_composition, lfl_dict, row, total_gas_l)
    except Exception:
        continue
    comparison_rows.append(
        {
            "场景": str(row.get("scenario_id", "未知场景")),
            "空间体积 (m³)": float(row.get("room_volume_m3", 0.0)),
            "通风条件": _ventilation_display(row.get("ventilation", "normal")),
            "LFL_mix (% vol)": scene_result["lfl_mix"],
            "空间浓度 (% vol)": scene_result["space_concentration"],
            "风险比值 R": scene_result["risk_ratio"] if scene_result["risk_ratio"] is not None else 0.0,
            "教学风险等级": scene_result["risk_info"]["level"],
        }
    )
comparison_df = pd.DataFrame(comparison_rows)
if comparison_df.empty:
    st.info("暂无可对比场景。")
else:
    st.plotly_chart(plot_scenario_comparison(comparison_df), width="stretch")
    st.dataframe(
        comparison_df.assign(
            **{
                "LFL_mix (% vol)": comparison_df["LFL_mix (% vol)"].map(
                    lambda v: "无法计算" if pd.isna(v) else f"{v:.2f}"
                ),
                "空间浓度 (% vol)": comparison_df["空间浓度 (% vol)"].map(lambda v: f"{v:.4f}"),
                "风险比值 R": comparison_df["风险比值 R"].map(lambda v: f"{v:.4f}"),
            }
        ),
        width="stretch",
        hide_index=True,
    )

render_section_title("本次虚拟实验记录摘要", "可直接用于报告页默认读取，也可复制到教学记录中。")
summary = (
    f"文献样本：{sample_labels[selected_idx]}\n\n"
    f"虚拟场景：{scene_labels[selected_scene_idx]}\n\n"
    f"虚拟总产气量：{total_gas_l:.1f} L\n\n"
    f"LFL_mix：{'无法计算' if lfl_mix is None else f'{lfl_mix:.2f} % vol'}\n\n"
    f"空间浓度：{space_conc:.4f} % vol\n\n"
    f"风险比值 R：{'—' if risk_ratio is None else f'{risk_ratio:.4f}'}\n\n"
    f"教学风险等级：{risk_info['level']}\n\n"
    f"结果解释：{risk_info['description']}"
)
st.text_area("记录摘要", value=summary, height=220)

render_global_footer()
