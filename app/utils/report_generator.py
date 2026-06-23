"""
app/utils/report_generator.py —— 实验报告自动生成

生成结构化 Markdown 或 HTML 教学报告。报告仅用于虚拟仿真实验教学，
不包含真实危险实验操作步骤。
"""

from __future__ import annotations

import csv
from datetime import datetime
import html
from pathlib import Path
import re
from typing import Mapping

from app.utils.app_config import APP_NAME, APP_VERSION, SAFETY_NOTICE


def _value(mapping: Mapping | None, key: str, default: object = "未记录") -> object:
    """从映射中读取值，空值返回默认值。"""
    if not mapping:
        return default
    value = mapping.get(key, default)
    if value is None or value == "":
        return default
    return value


def _fmt(value: object, digits: int = 2, none_text: str = "无法计算") -> str:
    """格式化报告数值。"""
    if value is None:
        return none_text
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    """生成 Markdown 表格。"""
    if not rows:
        rows = [["—" for _ in headers]]
    header_line = "| " + " | ".join(headers) + " |"
    split_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    row_lines = ["| " + " | ".join(str(item) for item in row) + " |" for row in rows]
    return "\n".join([header_line, split_line] + row_lines)


def _source_value(sample_info: Mapping, keys: list[str]) -> str:
    """读取样本来源相关字段，缺失时返回待补充。"""
    for key in keys:
        value = _value(sample_info, key, "")
        if value:
            return str(value)
    return "待补充"


def _report_id(now: datetime, experiment_params: Mapping | None) -> str:
    """生成报告编号。"""
    explicit_id = _value(experiment_params, "report_id", "")
    if explicit_id:
        return str(explicit_id)
    return f"VEXP-{now.strftime('%Y%m%d-%H%M%S')}"


def _load_registry_rows() -> list[list[object]]:
    """读取数据源登记表，用于报告汇总。"""
    registry_path = Path(__file__).resolve().parents[2] / "data" / "experiment" / "data_source_registry.csv"
    if not registry_path.exists():
        return [["data_source_registry", "未找到", "pending_user_input", "否", "待补充数据源登记表"]]
    rows: list[list[object]] = []
    with registry_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                [
                    row.get("data_file", ""),
                    row.get("data_type", ""),
                    row.get("source_type", ""),
                    "是" if str(row.get("is_literature", "")).lower() == "true" else "否",
                    row.get("notes", ""),
                ]
            )
    return rows or [["data_source_registry", "空表", "pending_user_input", "否", "待补充数据源登记记录"]]


