"""
app/pages/3_文献数据库.py —— 归一化样本数据资产管理与可视化看板

展示归一化产气组成样本，支持筛选、搜索、样本详情、Plotly 可视化和 CSV 下载。
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.utils.app_config import EXTENDED_SAFETY_NOTICE, FLAMMABLE_GASES, GAS_DISPLAY_NAMES
from app.utils.asset_utils import render_asset_image
from app.utils.chart_utils import plot_gas_composition_bar, plot_gas_composition_donut
from app.utils.dataset_manager import get_validated_status
from app.utils.data_loader import (
    load_arc_key_points_template,
    load_battery_sample_template,
    load_data_source_registry,
    load_gas_data,
    load_gas_volume_formula_template,
    load_gc_composition_template,
    load_lel_constants_reference_template,
    load_lfl_constants_data,
    load_literature_metadata_template,
    filter_literature_samples,
)
from app.utils.data_quality import summarize_data_quality, validate_literature_samples
from app.utils.ui_components import (
    render_info_card,
    render_kpi_grid,
    render_page_header,
    render_section_title,
    render_warning_banner,
)
from app.utils.ui_theme import apply_global_style, render_global_footer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

apply_global_style()


@st.cache_data
def _load_assets() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame], list[str]]:
    """加载文献数据和 LFL 常数表。"""
    errors: list[str] = []
    gas_df = pd.DataFrame()
    lfl_df = pd.DataFrame()
    source_assets: dict[str, pd.DataFrame] = {}
    try:
        gas_df = load_gas_data(DATA_DIR / "normalized_gas_data.csv")
    except Exception as exc:
        errors.append(f"产气数据加载失败：{exc}")
    try:
        lfl_df = load_lfl_constants_data(DATA_DIR / "gas_lfl_constants.csv")
    except Exception as exc:
        errors.append(f"LFL 常数加载失败：{exc}")
    template_loaders = {
        "数据源登记表": (load_data_source_registry, DATA_DIR / "experiment" / "data_source_registry.csv"),
        "文献元数据模板": (load_literature_metadata_template, DATA_DIR / "experiment" / "literature_metadata_template.csv"),
        "电池样品模板": (load_battery_sample_template, DATA_DIR / "experiment" / "battery_sample_template.csv"),
        "ARC 关键节点模板": (load_arc_key_points_template, DATA_DIR / "experiment" / "arc_key_points_template.csv"),
        "GC 组分模板": (load_gc_composition_template, DATA_DIR / "experiment" / "gc_composition_template.csv"),
        "产气量公式模板": (load_gas_volume_formula_template, DATA_DIR / "experiment" / "gas_volume_formula_template.csv"),
        "LFL 常数来源模板": (load_lel_constants_reference_template, DATA_DIR / "experiment" / "lel_constants_reference_template.csv"),
    }
    for name, (loader, path) in template_loaders.items():
        try:
            source_assets[name] = loader(path)
        except Exception as exc:
            errors.append(f"{name}加载失败：{exc}")
            source_assets[name] = pd.DataFrame()
    return gas_df, lfl_df, source_assets, errors


def _resolve_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """大小写不敏感地查找候选字段。"""
    cols = {col.lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in cols:
            return cols[candidate.lower()]
    return None


def _gas_columns(df: pd.DataFrame) -> list[str]:
    """提取气体组成字段，排除 SOC_pct。"""
    return [c for c in df.columns if c.endswith("_pct") and c != "SOC_pct"]


def _row_label(idx: int, row: pd.Series) -> str:
    """构造样本下拉标签。"""
    label = str(row.get("source", f"样本 {idx + 1}"))
    for col in ["SOC_pct", "soc", "SOC"]:
        if col in row.index and pd.notna(row.get(col)):
            label += f" · SOC={row[col]}%"
            break
    if "notes" in row.index and pd.notna(row.get("notes")):
        label += f" · {row['notes']}"
    return label


def _extract_all_gas_composition(row: pd.Series, gas_cols: list[str]) -> dict[str, float]:
    """从样本行中提取全部有效气体组成。"""
    composition: dict[str, float] = {}
    for col in gas_cols:
        gas = col.replace("_pct", "")
        try:
            value = float(row[col])
        except (TypeError, ValueError):
            continue
        if pd.isna(value) or value < 0:
            continue
        composition[gas] = value
    return composition


def _download_csv(df: pd.DataFrame) -> bytes:
    """生成 UTF-8 BOM CSV 下载内容，便于 Excel 打开中文。"""
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


gas_df, lfl_df, source_assets, load_errors = _load_assets()

render_page_header(
    title="文献数据库：归一化样本数据与来源标注",
    description=(
        "对当前 CSV 中的归一化产气组成样本进行筛选、搜索、查看和可视化展示；"
        "示例数据和待补充来源数据不会被表述为真实文献原始数据。"
    ),
    tags=["数据资产", "来源标注", "气体组成", "CSV 下载"],
)

render_warning_banner(EXTENDED_SAFETY_NOTICE)
render_warning_banner(
    "当前平台中的部分数据为教学演示数据、教学插值数据或待补充可核验文献来源的数据，"
    "不能作为真实文献原始数据使用。",
    title="文献接入状态提示",
)

if load_errors:
    for error in load_errors:
        st.error(error)
    st.stop()

if gas_df.empty:
    st.warning("产气数据为空，无法继续。")
    st.stop()

gas_cols = _gas_columns(gas_df)
lfl_combustible = set(FLAMMABLE_GASES)
if not lfl_df.empty and {"gas_formula", "is_combustible"}.issubset(lfl_df.columns):
    lfl_combustible = set(
        lfl_df.loc[
            lfl_df["is_combustible"].astype(str).str.lower().eq("true"),
            "gas_formula",
        ].astype(str)
    )

render_section_title("数据资产概览", "当前页面不改变 CSV 字段含义，仅做教学数据看板展示。")
registry_df = source_assets.get("数据源登记表", pd.DataFrame())
registry_count = len(registry_df) if not registry_df.empty else 0
pending_count = (
    int(registry_df["source_type"].astype(str).eq("pending_user_input").sum())
    if not registry_df.empty and "source_type" in registry_df.columns
    else 0
)
render_kpi_grid(
    [
        {"label": "样本总数", "value": len(gas_df), "unit": "条", "help": "normalized_gas_data.csv"},
        {"label": "字段数量", "value": len(gas_df.columns), "unit": "列", "help": "含来源、SOC、气体组成和备注"},
        {"label": "气体组成字段", "value": len(gas_cols), "unit": "列", "help": "以 _pct 结尾且非 SOC"},
        {"label": "可燃组分字段", "value": len([g for g in gas_cols if g.replace('_pct', '') in lfl_combustible]), "unit": "类", "help": "由 LFL 常数表识别"},
        {"label": "登记数据文件", "value": registry_count, "unit": "个", "help": "data_source_registry.csv 覆盖的文件数量"},
        {"label": "待补充来源", "value": pending_count, "unit": "项", "help": "source_type=pending_user_input"},
    ],
    columns=6,
)

render_section_title("当前数据源总览", "用于区分文献数据、教学插值、教学模拟和待补充来源。")
if registry_df.empty:
    st.info("未读取到数据源登记表。")
else:
    st.dataframe(registry_df, width="stretch", hide_index=True)
    st.caption("source_type 仅允许 literature / teaching_interpolation / teaching_simulation / pending_user_input。")

render_section_title("已校验数据状态", "检查 data/experiment/validated 是否具备二维实验台所需关键数据。")
validated_status = get_validated_status()
st.dataframe(validated_status, width="stretch", hide_index=True)
missing_validated = validated_status[validated_status["状态"].eq("待补充")]["数据项"].tolist()
if missing_validated:
    st.warning("已校验文献数据集尚不完整，缺失：" + "，".join(missing_validated))
else:
    st.success("已校验文献数据关键文件齐全，可在二维实验台选择使用。")

render_section_title("文献数据接入模板", "后续录入论文数据时优先使用这些模板，避免字段漂移。")
template_tabs = st.tabs(["文献元数据", "电池样品", "ARC 关键节点", "GC 组分", "产气量公式", "LFL 常数来源", "待补充项"])
for tab, key in zip(
    template_tabs[:6],
    ["文献元数据模板", "电池样品模板", "ARC 关键节点模板", "GC 组分模板", "产气量公式模板", "LFL 常数来源模板"],
):
    with tab:
        df = source_assets.get(key, pd.DataFrame())
        st.dataframe(df, width="stretch", hide_index=True)
        st.caption("空值或 pending_user_input 表示等待用户补充；不得用推断值补写 DOI、页码、表号或图号。")
with template_tabs[6]:
    st.markdown(
        """
