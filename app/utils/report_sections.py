"""Generate the formal ten-section teaching report."""

from __future__ import annotations

import html
import re
from typing import Any, Mapping

from app.utils.reaction_mechanism import collect_completed_mechanisms


INCOMPLETE_HINT = "该步骤尚未执行，完成二维交互实验后将自动写入报告。"
SAFETY_TEXT = "本平台结果仅用于虚拟仿真教学和实验创新设计展示，不作为真实工程安全判断或消防应急处置依据。"


def _fmt(value: object, digits: int = 2, none_text: str = "无法计算") -> str:
    if value is None:
        return none_text
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _table(headers: list[str], rows: list[list[object]]) -> str:
    if not rows:
        rows = [["-" for _ in headers]]
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
            *["| " + " | ".join(str(item) for item in row) + " |" for row in rows],
        ]
    )


def _label_state(state: str) -> str:
    labels = {
        "sample_preparation": "样品准备",
        "battery_loaded": "电池已装入",
        "leak_test": "气密性检测",
        "vacuuming": "抽真空",
        "nitrogen_filling": "氮气置换",
        "atmosphere_replacement": "气氛置换",
        "arc_ready": "ARC 就绪",
        "arc_heating": "ARC 升温",
        "thermal_runaway": "热失控演示",
        "cooling": "冷却",
        "gas_sampling": "气体采样",
        "gc_analysis": "GC-MS 分析",
        "gas_volume_calculation": "产气量记录",
        "lel_risk_evaluation": "可燃风险评价",
        "report_generated": "报告生成",
    }
    return labels.get(str(state), str(state))