def _load_experiment_csv_rows(file_name: str) -> list[dict[str, str]]:
    """读取 data/experiment 下的 CSV 为字典行。"""
    path = Path(__file__).resolve().parents[2] / "data" / "experiment" / file_name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _build_zeng_2026_section() -> str:
    """生成曾垂辉等 2026 文献装置模式报告段落。"""
    metadata_rows = _load_experiment_csv_rows("literature_zeng_2026_metadata.csv")
    battery_rows = _load_experiment_csv_rows("literature_zeng_2026_battery_sample.csv")
    key_rows = _load_experiment_csv_rows("literature_zeng_2026_arc_key_points.csv")
    gc_rows = _load_experiment_csv_rows("literature_zeng_2026_gc_composition.csv")

    meta = metadata_rows[0] if metadata_rows else {}
    battery = battery_rows[0] if battery_rows else {}
    battery_table = [
        ["实验对象", battery.get("battery_type", "方壳 LFP 电池样品")],
        ["尺寸", battery.get("dimensions_mm", "128.7×148.7×17.7 mm")],
        ["质量", battery.get("mass_g", "628±10 g")],
        ["额定容量", f"{battery.get('nominal_capacity_ah', '22')} Ah"],
        ["额定电压", f"{battery.get('nominal_voltage_v', '3.22')} V"],
        ["标准充电电压", f"{battery.get('standard_charge_voltage_v', '3.65')} V"],
        ["放电截止电压", f"{battery.get('discharge_cutoff_voltage_v', '2.5')} V"],
        ["SOC", "0%、25%、50%、75%、100%"],
    ]
    key_table = [
        [
            row.get("soc_pct", ""),
            row.get("vent_time_s", ""),
            row.get("vent_temperature_c", ""),
            f"{row.get('voltage_drop_start_s', '')}-{row.get('voltage_drop_end_s', '')}",
            row.get("thermal_runaway_time_s", "") or "未热失控",
            row.get("max_heating_rate_c_per_s", "") or "—",
            row.get("max_temperature_c", "") or "—",
            row.get("thermal_runaway_observed", ""),
        ]
        for row in key_rows
    ]
    gc_pending_count = sum(1 for row in gc_rows if row.get("source_type") == "pending_user_input")
    stage_rows = [
        ["第一次采气", "T2=100℃", "表 3 阶段结构已建；具体组分数值待用户提供"],
        ["第二次采气", "安全阀喷阀", "表 3 阶段结构已建；具体组分数值待用户提供"],
        ["第三次采气", "热失控 / 温度峰值", "表 3 阶段结构已建；具体组分数值待用户提供"],
        ["第四次采气", "反应结束 / 压力稳定", "表 3 阶段结构已建；具体组分数值待用户提供"],
    ]

    return f"""
## 16A. 文献装置模式记录

| 项目 | 内容 |
|---|---|
| 实验模式 | 文献装置模式：防爆舱-加热模块产气教学演示 |
| 文献来源 | 曾垂辉等，2026 |
| 题名 | {meta.get('title', '方壳磷酸铁锂锂离子电池热失控不同阶段产热产气机理研究')} |
| DOI | {meta.get('doi', '10.19799/j.cnki.2095-4239.2026.0036')} |
| 数据用途 | 教学平台的数据回放与风险评价演示 |

### 电池样品参数

{_markdown_table(['参数', '数值'], battery_table)}

### 装置组成

防爆舱体、舱门、观察窗、方壳 LFP 电池、加热模块、隔热板、T1/T2/T3 热电偶、电压采集线、压力传感器、舱内压力表、真空接口、氮气接口、采样口、集气袋、GC 气相色谱仪和 DAQ 数据采集仪。

### 采气阶段说明

{_markdown_table(['采气序号', '阶段', '数据状态'], stage_rows)}

### 热失控关键节点表

{_markdown_table(['SOC (%)', '喷阀时间 (s)', '喷阀温度 (℃)', '电压下降时间 (s)', '热失控时间 (s)', '最大温升速率 (℃/s)', '最高温度 (℃)', '是否热失控'], key_table)}

### 阶段性产气表状态

`literature_zeng_2026_gc_composition.csv` 已建立 25%、50%、75%、100% SOC × T2=100℃、喷阀、热失控、反应结束 × H2、CO2、CO、碳氢化合物的占位结构。当前 {gc_pending_count} 条记录仍为 `pending_user_input`，未录入表 3 具体数值，不得表述为文献原始数据。

### 二维教学仿真边界说明

本文献数据仅用于教学平台的数据回放与风险评价演示；平台不用于真实事故预测、消防应急或工程防爆设计。平台模拟实验流程、装置关系、数据回放和风险评价，不等同于三维物理仿真、CFD 仿真或真实热化学反应仿真。
"""


def _risk_level_text(risk_info: Mapping | None, calculation_results: Mapping | None) -> tuple[str, str]:
    """解析风险等级和解释。"""
    risk_info = risk_info or _value(calculation_results, "risk_info", {})
    if not isinstance(risk_info, Mapping):
        risk_info = {}
    level = str(_value(risk_info, "level", _value(calculation_results, "risk_level", "无法评价")))
    description = str(_value(risk_info, "description", _value(calculation_results, "risk_description", "缺少有效风险评价信息。")))
    return level, description


