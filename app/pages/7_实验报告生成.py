"""
app/pages/7_实验报告生成.py —— 正式教学报告生成模块

自动读取最近一次虚拟实验记录，或手动选择样本与场景，生成 Markdown/HTML 教学报告。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.components.teaching_ai_widget import render_teaching_ai_widget
from app.utils.app_config import EXTENDED_SAFETY_NOTICE
from app.utils.data_loader import load_gas_data, load_virtual_scenarios
from app.utils.lfl_calculator import (
    calculate_flammable_fraction,
    calculate_lfl_mix,
    load_lfl_constants,
    normalize_flammable_gases,
)
from app.utils.report_context import collect_report_context
from app.utils.report_sections import generate_formal_report, generate_formal_report_html
from app.utils.report_docx import generate_docx
from app.utils.learning_trace import record_operation
from app.utils.risk_model import (
    VENTILATION_FACTOR_MAP,
    calculate_risk_ratio,
    classify_risk_level,
    estimate_space_concentration,
)
from app.utils.ui_components import (
    render_info_card,
    render_kpi_grid,
    render_page_header,
    render_risk_badge,
    render_section_title,
    render_warning_banner,
)
from app.utils.ui_theme import apply_global_style, render_global_footer
from app.utils.scoring import calculate_final_score


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

apply_global_style()


@st.cache_data
def _load_assets() -> tuple[pd.DataFrame, dict[str, float], pd.DataFrame, list[str]]:
    """加载报告页所需数据。"""
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


@st.cache_data
def _get_formal_report_markdown(report_ctx: dict) -> str:
    """按需生成正式报告 Markdown，避免普通页面加载反复生成大文本。"""

    return generate_formal_report(report_ctx)


@st.cache_data
def _get_formal_report_html(markdown: str, title: str) -> str:
    """仅在用户明确要求 HTML 下载时转换。"""

    return generate_formal_report_html(markdown, title=title)


@st.cache_data
def _get_formal_report_docx(report_ctx: dict) -> bytes:
    """仅在用户明确要求 Word 下载时生成 docx bytes。"""

    return generate_docx(report_ctx)


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


def _scene_label(row: pd.Series) -> str:
    """构造场景标签。"""
    scenario_id = str(row.get("scenario_id", "未知场景"))
    if "·" in scenario_id:
        return scenario_id
    return (
        f"{scenario_id} · {float(row.get('room_volume_m3', 0.0)):.1f}立方米 · "
        f"{_ventilation_display(row.get('ventilation', 'normal'))}"
    )


def _ventilation_display(label: object) -> str:
    """返回通风条件中文展示。"""
    text = str(label)
    return {"none": "通风不良", "poor": "通风不良", "normal": "通风良好", "good": "通风良好"}.get(text.lower(), text)


def _ventilation_factor(label: object) -> float:
    """将通风标签转换为通风因子。"""
    if not isinstance(label, str):
        return 1.0
    return VENTILATION_FACTOR_MAP.get(label.strip().lower(), 1.0)


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
    """提取可燃组分。"""
    return {gas: value for gas, value in all_composition.items() if gas in lfl_dict}


def _soc_value(row: pd.Series) -> str:
    """读取 SOC 字段。"""
    for col in ["SOC_pct", "soc", "SOC"]:
        if col in row.index and pd.notna(row.get(col)):
            return f"{row[col]}%"
    return "未记录"


def _optional_row_value(row: pd.Series, candidates: list[str]) -> str:
    """读取可选字段，缺失时返回空字符串。"""
    for col in candidates:
        if col in row.index and pd.notna(row.get(col)):
            value = str(row[col]).strip()
            if value:
                return value
    return ""


def _build_report_inputs(
    selected_row: pd.Series,
    sample_label: str,
    scene_row: pd.Series,
    scene_label: str,
    total_gas_l: float,
    lfl_dict: dict[str, float],
) -> tuple[dict, dict, dict]:
    """构造 generate_report 入参。"""
    all_composition = _extract_all_composition(selected_row)
    flammable_composition = _extract_flammable_composition(all_composition, lfl_dict)
    flammable_fraction = calculate_flammable_fraction(flammable_composition, lfl_dict)
    normalized = normalize_flammable_gases(flammable_composition, lfl_dict)
    lfl_mix = calculate_lfl_mix(flammable_composition, lfl_dict)
    space_volume = float(scene_row["room_volume_m3"])
    vent_factor = _ventilation_factor(scene_row.get("ventilation", "normal"))
    space_conc = estimate_space_concentration(total_gas_l, space_volume, vent_factor)
    risk_ratio = calculate_risk_ratio(space_conc, lfl_mix)
    risk_info = classify_risk_level(risk_ratio)

    experiment_params = {
        "experiment_name": "锂离子电池热失控产气组成与混合气体可燃性评价虚拟实验",
        "scene_info": {
            "scene_label": scene_label,
            **scene_row.to_dict(),
        },
        "total_gas_l": total_gas_l,
        "ventilation_factor": vent_factor,
    }
    literature_data = {
        "sample_info": {
            "sample_label": sample_label,
            "source": selected_row.get("source", "未记录"),
            "soc": _soc_value(selected_row),
            "notes": selected_row.get("notes", "未记录"),
            "DOI": _optional_row_value(selected_row, ["DOI", "doi"]),
            "reference": _optional_row_value(selected_row, ["reference", "citation", "文献来源"]),
            "reliability_level": _optional_row_value(selected_row, ["reliability_level", "data_status", "数据状态"]),
        },
        "gas_composition": all_composition,
        "flammable_composition": flammable_composition,
        "flammable_fraction": flammable_fraction,
    }
    calculation_results = {
        "normalized": normalized,
        "lfl_constants": lfl_dict,
        "lfl_mix": lfl_mix,
        "space_concentration": space_conc,
        "risk_ratio": risk_ratio,
        "risk_info": risk_info,
    }
    return experiment_params, literature_data, calculation_results


def _fmt(value: object, digits: int = 2) -> str:
    """格式化结果显示。"""
    if value is None:
        return "无法计算"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


gas_df, lfl_dict, scenes_df, load_errors = _load_assets()

render_page_header(
    title="实验报告生成：正式教学报告模块",
    description=(
        "将文献样本、虚拟场景参数、气体组成、LFL_mix、空间浓度、风险比值和模型局限性"
        "整理为结构化 Markdown/HTML 教学报告。"
    ),
    tags=["报告预览", "Markdown 下载", "HTML 下载", "教学提交"],
)
render_warning_banner(EXTENDED_SAFETY_NOTICE)

if load_errors:
    for error in load_errors:
        st.error(error)
    st.stop()
if gas_df.empty or not lfl_dict or scenes_df.empty:
    st.warning("缺少必要数据，无法生成报告。")
    st.stop()

sample_labels = [_sample_label(idx, row) for idx, (_, row) in enumerate(gas_df.iterrows())]
scene_labels = [_scene_label(row) for _, row in scenes_df.iterrows()]

if st.query_params.get("capture") == "completed-report":
    st.session_state["virtual_experiment_last"] = {
        "sample_index": 0,
        "sample_label": sample_labels[0],
        "scene_index": 0,
        "scene_label": scene_labels[0],
        "total_gas_l": 200.0,
    }
    st.session_state["interactive_experiment_last"] = {
        "experiment_state": {
            "selected_soc": 100,
            "battery_loaded": True,
            "arc_door_closed": True,
            "leak_test_passed": True,
            "replacement_count": 3,
            "sampling_started": True,
            "gas_bag_connected": True,
            "gas_bag_filled": True,
            "gc_started": True,
            "gc_finished": True,
            "ms_finished": True,
            "computer_result_ready": True,
            "gas_volume_calculated": True,
            "lel_calculated": True,
            "current_state": "report_generated",
            "score": 100,
            "error_count": 0,
            "operation_logs": [
                {"time": "00:00:01", "action": "open_sampling_valve", "level": "info", "message": "采样阀已打开，采样管路高亮。"},
                {"time": "00:00:02", "action": "finish_gc", "level": "info", "message": "GC-MS 分析完成，色谱峰、质谱识别和电脑组分结果可查看。"},
            ],
        },
        "score_summary": {"final_score": 100, "grade": "优秀", "error_count": 0, "completion_pct": 100.0, "deductions": []},
        "active_dataset": {"dataset_name": "teaching_demo", "label": "教学演示数据"},
    }

last_record = st.session_state.get("virtual_experiment_last")
interactive_record = st.session_state.get("interactive_experiment_last")

with st.container(border=True):
    st.markdown("**报告数据来源**")
    if last_record:
        st.success(f"已读取最近一次虚拟实验记录：{last_record.get('sample_label', '样本记录已保存')}")
    else:
        st.info("未读取到虚拟实验页保存记录，报告将使用默认样本和 S01 场景生成教学预览。")
    if interactive_record:
        st.success("已读取二维交互实验台记录，报告将写入流程、评分、采样、GC-MS 与同步反应机理。")
    else:
        st.info("二维交互实验台流程尚未完成，相关板块会给出自然的后续执行提示。")

selected_idx = min(int(last_record.get("sample_index", 0)), len(gas_df) - 1) if last_record else 0
selected_scene_idx = min(int(last_record.get("scene_index", 0)), len(scenes_df) - 1) if last_record else 0
total_gas_l = float(last_record.get("total_gas_l", 10.0)) if last_record else 10.0

preview_col, collapse_col = st.columns([1, 1])
with preview_col:
    if st.button("生成报告预览", type="primary", width="stretch"):
        st.session_state["show_formal_report_preview"] = True
        st.session_state.pop("formal_report_html_bytes", None)
        st.session_state.pop("formal_report_docx_bytes", None)
        record_operation(
            page_name="实验报告生成",
            action_type="report",
            action_name="generate_report_preview",
            experiment_state=(interactive_record or {}).get("experiment_state", {}),
            ok=True,
        )
with collapse_col:
    if st.button("收起报告预览", width="stretch"):
        st.session_state["show_formal_report_preview"] = False

selected_row = gas_df.iloc[selected_idx]
scene_row = scenes_df.iloc[selected_scene_idx]

try:
    experiment_params, literature_data, calculation_results = _build_report_inputs(
        selected_row=selected_row,
        sample_label=sample_labels[selected_idx],
        scene_row=scene_row,
        scene_label=scene_labels[selected_scene_idx],
        total_gas_l=float(total_gas_l),
        lfl_dict=lfl_dict,
    )
except Exception as exc:
    st.error(f"报告计算失败：{exc}")
    st.stop()

if interactive_record:
    experiment_state = interactive_record.get("experiment_state", {})
    experiment_params["interactive_state"] = experiment_state
    experiment_params["gas_volume_status"] = interactive_record.get("gas_volume", {})
    experiment_params["active_dataset"] = interactive_record.get("active_dataset", {})
    experiment_params["score_summary"] = interactive_record.get(
        "score_summary",
        calculate_final_score(experiment_state) if isinstance(experiment_state, dict) else {},
    )
    if interactive_record.get("lel_result"):
        lel_result = interactive_record["lel_result"]
        calculation_results.update(
            {
                "normalized": lel_result.get("normalized", calculation_results.get("normalized", {})),
                "lfl_constants": lel_result.get("lfl_constants", calculation_results.get("lfl_constants", {})),
                "lfl_mix": lel_result.get("lfl_mix"),
                "space_concentration": lel_result.get("space_concentration"),
                "risk_ratio": lel_result.get("risk_ratio"),
                "risk_info": lel_result.get("risk_info", calculation_results.get("risk_info")),
            }
        )

report_ctx = collect_report_context(
    experiment_params=experiment_params,
    literature_data=literature_data,
    calculation_results=calculation_results,
)

if st.session_state.get("show_formal_report_preview", False):
    formal_md = _get_formal_report_markdown(report_ctx)
    st.session_state["formal_report_last"] = {"ctx": report_ctx, "markdown": formal_md}
    render_section_title("正式报告预览（十大板块）", "以下为按照双实验逻辑生成的正式报告。")
    with st.container(border=True):
        st.markdown(formal_md)

    render_section_title("报告下载", "下载内容已包含安全边界声明、计算过程、结果解释和模型局限性。")
    download_col1, download_col2, download_col3 = st.columns(3)
    with download_col1:
        record_operation(
            page_name="实验报告生成",
            action_type="report",
            action_name="download_markdown_ready",
            experiment_state=(interactive_record or {}).get("experiment_state", {}),
            ok=True,
        )
        st.download_button(
            "下载 Markdown 报告 (.md)",
            data=formal_md.encode("utf-8"),
            file_name="锂电池热失控产气虚拟实验报告.md",
            mime="text/markdown",
            width="stretch",
        )
    with download_col2:
        if st.button("生成 Word 下载文件", width="stretch"):
            try:
                st.session_state["formal_report_docx_bytes"] = _get_formal_report_docx(report_ctx)
                record_operation(
                    page_name="实验报告生成",
                    action_type="report",
                    action_name="download_docx_ready",
                    experiment_state=(interactive_record or {}).get("experiment_state", {}),
                    ok=True,
                )
            except Exception as exc:
                record_operation(
                    page_name="实验报告生成",
                    action_type="report",
                    action_name="download_docx_failed",
                    experiment_state=(interactive_record or {}).get("experiment_state", {}),
                    ok=False,
                    error_category="docx生成失败",
                )
                st.error(f"docx 生成失败：{exc}")
        docx_bytes = st.session_state.get("formal_report_docx_bytes")
        if docx_bytes:
            st.download_button(
                "下载 Word 报告 (.docx)",
                data=docx_bytes,
                file_name=f"锂电池热失控产气虚拟实验报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
                width="stretch",
            )
    with download_col3:
        if st.button("生成 HTML 下载文件", width="stretch"):
            formal_html = _get_formal_report_html(
                formal_md,
                str(report_ctx.get("report_title", "虚拟实验教学报告")),
            )
            st.session_state["formal_report_html_bytes"] = formal_html.encode("utf-8")
            record_operation(
                page_name="实验报告生成",
                action_type="report",
                action_name="download_html_ready",
                experiment_state=(interactive_record or {}).get("experiment_state", {}),
                ok=True,
            )
        html_bytes = st.session_state.get("formal_report_html_bytes")
        if html_bytes:
            st.download_button(
                "下载 HTML 报告 (.html)",
                data=html_bytes,
                file_name="锂电池热失控产气虚拟实验报告.html",
                mime="text/html",
                width="stretch",
            )

render_teaching_ai_widget(
    page_name="实验报告生成",
    experiment_state=(interactive_record or {}).get("experiment_state", {}),
    assessment=(interactive_record or {}).get("assessment_summary", {}),
    key_prefix="report_page",
)

render_info_card(
    "报告使用说明",
    "报告为虚拟仿真实验教学文档，适合课堂提交、课程项目归档和软件登记材料整理。"
    "报告中的所有风险评价均为教学评价，不得改写为真实事故预测或工程防爆设计结论。",
    accent="#e69500",
)

render_global_footer()