def _value(value: object, fallback: str = INCOMPLETE_HINT) -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def generate_formal_report(ctx: dict[str, Any]) -> str:
    """Generate a Markdown report with the required ten sections."""

    interactive = ctx.get("interactive_state", {}) if isinstance(ctx.get("interactive_state"), Mapping) else {}
    score = ctx.get("score_summary", {}) if isinstance(ctx.get("score_summary"), Mapping) else {}
    gas_rows = [[gas, _fmt(value, 3), "是" if gas in ctx.get("flammable_composition", {}) else "否"] for gas, value in (ctx.get("gas_composition") or {}).items()]
    normalized_rows = []
    for gas, y_i in (ctx.get("normalized") or {}).items():
        lfl_i = (ctx.get("lfl_constants") or {}).get(gas)
        contribution = None
        try:
            contribution = float(y_i) / float(lfl_i)
        except (TypeError, ValueError, ZeroDivisionError):
            pass
        normalized_rows.append([gas, _fmt(y_i, 6), _fmt(lfl_i, 3), _fmt(contribution, 6)])

    mechanisms = collect_completed_mechanisms(interactive)
    mechanism_parts = []
    for stage in mechanisms:
        equations = stage.get("equations", []) or []
        eq_text = "当前阶段以装置操作和数据采集为主，未触发新的化学反应方程式。"
        if equations:
            eq_text = "<br>".join(str(item.get("reaction", "")) for item in equations[:3] if isinstance(item, Mapping))
        gases = "、".join(str(g) for g in stage.get("main_gases", []) or []) or "以流程或数据处理为主"
        mechanism_parts.append([stage.get("title", "当前阶段"), stage.get("mechanism_summary", ""), eq_text, gases])

    operation_rows = [
        ["SOC", _value(interactive.get("selected_soc"), "该步骤尚未执行，完成 SOC 选择后将自动写入报告。")],
        ["气密性检测", "通过" if interactive.get("leak_test_passed") else INCOMPLETE_HINT],
        ["氮气置换次数", str(interactive.get("replacement_count", 0))],
        ["采样阀", "已打开并记录" if interactive.get("sampling_started") else INCOMPLETE_HINT],
        ["采样状态", "已完成" if interactive.get("gas_bag_filled") else INCOMPLETE_HINT],
        ["GC-MS 分析", "已完成，电脑组分结果可查看" if interactive.get("gc_finished") else INCOMPLETE_HINT],
        ["当前阶段", _label_state(interactive.get("current_state", "sample_preparation")) if interactive else INCOMPLETE_HINT],
    ]
    score_rows = [
        ["得分", str(score.get("final_score", interactive.get("score", INCOMPLETE_HINT)))],
        ["等级", str(score.get("grade", "优秀" if interactive.get("score", 100) >= 90 else "待评价"))],
        ["扣分原因", "无扣分" if not score.get("deductions") else "；".join(str(item.get("reason", "")) for item in score.get("deductions", [])[:5])],
    ]

    return f"""# 锂离子电池热失控产气数智化虚拟实验报告

## 1. 实验基本信息

{_table(['项目', '内容'], [
    ['报告编号', ctx.get('report_id', '-')],
    ['生成时间', ctx.get('generated_at', '-')],
    ['平台主题', '锂离子电池热失控产气数智化虚拟实验平台'],
    ['样本', ctx.get('sample_label', '-')],
    ['虚拟场景', ctx.get('scene_label', '-')],
    ['安全边界', SAFETY_TEXT],
])}

## 2. 实验背景与目的

本报告围绕两个实验部分展开：实验一是锂离子电池热失控产气成分探究实验，目标是建立“热失控阶段、产气机理、气体组分、数据分析”的学习路径；实验二是锂离子电池热失控可燃极限实验测法，目标是基于实验一组分结果完成 LFL_mix、空间浓度 C 和风险比值 R = C / LFL_mix 的虚拟仿真教学估算。

## 3. 实验一：热失控产气成分探究实验

实验一通过教学 ARC / 通用热失控模式展示 SOC 设置、装样、密封、气氛准备、热失控阶段观察、采样袋收集、气相色谱仪分离、质谱仪识别和电脑组分结果显示。典型关注气体包括 H₂、CO、CO₂、CH₄、C₂H₄、C₂H₆。

{_table(['气体', '体积百分比 (% vol)', '参与 LFL_mix'], gas_rows)}

## 4. 实验二：热失控可燃极限实验测法

实验二读取实验一得到的产气组分，选择小型/大型实验舱及通风状态，计算混合气体可燃下限 LFL_mix、空间浓度 C 和风险比值 R = C / LFL_mix。该评价仅用于虚拟仿真教学。

{_table(['指标', '结果'], [
    ['混合气体可燃下限 LFL_mix', f"{_fmt(ctx.get('lfl_mix'), 2)} % vol"],
    ['空间浓度 C', f"{_fmt(ctx.get('space_concentration'), 4)} % vol"],
    ['风险比值 R = C / LFL_mix', _fmt(ctx.get('risk_ratio'), 4)],
    ['可燃风险评价', ctx.get('risk_level', '无法评价')],
])}

## 5. 数智化平台与实验装置

平台模块按主页面和实验导学的学习顺序组织：文献数据导入、文献数据库、虚拟实验、二维交互实验台、可燃极限计算、实验报告生成。二维画布中 ARC 实验舱、采样袋、气相色谱仪、质谱仪、电脑和 DAQ 数据采集仪形成产气采集和 GC-MS 组分分析链路。

## 6. 实验流程与关键操作记录

{_table(['步骤', '状态'], operation_rows)}

## 7. 实验数据与气体组分结果

可燃组分按 LFL 常数表识别并归一化，CO₂、N₂、HF 及无有效 LFL 数据的组分不参与 Le Chatelier 求和。

{_table(['气体', '归一化 y_i', 'LFL_i (% vol)', 'y_i / LFL_i'], normalized_rows)}

## 8. 同步反应机理与阶段方程式

以下内容读取自 `docs/阶段方程式.json`，并随二维交互状态同步写入报告。

{_table(['阶段', '主要机理说明', '主要反应方程式', '主要产气物种'], mechanism_parts)}

## 9. LFL_mix 计算与可燃风险评价

Le Chatelier 混合规则：

$$
LFL_{{mix}} = \\frac{{1}}{{\\sum_i \\frac{{y_i}}{{LFL_i}}}}
$$

虚拟场景中，10.0 m³ 小型实验舱在同等产气量下空间浓度更高；50.0 m³ 大型实验舱空间浓度更低。通风不良表示气体滞留比例较高，通风良好表示稀释和排出效果更明显。风险比值 R = C / LFL_mix 仅用于课堂讨论。

{_table(['场景参数', '值'], [
    ['场景', ctx.get('scene_label', '-')],
    ['虚拟空间体积', f"{ctx.get('scene_volume', '-')} m³"],
    ['通风条件', ctx.get('scene_ventilation', '-')],
    ['虚拟总产气量', f"{_fmt(ctx.get('total_gas_l'), 3)} L"],
    ['评价解释', ctx.get('risk_description', '-')],
])}

## 10. 实验结论、评分与反思

本次虚拟仿真教学估算得到 LFL_mix = {_fmt(ctx.get('lfl_mix'), 2)} % vol，空间浓度 C = {_fmt(ctx.get('space_concentration'), 4)} % vol，风险比值 R = {_fmt(ctx.get('risk_ratio'), 4)}，可燃风险评价为 {ctx.get('risk_level', '无法评价')}。

{_table(['评分项', '结果'], score_rows)}

反思要点：比较 SOC、空间体积、通风状态和可燃组分比例对 R 的影响；报告结论必须保持虚拟仿真教学边界，不扩展为真实工程安全判断或消防应急处置依据。"""