def _build_markdown(
    experiment_params: Mapping | None,
    literature_data: Mapping | None,
    calculation_results: Mapping | None,
    now: datetime,
) -> str:
    """生成 Markdown 报告正文。"""
    experiment_params = experiment_params or {}
    literature_data = literature_data or {}
    calculation_results = calculation_results or {}
    interactive_state = _value(experiment_params, "interactive_state", {})
    if not isinstance(interactive_state, Mapping):
        interactive_state = {}
    gas_volume_status = _value(experiment_params, "gas_volume_status", {})
    if not isinstance(gas_volume_status, Mapping):
        gas_volume_status = {}
    score_summary = _value(experiment_params, "score_summary", {})
    if not isinstance(score_summary, Mapping):
        score_summary = {}
    active_dataset = _value(experiment_params, "active_dataset", {})
    if not isinstance(active_dataset, Mapping):
        active_dataset = {}
    dataset_name = str(_value(active_dataset, "dataset_name", "teaching_demo"))
    dataset_label = str(_value(active_dataset, "label", "教学演示数据"))
    dataset_message = str(
        _value(
            active_dataset,
            "message",
            "当前使用：教学演示数据，非文献原始数据。",
        )
    )
    dataset_files = _value(active_dataset, "files", {})
    if not isinstance(dataset_files, Mapping):
        dataset_files = {}
    dataset_source_counts = _value(active_dataset, "source_type_counts", {})
    if not isinstance(dataset_source_counts, Mapping):
        dataset_source_counts = {}
    dataset_missing = _value(active_dataset, "missing_items", [])
    if not isinstance(dataset_missing, list):
        dataset_missing = []

    report_id = _report_id(now, experiment_params)
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S")
    experiment_name = str(
        _value(
            experiment_params,
            "experiment_name",
            "锂离子电池热失控产气组成与混合气体可燃性评价虚拟实验",
        )
    )

    sample_info = _value(literature_data, "sample_info", {})
    if not isinstance(sample_info, Mapping):
        sample_info = {}

    scene_info = _value(experiment_params, "scene_info", {})
    if not isinstance(scene_info, Mapping):
        scene_info = {}

    gas_composition = _value(literature_data, "gas_composition", {})
    if not isinstance(gas_composition, Mapping):
        gas_composition = {}

    flammable_composition = _value(literature_data, "flammable_composition", {})
    if not isinstance(flammable_composition, Mapping):
        flammable_composition = {}

    normalized = _value(calculation_results, "normalized", {})
    if not isinstance(normalized, Mapping):
        normalized = {}

    lfl_constants = _value(calculation_results, "lfl_constants", {})
    if not isinstance(lfl_constants, Mapping):
        lfl_constants = {}

    risk_level, risk_description = _risk_level_text(
        _value(calculation_results, "risk_info", {}),
        calculation_results,
    )
    source_text = _source_value(sample_info, ["source", "reference", "DOI"])
    doi_text = _source_value(sample_info, ["DOI", "doi"])
    reference_text = _source_value(sample_info, ["reference", "source"])
    reliability_text = _source_value(sample_info, ["reliability_level", "data_status"])

    gas_rows = []
    for gas, value in gas_composition.items():
        gas_rows.append([gas, _fmt(value, 3), "是" if gas in flammable_composition else "否/不参与"])

    flammable_rows = []
    for gas, value in flammable_composition.items():
        flammable_rows.append([gas, _fmt(value, 3), _fmt(lfl_constants.get(gas), 3)])

    normalized_rows = []
    for gas, y_i in normalized.items():
        lfl_i = lfl_constants.get(gas)
        contribution = None
        try:
            contribution = float(y_i) / float(lfl_i)
        except (TypeError, ValueError, ZeroDivisionError):
            contribution = None
        normalized_rows.append([gas, _fmt(y_i, 6), _fmt(lfl_i, 3), _fmt(contribution, 6)])

    conclusion = (
        f"在所选文献样本和虚拟场景下，混合可燃下限 LFL_mix 为 "
        f"{_fmt(_value(calculation_results, 'lfl_mix', None), 2)} % vol，"
        f"虚拟空间浓度为 {_fmt(_value(calculation_results, 'space_concentration', None), 4)} % vol，"
        f"风险比值 R 为 {_fmt(_value(calculation_results, 'risk_ratio', None), 4)}，"
        f"教学风险等级为 {risk_level}。该结论仅用于虚拟仿真教学和模型理解。"
    )
    operation_logs = _value(interactive_state, "operation_logs", [])
    if not isinstance(operation_logs, list):
        operation_logs = []
    log_rows = [
        [log.get("time", "未记录"), log.get("action", "未记录"), log.get("level", "info"), log.get("message", "")]
        for log in operation_logs[:12]
        if isinstance(log, Mapping)
    ]

    if interactive_state:
        interactive_section = f"""
## 16. 二维交互实验流程记录

| 项目 | 内容 |
|---|---|
| 所选 SOC | {_value(interactive_state, 'selected_soc', '未记录')} |
| 气密性检测结果 | {'通过' if _value(interactive_state, 'leak_test_passed', False) else '未完成'} |
| 氮气置换次数 | {_value(interactive_state, 'replacement_count', 0)} |
| 当前阶段 | {_value(interactive_state, 'current_state', '未记录')} |
| 采样状态 | {'已完成' if _value(interactive_state, 'gas_bag_filled', False) else '未完成'} |
| GC 分析状态 | {'已完成' if _value(interactive_state, 'gc_finished', False) else '未完成'} |
| 产气量计算状态 | {_value(gas_volume_status, 'status', 'pending_user_input')} |
| 产气量说明 | {_value(gas_volume_status, 'message', '待补充文献产气量计算公式和参数')} |

### ARC 虚拟曲线摘要

ARC 温度和温升速率曲线为教学插值 / 模拟曲线，尚未接入可核验来源。

### 压力曲线摘要

20 L 密封气体收集罐压力变化为教学可视化模拟数据，尚未接入可核验来源曲线。

### GC 分析结果

GC 色谱峰为教学模拟显示；气体组成优先读取平台 `data/normalized_gas_data.csv` 字段。

### 操作评分

| 指标 | 值 |
|---|---|
| 最终得分 | {_value(score_summary, 'final_score', _value(interactive_state, 'score', '未记录'))} |
| 错误次数 | {_value(score_summary, 'error_count', _value(interactive_state, 'error_count', '未记录'))} |
| 实验完成度 | {_value(score_summary, 'completion_pct', '未记录')}% |

### 错误与操作日志

{_markdown_table(['时间', '动作', '级别', '说明'], log_rows)}

### 数据来源说明

1. `normalized_gas_data.csv` 当前示例数据需继续补充可核验文献来源。
2. `arc_curve_demo.csv` 为教学插值 / 模拟曲线。
3. `pressure_curve_demo.csv` 为教学可视化模拟数据。
4. `gc_peaks_demo.csv` 为教学模拟 GC 峰。
5. 产气量正式计算公式和参数待补充文献依据。
"""
    else:
        interactive_section = """
## 16. 二维交互实验流程记录

未检测到二维交互实验台 session 记录。本报告仍保留该章节，用于提示后续应从二维实验台生成包含操作日志、评分和设备流程状态的完整记录。
"""
    experiment_mode = str(
        _value(
            experiment_params,
            "experiment_mode",
            _value(interactive_state, "experiment_mode", ""),
        )
    )
    literature_device_section = (
        _build_zeng_2026_section()
        if experiment_mode in {"literature_explosion_chamber_heating", "文献装置模式"}
        else ""
    )
    registry_rows = _load_registry_rows()
    dataset_file_rows = [[key, value] for key, value in dataset_files.items()]
    dataset_count_rows = [[key, value] for key, value in dataset_source_counts.items()]
    pending_present = any("pending_user_input" in counts for counts in dataset_source_counts.values() if isinstance(counts, Mapping))
    if dataset_name == "teaching_demo":
        dataset_notice = "本报告使用教学演示数据，非文献原始数据。"
    elif dataset_missing:
        dataset_notice = "当前文献数据集不完整，缺失项仍显示为待补充。"
    else:
        dataset_notice = "本报告使用已校验文献数据；具体来源见文献数据接入状态和上传校验记录。"

    md = f"""# {experiment_name}报告

## 1. 报告基本信息

| 项目 | 内容 |
|---|---|
| 报告编号 | {report_id} |
| 生成时间 | {generated_at} |
| 实验名称 | {experiment_name} |
| 软件平台 | {APP_NAME} |
| 软件版本 | {APP_VERSION} |

## 2. 实验目的

1. 理解锂离子电池热失控产气组成样本的归一化表达方式和来源标注要求。
2. 掌握可燃组分识别和 Le Chatelier 混合可燃下限计算方法。
3. 理解虚拟空间浓度、LFL_mix 和风险比值 R 之间的关系。
4. 认识教学模型的假设、适用边界和局限性。

## 3. 实验原理

本虚拟实验以二维交互流程串联 ARC 热失控产气演示、20 L 密封罐收集、冷却后集气袋采样、GC 组成分析和可燃风险教学评价。气体组成进入 Le Chatelier 混合规则计算 LFL_mix，再与虚拟空间浓度 C 形成风险比值 R = C / LFL_mix。当前产气量正式公式、ARC 曲线、压力曲线和 GC 色谱峰均按数据来源登记处理，不作为可核验文献结果。

## 4. 软件平台说明

{APP_NAME} 是面向化学实验教学与虚拟仿真的轻量化 Streamlit 软件平台。平台使用 CSV 数据文件、Pandas 数据处理、Plotly 交互图表和轻量计算模型，形成从实验导学、文献数据、虚拟实验、可燃极限计算到报告生成的教学闭环。

## 5. 安全边界声明

> {SAFETY_NOTICE}
>
> 本报告不包含真实热失控、过充、针刺、加热、点火、制备可燃气体或混合可燃气体等危险实验步骤。所有风险评价均为教学评价标签，不用于真实安全决策。

## 6. 数据来源说明

本报告基于平台当前数据文件生成。数据来源完整性以项目数据字典和数据源登记表为准。

| 来源字段 | 内容 |
|---|---|
| source | {source_text} |
| data_type | {_value(sample_info, 'data_type', '未记录')} |
| data_status | {_value(sample_info, 'data_status', '未记录')} |
| DOI | {doi_text} |
| reference | {reference_text} |

数据按来源类型分级：
- **literature_with_experimental_label**：文献数据，含实验测量 LFL/UFL 标签
- **literature_gas_composition_only**：文献数据，仅含气体组成，无实验可燃极限标签
- **calculated_label**：基于 Le Chatelier 混合规则的教学估算值（非实验测量）
- **ML_prediction**：机器学习 LOOCV 交叉验证预测值（仅用于教学对比，小样本下不超越物理 baseline）

报告不补写未核实的文献作者、DOI、专利、测试结论或工程验证结果。

## 7. 文献数据接入状态

{_markdown_table(['数据文件', '数据类型', 'source_type', '是否文献数据', '说明'], registry_rows)}

### 当前使用数据集

| 项目 | 内容 |
|---|---|
| active_dataset | {dataset_name} |
| 数据集名称 | {dataset_label} |
| 数据集说明 | {dataset_message} |
| 教学演示数据 | {'是' if dataset_name == 'teaching_demo' else '否'} |
| 已校验文献数据 | {'是' if dataset_name == 'validated_literature' else '否'} |
| 是否存在 pending_user_input | {'是' if pending_present else '否'} |
| 缺失项 | {'，'.join(dataset_missing) if dataset_missing else '无'} |

{dataset_notice}

{_markdown_table(['数据项', '当前数据文件'], dataset_file_rows)}

{_markdown_table(['数据项', 'source_type 分布'], dataset_count_rows)}

| 接入项 | 当前状态 |
|---|---|
| 产气量公式状态 | {_value(gas_volume_status, 'status', 'pending_user_input')}；{_value(gas_volume_status, 'message', '待补充文献产气量计算公式和参数')} |
| ARC 曲线状态 | `arc_curve_demo.csv` 为教学插值 / 模拟曲线；`arc_curve_template.csv` 等待用户录入可核验来源 |
| GC 组分来源状态 | `normalized_gas_data.csv` 已扩充至 47 条文献产气组成数据（8种化学体系/SOC 0-143%/30-60°C）；`gc_composition_template.csv` 已准备 |
| LFL 常数来源状态 | `gas_lfl_constants.csv` 已更新为 SFPE Handbook / Engineering Toolbox / PHMSA 等权威来源；含 CAS 号和置信度标注 |
| 计算标签状态 | `calculated_lfl_labels.csv` 含 47 条记录的 fuel_basis / vent_known_basis / missing_as_N2 三种 Le Chatelier 计算结果 |
| ML 对比状态 | `ml_prediction_comparison.csv` 含 5 种模型 × 13 条实验标签的 LOOCV 预测；结论：当前数据规模下 ML 不超越物理 baseline |

## 8. 文献样本信息

| 字段 | 内容 |
|---|---|
| 样本名称 | {_value(sample_info, 'sample_label', _value(sample_info, 'source', '未记录'))} |
| 数据来源字段 | {_value(sample_info, 'source', '未记录')} |
| SOC | {_value(sample_info, 'soc', '未记录')} |
| 备注/触发方式字段 | {_value(sample_info, 'notes', '未记录')} |

## 9. 虚拟场景参数

| 参数 | 值 |
|---|---|
| 场景名称 | {_value(scene_info, 'scene_label', _value(scene_info, 'scenario_id', '未记录'))} |
| 虚拟空间体积 | {_fmt(_value(scene_info, 'room_volume_m3', None), 3)} m³ |
| 温度字段 | {_value(scene_info, 'temp_c', '未记录')} |
| 压力字段 | {_value(scene_info, 'pressure_kpa', '未记录')} |
| 通风条件 | {_value(scene_info, 'ventilation', '未记录')} |
| 通风稀释因子 | {_fmt(_value(experiment_params, 'ventilation_factor', None), 3)} |
| 虚拟总产气量 | {_fmt(_value(experiment_params, 'total_gas_l', None), 3)} L |

## 10. 气体组成表

{_markdown_table(['气体', '体积百分比 (% vol)', '是否参与 LFL 计算'], gas_rows)}

## 11. 可燃组分识别

参与 Le Chatelier 混合规则求和的可燃组分如下。CO₂、HF、N₂ 和其他非可燃或无有效 LFL 数据的组分不参与求和。

{_markdown_table(['气体', '原始体积百分比 (% vol)', 'LFL_i (% vol)'], flammable_rows)}

## 12. LFL_mix 计算结果

Le Chatelier 混合规则：

$$
LFL_{{mix}} = \\frac{{1}}{{\\sum_i \\frac{{y_i}}{{LFL_i}}}}
$$

其中 y_i 为可燃组分内部归一化体积分数，LFL_i 为纯物质可燃下限（% vol），不转换为小数。

{_markdown_table(['气体', '归一化 y_i', 'LFL_i (% vol)', 'y_i / LFL_i'], normalized_rows)}

**LFL_mix = {_fmt(_value(calculation_results, 'lfl_mix', None), 2)} % vol**

## 13. 虚拟空间浓度估算

虚拟空间浓度基于均匀混合假设估算：

| 指标 | 值 |
|---|---|
| 虚拟空间浓度 C | {_fmt(_value(calculation_results, 'space_concentration', None), 4)} % vol |
| 混合可燃下限 LFL_mix | {_fmt(_value(calculation_results, 'lfl_mix', None), 2)} % vol |

## 14. 风险比值 R

$$
R = \\frac{{C}}{{LFL_{{mix}}}}
$$

| 指标 | 值 |
|---|---|
| 风险比值 R | {_fmt(_value(calculation_results, 'risk_ratio', None), 4)} |
| 教学风险等级 | {risk_level} |

## 15. 教学风险等级和解释

{risk_description}

{interactive_section}

{literature_device_section}

## 17. 模型假设与局限性

1. Le Chatelier 混合规则为经验公式，当前版本用于理想混合体系的教学估算。本平台实现了三种计算变体：fuel_basis（仅可燃组分）、vent_known_basis（含 CO2 稀释修正）、missing_as_N2（缺失气体假设为惰性 N2）。
2. 当前模型未考虑 Burgess-Wheeler 温度修正和 Zabetakis 压力修正（均需额外实验数据支持，当前暂未激活）。
3. 虚拟空间浓度采用均匀混合假设，不描述扩散分层、局部积聚或真实事故演化。
4. 风险等级阈值仅用于课堂风险认知训练，不具有工程标准依据。
5. 产气组成数据来源于公开文献整理（47 条记录，8 种化学体系）；各条数据标注了 data_type（literature_with_experimental_label / literature_gas_composition_only）和 data_status（verified / partially_extracted / partially_extracted_gas_sum_below_85），字段解释以项目数据字典为准。
6. LFL/UFL 常数来源于 SFPE Handbook 5th Ed.、Engineering Toolbox、PHMSA 等公开参考来源，标注了置信度（high / medium）。
7. 机器学习预测结果为 LOOCV 交叉验证（5 种模型，13 条实验标签），在当前数据规模下物理 baseline（missing_as_N2 MAE≈1.21 vol%）优于所有 ML 模型。ML 仅用于教学对比展示，不替代物理模型。
8. 本报告不作为真实事故预测、消防应急或工程防爆设计依据。

## 18. 结论

{conclusion}

## 19. 思考题

1. 为什么 CO₂ 不参与 Le Chatelier 求和，但实际中仍可能影响可燃性？
2. 如果虚拟空间体积增大或通风稀释因子增大，R 值会如何变化？
3. LFL_i 使用 % vol 单位时，为什么不能错误转换为小数？
4. 报告结论中应如何避免把教学模型误写为真实工程安全判断？

## 20. 后续实验设计展望

后续可在安全边界内扩展更丰富的公开文献数据字段、学生学习记录、教师评价指标、报告模板和可解释图表。相关扩展仍应保持虚拟仿真教学定位，不加入真实危险实验流程或工程防爆设计建议。

## 21. 待补充文献项

1. 归一化产气组成样本的可核验文献来源、DOI、数据位置和归一化方法。
2. 产气量正式计算公式、适用条件和参数来源。
3. ARC 温度曲线、压力曲线和 GC 色谱峰的可核验文献或实验数据来源。
4. LFL / UFL 常数的标准、手册或数据库来源及适用条件。

## 22. 虚拟教学免责声明

本报告仅用于虚拟仿真教学，不用于真实事故预测、消防应急或工程防爆设计。
"""
    return md


