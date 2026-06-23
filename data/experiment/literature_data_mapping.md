# 文献数据接入字段映射说明

本目录用于准备后续接入可核验论文数据。当前模板不包含真实文献数据，空值和 `pending_user_input` 表示等待用户补充。

## 1. 实验对象提取

从论文的实验方法、材料表、补充信息中提取电池类型、外形、化学体系、正负极、电解液、额定容量、电压、质量和能量。录入 `battery_sample_template.csv`。如果论文未给出某字段，保持空值，不推断。

## 2. SOC 记录

SOC 使用 `soc_pct`，单位为百分数，不写 `%` 符号。不同 SOC 的样品必须使用不同 `sample_id` 或在曲线/组成表中逐行记录。

## 3. ARC 关键温度点

论文给出的自发热起点、排气、热失控起点、最高温、冷却结束等节点录入 `arc_key_points_template.csv`。`phase` 建议使用 `initial`、`self_heating_onset`、`venting`、`thermal_runaway_onset`、`max_temperature`、`cooling`、`end`。

## 4. ARC 曲线

文献原始表格数据可标 `source_type=literature`，并填写 `literature_id` 与 `source_location`。从图像数字化得到的数据必须在 `notes` 写明 `digitized_from_figure`。根据关键节点插值得到的曲线必须标 `teaching_interpolation`，不得标为 `literature`。

## 5. 20 L 罐压力曲线

压力曲线录入 `pressure_curve_template.csv`。如果论文未给出压力曲线，保持 `pending_user_input`；用于页面演示的曲线保持 `teaching_simulation`。

## 6. GC 组分

GC 组分录入 `gc_composition_template.csv`。`gas_component` 使用分子式，如 `H2`、`CO`、`CO2`、`CH4`、`C2H4`、`C2H6`、`C3H6`、`C3H8`、`O2`、`N2`、`others`。归一化数据的 `measurement_basis` 写 `normalized_volume_fraction`，文献原始体积分数写 `reported_volume_fraction`。

## 7. GC 色谱峰

GC 峰录入 `gc_peaks_template.csv`。如果论文没有峰图、峰位或响应强度，不得补造数值，保持 `pending_user_input` 或页面演示数据的 `teaching_simulation`。

## 8. 产气量公式

产气量公式和参数录入 `gas_volume_formula_template.csv`。如果使用理想气体状态方程，必须逐项记录 `P`、`V`、`n`、`R`、`T` 的数值、单位和来源位置；如有修正系数，也必须逐项记录。缺少公式时继续 `pending_user_input`。

## 9. LFL / UFL 常数来源

LFL / UFL 来源录入 `lel_constants_reference_template.csv`。记录标准、手册、数据库或文献来源、适用温度压力和适用范围。没有来源时不得写“权威数据”。

## 10. source_type 区分

- `literature`：文献表格、正文或补充材料中可定位的数据，必须有 `literature_id` 和 `source_location`。
- `teaching_interpolation`：由关键节点或图示趋势插值得到的教学曲线，不是文献原始数据。
- `teaching_simulation`：为界面演示和教学流程生成的模拟数据。
- `pending_user_input`：等待用户补充或核验的数据。

## 11. 避免误写

不要把示例数据、插值曲线、模拟色谱峰、模拟压力曲线写成文献数据。只有在 `source_type=literature` 且具有明确文献编号、页码/表号/图号/补充材料位置时，才可在页面或报告中称为文献数据。
