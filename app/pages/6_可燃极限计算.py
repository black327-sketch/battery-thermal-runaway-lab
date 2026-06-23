"""
app/pages/6_可燃极限计算.py —— 可解释计算教学页

分步展示 Le Chatelier 混合规则：原始组成、可燃识别、归一化、贡献项和 LFL_mix。
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.utils.app_config import EXTENDED_SAFETY_NOTICE, GAS_DISPLAY_NAMES
from app.utils.asset_utils import render_asset_image
from app.utils.chart_utils import (
    plot_flammable_ratio,
    plot_gas_composition_bar,
    plot_gas_composition_donut,
    plot_lfl_contribution,
)
from app.utils.data_loader import load_gas_data
from app.utils.lfl_calculator import (
    calculate_flammable_fraction,
    calculate_lfl_mix,
    load_lfl_constants,
    normalize_flammable_gases,
)
from app.utils.ui_components import (
    render_info_card,
    render_kpi_grid,
    render_model_notice,
    render_page_header,
    render_result_card,
    render_section_title,
    render_warning_banner,
)
from app.utils.ui_theme import apply_global_style, render_global_footer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

apply_global_style()


@st.cache_data
def _load_assets() -> tuple[pd.DataFrame, dict[str, float], list[str]]:
    """加载计算页所需数据。"""
    errors: list[str] = []
    gas_df = pd.DataFrame()
    lfl_dict: dict[str, float] = {}
    try:
        gas_df = load_gas_data(DATA_DIR / "normalized_gas_data.csv")
    except Exception as exc:
        errors.append(f"产气数据加载失败：{exc}")
    try:
        lfl_dict = load_lfl_constants(DATA_DIR / "gas_lfl_constants.csv")
    except Exception as exc:
        errors.append(f"LFL 常数加载失败：{exc}")
    return gas_df, lfl_dict, errors


def _sample_label(idx: int, row: pd.Series) -> str:
    """构造样本标签。"""
    label = str(row.get("source", f"样本 {idx + 1}"))
    for col in ["SOC_pct", "soc", "SOC"]:
        if col in row.index and pd.notna(row.get(col)):
            label += f" · SOC={row[col]}%"
            break
    if "notes" in row.index and pd.notna(row.get("notes")):
        label += f" · {row['notes']}"
    return label


def _extract_all_composition(row: pd.Series) -> dict[str, float]:
    """提取全部气体组成字段。"""
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


def _extract_flammable_composition(
    all_composition: dict[str, float],
    lfl_dict: dict[str, float],
) -> dict[str, float]:
    """从全部组成中提取可燃组分。"""
    return {gas: value for gas, value in all_composition.items() if gas in lfl_dict}


def _fmt(value: float | None, digits: int = 2) -> str:
    """格式化数值。"""
    if value is None:
        return "无法计算"
    return f"{value:.{digits}f}"


gas_df, lfl_dict, load_errors = _load_assets()

render_page_header(
    title="可燃极限计算：Le Chatelier 可解释教学页",
    description=(
        "以单个文献样本为例，透明展示从原始气体组成到可燃组分识别、归一化、"
        "y_i / LFL_i 贡献和 LFL_mix 结果的完整计算过程。"
    ),
    tags=["Le Chatelier", "可燃组分识别", "归一化", "贡献分析"],
)
render_warning_banner(EXTENDED_SAFETY_NOTICE)

if load_errors:
    for error in load_errors:
        st.error(error)
    st.stop()
if gas_df.empty or not lfl_dict:
    st.warning("缺少必要数据，无法进行计算。")
    st.stop()

render_section_title("计算规则", "LFL_i 使用 % vol 单位；CO₂、HF、N₂ 等非可燃气体不参与求和。")
st.markdown(
    r"""