def _markdown_to_basic_html(markdown_text: str) -> str:
    """将报告 Markdown 转为轻量 HTML，避免引入额外依赖。"""
    escaped = html.escape(markdown_text)
    lines = escaped.splitlines()
    html_lines: list[str] = []
    in_ul = False
    in_quote = False

    def close_lists() -> None:
        nonlocal in_ul
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False

    def close_quote() -> None:
        nonlocal in_quote
        if in_quote:
            html_lines.append("</blockquote>")
            in_quote = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            close_lists()
            close_quote()
            html_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            close_lists()
            close_quote()
            html_lines.append(f"<h1>{stripped[2:]}</h1>")
        elif re.match(r"^\d+\. ", stripped):
            close_quote()
            close_lists()
            html_lines.append(f"<p>{stripped}</p>")
        elif stripped.startswith("- "):
            close_quote()
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li>{stripped[2:]}</li>")
        elif stripped.startswith("&gt;"):
            close_lists()
            if not in_quote:
                html_lines.append("<blockquote>")
                in_quote = True
            html_lines.append(f"<p>{stripped.replace('&gt;', '', 1).strip()}</p>")
        elif stripped.startswith("|"):
            close_lists()
            close_quote()
            html_lines.append(f"<pre>{stripped}</pre>")
        elif stripped:
            close_lists()
            close_quote()
            html_lines.append(f"<p>{stripped}</p>")
        else:
            close_lists()
            close_quote()
    close_lists()
    close_quote()

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>虚拟实验教学报告</title>
<style>
body {{ font-family: "Microsoft YaHei", Arial, sans-serif; line-height: 1.75; color: #213547; max-width: 980px; margin: 32px auto; padding: 0 24px; }}
h1, h2 {{ color: #0b3a63; }}
blockquote {{ border-left: 5px solid #e69500; background: #fff8e1; padding: 8px 16px; color: #5f3b00; }}
pre {{ white-space: pre-wrap; background: #f8fbfe; border: 1px solid #d9e4ef; border-radius: 8px; padding: 8px 12px; }}
</style>
</head>
<body>
{chr(10).join(html_lines)}
</body>
</html>"""


def generate_report(
    experiment_params: dict,
    literature_data: dict,
    calculation_results: dict,
    output_format: str = "markdown",
) -> str:
    """
    生成结构化教学实验报告。

    Parameters
    ----------
    experiment_params : dict
        虚拟实验参数，如报告编号、场景信息、总产气量、通风因子。
    literature_data : dict
        文献样本信息、气体组成和可燃组分识别结果。
    calculation_results : dict
        LFL_mix、归一化组分、空间浓度、R 值和风险等级等计算结果。
    output_format : str
        输出格式，支持 "markdown" / "md" 或 "html"。

    Returns
    -------
    str
        生成的报告文本。
    """
    now = datetime.now()
    markdown_text = _build_markdown(
        experiment_params=experiment_params,
        literature_data=literature_data,
        calculation_results=calculation_results,
        now=now,
    )
    if output_format.lower() in {"markdown", "md"}:
        return markdown_text
    if output_format.lower() == "html":
        return _markdown_to_basic_html(markdown_text)
    raise ValueError("output_format 仅支持 markdown、md 或 html。")