def generate_formal_report_html(markdown_text: str, *, title: str = "虚拟实验教学报告") -> str:
    """Convert the shared Markdown report into a standalone HTML document."""

    lines = markdown_text.splitlines()
    html_lines: list[str] = []
    in_ul = False
    in_table = False
    table_row_count = 0

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False

    def close_table() -> None:
        nonlocal in_table, table_row_count
        if in_table:
            html_lines.append("</tbody></table>")
            in_table = False
            table_row_count = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            close_ul()
            close_table()
            continue
        if stripped.startswith("|"):
            close_ul()
            cells = [html.escape(cell.strip()) for cell in stripped.strip("|").split("|")]
            if all(set(cell) <= {"-", ":"} for cell in cells):
                continue
            if not in_table:
                html_lines.append("<table><tbody>")
                in_table = True
                table_row_count = 0
            tag = "th" if table_row_count == 0 else "td"
            html_lines.append("<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>")
            table_row_count += 1
            continue
        close_table()
        if stripped.startswith("# "):
            close_ul()
            html_lines.append(f"<h1>{html.escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            close_ul()
            html_lines.append(f"<h2>{html.escape(stripped[3:])}</h2>")
        elif stripped.startswith("- "):
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li>{html.escape(stripped[2:])}</li>")
        elif re.match(r"^\d+\. ", stripped):
            close_ul()
            html_lines.append(f"<p>{html.escape(stripped)}</p>")
        else:
            close_ul()
            html_lines.append(f"<p>{html.escape(stripped)}</p>")
    close_ul()
    close_table()

    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{safe_title}</title>
<style>
body {{ font-family: "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif; max-width: 980px; margin: 32px auto; padding: 0 24px; line-height: 1.75; color: #213547; }}
h1, h2 {{ color: #0b3a63; }}
table {{ width: 100%; border-collapse: collapse; margin: 14px 0 22px; font-size: 14px; }}
th, td {{ border: 1px solid #d9e4ef; padding: 8px 10px; vertical-align: top; }}
th {{ background: #f4f8fb; color: #0b3a63; }}
p {{ margin: 0 0 12px; }}
ul {{ margin: 0 0 14px 22px; }}
</style>
</head>
<body>
{chr(10).join(html_lines)}
</body>
</html>"""