$$
LFL_{mix} = \frac{1}{\sum_i \frac{y_i}{LFL_i}}
$$
"""
)
render_model_notice(
    "公式中的 y_i 为可燃组分内部归一化体积分数，LFL_i 为纯物质可燃下限（% vol）。"
    "例如 H₂ 的 LFL_i = 4.0，不转换为 0.04。",
    title="单位说明",
)

render_section_title("步骤一：选择文献样本", "选择一个样本后，页面会自动完成分步教学计算。")
labels = [_sample_label(idx, row) for idx, (_, row) in enumerate(gas_df.iterrows())]
selected_idx = st.selectbox(
    "文献样本",
    options=range(len(gas_df)),
    format_func=lambda idx: labels[idx],
)
selected_row = gas_df.iloc[selected_idx]

all_composition = _extract_all_composition(selected_row)
flammable_composition = _extract_flammable_composition(all_composition, lfl_dict)

if not all_composition:
    st.warning("所选样本未提取到有效气体组成。")
    st.stop()

render_section_title("步骤二：展示原始气体组成", "原始组成来自 CSV 字段，不改变字段含义。")
chart_col1, chart_col2 = st.columns([1.3, 1])
with chart_col1:
    st.plotly_chart(
        plot_gas_composition_bar(
            all_composition,
            flammable_gases=set(lfl_dict.keys()),
            title="原始气体组成柱状图",
        ),
        width="stretch",
    )
with chart_col2:
    st.plotly_chart(
        plot_gas_composition_donut(
            all_composition,
            flammable_gases=set(lfl_dict.keys()),
            title="原始气体组成环形图",
        ),
        width="stretch",
    )

render_section_title("步骤三：识别可燃组分", "只有在 LFL 常数表中标记为可燃且有有效 LFL_i 的组分参与求和。")
rows = []
for gas, value in all_composition.items():
    is_flammable = gas in lfl_dict
    lfl_display = f"{lfl_dict[gas]:.3f}" if is_flammable else "—"
    rows.append(
        {
            "气体": GAS_DISPLAY_NAMES.get(gas, gas),
            "分子式": gas,
            "原始体积百分比 (% vol)": f"{value:.3f}",
            "是否参与 LFL 计算": "是" if is_flammable else "否",
            "LFL_i (% vol)": lfl_display,
        }
    )
st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

flammable_fraction = calculate_flammable_fraction(flammable_composition, lfl_dict)
render_kpi_grid(
    [
        {"label": "总气体组成", "value": f"{sum(all_composition.values()):.1f}", "unit": "%", "help": "组成总和检查"},
        {"label": "可燃气体总比例", "value": f"{flammable_fraction:.1f}", "unit": "% vol", "help": "参与 LFL 计算前的原始比例"},
        {"label": "可燃组分数量", "value": len(flammable_composition), "unit": "类", "help": "H₂、CO、CH₄ 等"},
        {"label": "非可燃/其他比例", "value": f"{max(0.0, 100.0 - flammable_fraction):.1f}", "unit": "% vol", "help": "不参与 Le Chatelier 求和"},
    ],
    columns=4,
)
st.plotly_chart(plot_flammable_ratio(flammable_fraction), width="stretch")

if not flammable_composition:
    st.info("该样本未识别出可燃组分，无法进行 LFL_mix 计算。")
    render_global_footer()
    st.stop()

render_section_title("步骤四：归一化可燃组分比例", "将可燃组分内部比例归一化，使 Σy_i = 1。")
normalized = normalize_flammable_gases(flammable_composition, lfl_dict)
norm_rows = []
for gas, y_i in normalized.items():
    lfl_i = lfl_dict[gas]
    norm_rows.append(
        {
            "气体": GAS_DISPLAY_NAMES.get(gas, gas),
            "分子式": gas,
            "原始体积 (%)": round(flammable_composition.get(gas, 0.0), 4),
            "归一化 y_i": round(y_i, 6),
            "LFL_i (% vol)": round(lfl_i, 4),
            "y_i / LFL_i": round(y_i / lfl_i, 6),
        }
    )
norm_df = pd.DataFrame(norm_rows)
st.dataframe(norm_df, width="stretch", hide_index=True)

norm_composition = {gas: y_i * 100 for gas, y_i in normalized.items()}
chart_norm, chart_contrib = st.columns(2)
with chart_norm:
    st.plotly_chart(
        plot_gas_composition_donut(
            norm_composition,
            flammable_gases=set(normalized.keys()),
            title="可燃组分归一化占比",
        ),
        width="stretch",
    )
with chart_contrib:
    st.plotly_chart(plot_lfl_contribution(normalized, lfl_dict), width="stretch")

render_section_title("步骤五：得到 LFL_mix 结果", "贡献项求和后取倒数，得到混合可燃下限教学估算值。")
denominator = sum(y_i / lfl_dict[gas] for gas, y_i in normalized.items())
lfl_mix = calculate_lfl_mix(flammable_composition, lfl_dict)
result_cols = st.columns([1, 1, 1])
with result_cols[0]:
    render_result_card(
        "Σ(y_i / LFL_i)",
        f"{denominator:.5f}",
        "Le Chatelier 求和项，值越大，LFL_mix 越低。",
    )
with result_cols[1]:
    render_result_card(
        "LFL_mix",
        f"{_fmt(lfl_mix)} % vol",
        "教学估算值，不用于真实工程安全判定。",
    )
with result_cols[2]:
    render_asset_image(
        "assets/mechanism/08_lel_risk_evaluation.png",
        "LFL 教学风险解释图，不作为消防应急或工程防爆判据。",
        "可燃风险解释示意",
    )

render_info_card(
    "教学解释",
    f"该样本中可燃气体总比例为 {flammable_fraction:.1f}% vol。"
    f"在可燃组分内部归一化后，根据 Le Chatelier 混合规则得到 LFL_mix = {_fmt(lfl_mix)}% vol。"
    "CO₂、HF、N₂ 和其他非可燃或无 LFL 数据组分不参与求和；实际体系中惰性稀释、温度和压力会影响可燃极限，本版未做定量修正。",
    accent="#00838f",
)

render_section_title("模型局限性", "用于教学解释，不用于真实事故预测、消防应急或工程防爆设计。")
render_model_notice(
    "Le Chatelier 混合规则适用于理想混合的教学估算。当前页面未考虑温度、压力、惰性稀释修正、反应动力学和动态通风条件。",
    title="计算局限",
)
render_model_notice(
    "本页展示的是可燃极限计算过程，不是热失控实验操作流程，也不提供真实气体制备、混合或点燃方法。",
    title="安全边界",
)

render_global_footer()