- 归一化产气组成样本的可核验文献来源、DOI、数据位置和归一化方法。
- ARC 关键温度点、完整曲线和压力曲线的可核验来源。
- GC 组分、GC 峰和检测器信息的页码、表号或图号。
- 产气量公式、参数、单位和适用条件。
- LFL / UFL 常数的标准、手册或数据库来源。
"""
    )

render_section_title("筛选面板", "支持按样本、材料体系、SOC、触发方式和关键字进行组合筛选；缺失字段会自动降级处理。")
with st.container(border=True):
    c1, c2, c3, c4 = st.columns([1.2, 1.1, 1.1, 1.4])
    with c1:
        cathode_col = _resolve_column(gas_df, ["cathode", "cathode_type", "正极体系"])
        cathode_disabled = cathode_col is None and "source" not in gas_df.columns
        cathode_input = st.text_input(
            "材料体系",
            value="",
            placeholder="如 NCM111、NCM523、LFP",
            disabled=cathode_disabled,
        )
        if cathode_disabled:
            st.caption("未找到材料字段或 source 字段")
    with c2:
        soc_col = _resolve_column(gas_df, ["SOC_pct", "soc", "SOC"])
        soc_options = ["全部"]
        if soc_col:
            soc_options += [
                str(v).replace(".0", "")
                for v in sorted(pd.to_numeric(gas_df[soc_col], errors="coerce").dropna().unique())
            ]
        selected_soc = st.selectbox("SOC (%)", soc_options)
        soc_input = None if selected_soc == "全部" else selected_soc
    with c3:
        trigger_col = _resolve_column(gas_df, ["trigger_method", "trigger", "触发方式", "notes"])
        trigger_disabled = trigger_col is None
        trigger_input = st.text_input(
            "触发方式关键词",
            value="",
            placeholder="如 过充、过热",
            disabled=trigger_disabled,
        )
        if trigger_disabled:
            st.caption("未找到触发方式或备注字段")
    with c4:
        keyword = st.text_input(
            "全文关键字搜索",
            value="",
            placeholder="搜索 source、notes 或任意字段",
        )

filter_kwargs: dict[str, str] = {}
if cathode_input.strip():
    filter_kwargs["cathode"] = cathode_input.strip()
if soc_input:
    filter_kwargs["soc"] = soc_input
if trigger_input.strip():
    filter_kwargs["trigger_method"] = trigger_input.strip()

try:
    filtered_df = filter_literature_samples(gas_df, **filter_kwargs) if filter_kwargs else gas_df.copy()
except ValueError as exc:
    st.warning(f"筛选条件无法应用：{exc}")
    filtered_df = gas_df.copy()

if keyword.strip():
    text_blob = filtered_df.astype(str).agg(" ".join, axis=1)
    filtered_df = filtered_df[text_blob.str.contains(keyword.strip(), case=False, na=False)]

render_section_title("筛选结果", f"当前共 {len(filtered_df)} 条数据，原始数据共 {len(gas_df)} 条。")
if filtered_df.empty:
    st.info("当前筛选条件下没有匹配数据，请调整筛选条件。")
else:
    display_mode = st.radio("字段显示", ["核心字段", "全部字段"], horizontal=True)
    if display_mode == "核心字段":
        core_cols = [c for c in ["source", "SOC_pct", "notes"] if c in filtered_df.columns] + gas_cols
        display_df = filtered_df[[c for c in core_cols if c in filtered_df.columns]]
    else:
        display_df = filtered_df
    st.dataframe(display_df, width="stretch", hide_index=True)
    st.download_button(
        "下载当前筛选结果 CSV",
        data=_download_csv(display_df),
        file_name="filtered_literature_gas_data.csv",
        mime="text/csv",
        width="stretch",
    )

with st.expander("数据质量检查", expanded=False):
    st.caption("该检查仅用于提示数据整理状态，不影响页面浏览和教学演示。")
    quality_issues = validate_literature_samples(filtered_df)
    quality_summary = summarize_data_quality(quality_issues)
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        st.metric("当前筛选结果", f"{len(filtered_df)} 条")
    with q2:
        st.metric("字段数量", f"{len(filtered_df.columns)} 列")
    with q3:
        st.metric("质量提示", quality_summary["total_issues"])
    with q4:
        source_columns = [col for col in ["source", "DOI", "reference", "reliability_level"] if col in filtered_df.columns]
        if source_columns and not filtered_df.empty:
            filled_cells = 0
            total_cells = len(filtered_df) * len(source_columns)
            for col in source_columns:
                filled_cells += int((filtered_df[col].notna() & ~filtered_df[col].astype(str).str.strip().eq("")).sum())
            completeness = filled_cells / total_cells if total_cells else 0
            st.metric("来源字段完整率", f"{completeness:.0%}")
        else:
            st.metric("来源字段完整率", "待补充")

    if not any(col in filtered_df.columns for col in ["DOI", "reference", "reliability_level"]):
        st.info("当前数据源字段仍待补充，不影响教学演示；正式整理数据时需补齐 DOI、reference 或 reliability_level 等来源信息。")

    if quality_issues:
        issue_df = pd.DataFrame(quality_issues)
        st.dataframe(issue_df, width="stretch", hide_index=True)
    else:
        st.success("当前筛选结果未发现基础字段和数值范围问题。")

render_section_title("样本详情", "选择单个样本查看基本信息、组成检查和 Plotly 交互图表。")
if filtered_df.empty:
    st.info("无可查看样本。")
else:
    indexed_rows = list(filtered_df.iterrows())
    selected_pos = st.selectbox(
        "选择样本",
        options=range(len(indexed_rows)),
        format_func=lambda pos: _row_label(pos, indexed_rows[pos][1]),
    )
    _, selected_row = indexed_rows[selected_pos]
    composition = _extract_all_gas_composition(selected_row, gas_cols)
    total_pct = sum(composition.values())

    c_info, c_check = st.columns([2, 1])
    with c_info:
        info_rows = []
        for label, col in [("数据来源", "source"), ("SOC", "SOC_pct"), ("备注", "notes")]:
            if col in selected_row.index and pd.notna(selected_row.get(col)):
                value = f"{selected_row[col]}%" if label == "SOC" else selected_row[col]
                info_rows.append([label, value])
        st.dataframe(pd.DataFrame(info_rows, columns=["字段", "值"]), width="stretch", hide_index=True)
    with c_check:
        if abs(total_pct - 100.0) <= 2.0:
            st.success(f"组成总和检查：{total_pct:.1f}%（接近 100%）")
        elif total_pct > 0:
            st.warning(f"组成总和检查：{total_pct:.1f}%（请注意归一化差异）")
        else:
            st.info("组成总和检查：无有效气体组成")

    if composition:
        table_rows = []
        for gas, value in composition.items():
            category = "可燃组分" if gas in lfl_combustible else "不可燃/其他"
            table_rows.append(
                {
                    "气体": GAS_DISPLAY_NAMES.get(gas, gas),
                    "分子式": gas,
                    "体积百分比 (% vol)": round(value, 3),
                    "类别": category,
                }
            )
        st.dataframe(pd.DataFrame(table_rows), width="stretch", hide_index=True)

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.plotly_chart(
                plot_gas_composition_bar(
                    composition,
                    flammable_gases=lfl_combustible,
                    title="样本气体组成柱状图",
                ),
                width="stretch",
            )
        with chart_col2:
            st.plotly_chart(
                plot_gas_composition_donut(
                    composition,
                    flammable_gases=lfl_combustible,
                    title="样本气体组成环形图",
                ),
                width="stretch",
            )
    else:
        st.info("未提取到有效气体组成数据。")

render_section_title("数据说明", "用于教学和展示的严谨说明。")
source_cols = st.columns(2)
with source_cols[0]:
    render_asset_image(
        "assets/mechanism/05_hydrogen_generation_pathway.png",
        "H₂ 生成路径示意，仅用于解释气体组分来源，不替代数据表。",
        "H₂ 组分来源提示",
    )
with source_cols[1]:
    render_asset_image(
        "assets/mechanism/06_co_co2_generation_pathway.png",
        "CO / CO₂ 生成路径示意，仅用于解释气体组分来源，不替代数据表。",
        "CO / CO₂ 组分来源提示",
    )
render_info_card(
    "数据来源说明",
    "本页展示的数据来自项目 CSV 文件中的归一化样本、教学演示数据或待补充可核验文献来源的数据。"
    "页面不编造 DOI、作者、实验条件或真实测试结论；后续如补充文献信息，应以原始文献和数据登记表为准。",
)
render_info_card(
    "使用边界",
    "不同文献中的电池规格、SOC、触发方式、检测方法和归一化方式可能存在差异。"
    "本页用于化学实验教学中的数据对比和模型输入，不用于真实事故预测或工程设计。",
    accent="#e69500",
)

render_global_footer()
