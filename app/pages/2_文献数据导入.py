"""文献数据导入与校验页面。"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.utils.data_loader import EXPERIMENT_TEMPLATE_COLUMNS
from app.utils.literature_importer import (
    TYPE_TO_TEMPLATE,
    VALIDATORS,
    build_import_summary,
    load_uploaded_csv,
)
from app.utils.ui_components import (
    render_info_card,
    render_kpi_grid,
    render_page_header,
    render_section_title,
    render_warning_banner,
)
from app.utils.ui_theme import apply_global_style, render_global_footer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = PROJECT_ROOT / "data" / "experiment"
VALIDATED_DIR = EXP_DIR / "validated"

st.set_page_config(page_title="文献数据导入与校验", page_icon="📄", layout="wide")
apply_global_style()


DATA_TYPE_OPTIONS = {
    "literature_metadata": "文献元数据",
    "battery_sample": "电池样品",
    "arc_key_points": "ARC 关键节点",
    "arc_curve": "ARC 曲线",
    "pressure_curve": "压力曲线",
    "gc_composition": "GC 组分",
    "gc_peaks": "GC 色谱峰",
    "gas_volume_formula": "产气量公式",
    "lel_constants_reference": "LFL / UFL 常数来源",
}


def _template_path(data_type: str) -> Path:
    return EXP_DIR / TYPE_TO_TEMPLATE[data_type]


def _validated_path(data_type: str) -> Path:
    return VALIDATED_DIR / f"{data_type}_validated.csv"


def _download_bytes(df: pd.DataFrame) -> bytes:
    return ("\ufeff" + df.to_csv(index=False)).encode("utf-8")


render_page_header(
    title="文献数据导入与校验",
    description="上传论文整理后的 CSV，先做字段、source_type、文献定位和待补充状态校验，再决定是否保存为已校验数据。",
    tags=["CSV 导入", "模板校验", "来源标注", "已校验数据集"],
)
render_warning_banner(
    "上传数据不会自动覆盖模板，也不会自动升级为 literature。只有通过校验并明确保存后，才写入 data/experiment/validated/。",
    title="导入安全边界",
)

left, right = st.columns([0.95, 1.55], gap="large")
with left:
    render_section_title("数据类型选择", "选择上传 CSV 对应的模板类型。")
    selected_type = st.selectbox(
        "数据类型",
        options=list(DATA_TYPE_OPTIONS.keys()),
        format_func=lambda key: DATA_TYPE_OPTIONS[key],
    )
    template_file = TYPE_TO_TEMPLATE[selected_type]
    template_path = _template_path(selected_type)
    template_df = pd.read_csv(template_path) if template_path.exists() else pd.DataFrame(columns=EXPERIMENT_TEMPLATE_COLUMNS[template_file])

    st.write(f"模板文件：`data/experiment/{template_file}`")
    st.download_button(
        "下载空模板 CSV",
        data=_download_bytes(pd.DataFrame(columns=EXPERIMENT_TEMPLATE_COLUMNS[template_file])),
        file_name=template_file,
        mime="text/csv",
        width="stretch",
    )

    uploaded = st.file_uploader("上传已填写 CSV", type=["csv"])
    use_template_demo = st.checkbox("使用当前模板文件进行校验预览", value=False)

with right:
    render_section_title("当前模板字段说明", "字段缺失会被列为错误，空值不会自动补写为文献数据。")
    field_df = pd.DataFrame({"字段": EXPERIMENT_TEMPLATE_COLUMNS[template_file]})
    st.dataframe(field_df, width="stretch", hide_index=True)

if uploaded is not None:
    upload_df = load_uploaded_csv(uploaded)
elif use_template_demo:
    upload_df = template_df.copy()
else:
    upload_df = pd.DataFrame()

render_section_title("上传数据预览", "仅预览和校验，不自动保存。")
if upload_df.empty:
    st.info("尚未上传数据，或上传文件为空。")
else:
    st.dataframe(upload_df.head(100), width="stretch", hide_index=True)

validator = VALIDATORS[selected_type]
result = validator(upload_df)
summary_df = build_import_summary({selected_type: result})

render_section_title("校验结果", "valid=True 只表示字段与来源规则通过，不代表数据内容已经被科学核验。")
render_kpi_grid(
    [
        {"label": "是否通过", "value": "通过" if result["valid"] else "未通过", "help": "存在 errors 时不能保存为已校验数据"},
        {"label": "行数", "value": result["row_count"], "help": "上传 CSV 数据行数"},
        {"label": "字段数", "value": result["field_count"], "help": "上传 CSV 字段数"},
        {"label": "错误数", "value": len(result["errors"]), "help": "必须修复"},
        {"label": "警告数", "value": len(result["warnings"]), "help": "建议核对"},
    ],
    columns=5,
)
st.dataframe(summary_df, width="stretch", hide_index=True)

err_col, warn_col = st.columns(2)
with err_col:
    render_section_title("错误列表", "错误未修复前不能保存为已校验数据。")
    if result["errors"]:
        for item in result["errors"]:
            st.error(item)
    else:
        st.success("未发现阻断性错误。")
with warn_col:
    render_section_title("警告列表", "警告不一定阻断保存，但需要人工核对。")
    if result["warnings"]:
        for item in result["warnings"]:
            st.warning(item)
    else:
        st.info("暂无警告。")

render_section_title("数据来源类型统计", "用于检查是否混入未声明来源的数据。")
if result["source_type_counts"]:
    st.dataframe(
        pd.DataFrame(
            [{"source_type": key, "count": value} for key, value in result["source_type_counts"].items()]
        ),
        width="stretch",
        hide_index=True,
    )
else:
    st.info("当前数据类型无 source_type 字段或上传为空。")

can_save = result["valid"] and not upload_df.empty
render_section_title("保存为已校验数据", "保存前必须明确确认；不会修改原始模板。")
st.write("是否可用于正式文献数据：", "可以进入 validated 数据集候选" if can_save else "不可以，需先修复错误或上传非空数据")
confirm = st.checkbox("我确认该 CSV 已按模板整理，并接受系统校验结果。")
if st.button("保存为已校验数据", type="primary", disabled=not (can_save and confirm), width="stretch"):
    VALIDATED_DIR.mkdir(parents=True, exist_ok=True)
    target = _validated_path(selected_type)
    upload_df.to_csv(target, index=False, encoding="utf-8")
    st.success(f"已保存：{target.relative_to(PROJECT_ROOT)}")

report_text = "\n".join(
    [
        f"数据类型: {selected_type}",
        f"valid: {result['valid']}",
        f"row_count: {result['row_count']}",
        f"field_count: {result['field_count']}",
        f"errors: {result['errors']}",
        f"warnings: {result['warnings']}",
        f"source_type_counts: {result['source_type_counts']}",
    ]
)
st.download_button(
    "下载校验报告",
    data=report_text.encode("utf-8"),
    file_name=f"{selected_type}_validation_report.txt",
    mime="text/plain",
    width="stretch",
)

render_info_card(
    "使用说明",
    "保存后的 CSV 位于 data/experiment/validated/。随后可在二维实验台选择“已校验文献数据”。"
    "如果关键文件缺失，系统会显示数据集不完整，不会自动回退并伪装为文献数据。",
    accent="var(--app-cyan)",
)

render_global_footer()
