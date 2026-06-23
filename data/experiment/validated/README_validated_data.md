# 真实文献数据 validated 模板目录

本目录存放经过校验的真实文献数据模板（均为空模板，仅表头）。

## 目录说明

| 文件 | 用途 |
|------|------|
| `literature_metadata_validated.csv` | 文献元数据：题名、作者、期刊、DOI、实验类型 |
| `battery_sample_validated.csv` | 电池样品参数：类型、化学体系、容量、SOC、质量 |
| `thermal_runaway_stage_validated.csv` | 热失控阶段划分：温度区间、主要事件、可观察现象 |
| `reaction_mechanism_validated.csv` | 反应机理：各阶段化学反应过程、产气组分 |
| `gas_generation_reaction_validated.csv` | 产气反应方程：具体化学方程式、反应物、产物 |
| `gc_composition_validated.csv` | GC 气体组成：各阶段各气体组分的体积百分比 |
| `lel_constants_reference_validated.csv` | LFL/UFL 常数来源：标准或手册引用、适用条件 |
| `mechanism_visual_assets.csv` | 机理可视化素材：场景描述、标签、反应方程式、视觉风格说明 |
| `mechanism_video_assets.csv` | 机理可视化视频素材：动画目标、旁白文案、转场说明 |

## source_type 取值规则

| 取值 | 含义 | 使用条件 |
|------|------|----------|
| `literature` | 从正式文献中提取的数据 | 必须有可核验的文献来源（DOI、页码、图表编号） |
| `teaching_interpolation` | 从文献曲线中插值获得的教学数据 | 必须注明原文献和插值方法 |
| `teaching_simulation` | 教学模拟数据，非文献真实数据 | 必须添加说明，不得伪装为真实文献数据 |
| `pending_user_input` | 占位字段，待用户填写 | 默认值，表示暂无有效数据 |

### 关键规则

1. **`source_type=literature` 时**：`source_location` 不得为空，必须写明具体表号/图号/段落。
2. **`source_type=teaching_simulation` 时**：严禁标记为真实文献数据。
3. **`source_type=pending_user_input` 时**：表示该字段或记录暂无数据，等待用户录入。
4. **`source_type=teaching_interpolation` 时**：必须注明插值源自哪篇文献的哪个图表。

## source_location 填写格式

```
期刊缩写 年份, 表X / 图X / 第X节
```

示例（仅说明格式，非真实数据）：

```
J. Power Sources 2020, Table 2
Electrochim. Acta 2019, Fig. 4(b)
```

## 必填字段

### literature_metadata_validated.csv

- `literature_id`：唯一标识，如 `LIT-YYYY-001`
- `title`：文献完整题名
- `source_type`：必须为 `literature` 或 `pending_user_input`

### battery_sample_validated.csv

- `sample_id`：样品唯一标识
- `literature_id`：对应文献 ID
- `soc_pct`：荷电状态百分比
- `source_type`：数据来源类型

### thermal_runaway_stage_validated.csv

- `stage_id`：阶段唯一标识
- `stage_order`：阶段序号
- `stage_name`：阶段名称

### gc_composition_validated.csv

- `composition_id`：组分记录 ID
- `gas_component`：气体分子式（如 H₂、CO、CO₂、CH₄）
- `source_type`：数据来源类型

### lel_constants_reference_validated.csv

- `component`：气体分子式
- `lfl_vol_pct`：可燃下限（体积百分比）
- `source_type`：常数来源类型

### mechanism_visual_assets.csv（建议必填）

- `asset_id`：素材唯一标识
- `asset_title`：素材标题
- `scene_description`：场景描述
- `visual_style`：视觉风格说明

### mechanism_video_assets.csv（建议必填）

- `video_id`：视频素材唯一标识
- `segment_title`：片段标题
- `duration_s`：时长（秒）

## 禁止事项

1. 禁止把教学模拟数据（`teaching_simulation`）标为真实文献数据（`literature`）
2. 禁止把教学插值数据（`teaching_interpolation`）标为原始文献测量值
3. 禁止编造虚假 DOI、作者、题名
4. 禁止编造虚假实验数据
5. 禁止在 `pending_user_input` 状态下行填入编造数值
6. 空模板本身不应导致程序崩溃或测试失败


