# 锂离子电池热失控气体生成及可燃性评价数智化实验平台

本项目是一个面向化学实验教学与虚拟仿真的 Streamlit 应用，用于展示锂离子电池热失控归一化产气组成样本、演示混合可燃下限计算过程，并生成结构化教学报告。

## 项目定位

平台面向新能源材料安全化学相关课程和学生项目训练。当前版本以 CSV 数据、轻量计算函数和交互式页面为基础，提供从数据查看、虚拟计算到报告生成的基本流程。

本项目不用于真实事故预测、消防应急处置或工程防爆设计。页面中的风险等级只作为课堂讨论和模型理解指标。

## 当前版本

- 软件名称：锂离子电池热失控气体生成及可燃性评价数智化实验平台
- 版本号：v0.2.1
- 应用类型：Streamlit 多页面教学软件
- 数据存储：CSV 文件
- 主要依赖：Python、Streamlit、Pandas、Plotly

## 功能流程

```text
实验导学 → 文献数据库 → 虚拟实验 → 可燃极限计算 → 实验报告生成
```

平台围绕以下步骤组织：

1. 选择归一化产气组成样本。
2. 查看 H2、CO、CO2、CH4、C2H4、C2H6 等气体组成。
3. 识别参与计算的可燃组分。
4. 使用 Le Chatelier 混合规则计算 LFL_mix。
5. 在预设虚拟空间中估算气体浓度。
6. 计算风险比值 R，给出教学风险等级。
7. 生成 Markdown 或 HTML 教学报告。

## 已实现功能

- 首页：软件定位、数据资产概览、模块入口和流程说明。
- 实验导学：学习目标、核心概念、模型假设和安全边界。
- 文献数据库：样本筛选、关键字搜索、样本详情、气体组成图表和 CSV 下载。
- 虚拟实验：样本选择、场景选择、总产气量输入、LFL_mix、空间浓度、R 值和场景对比。
- 可燃极限计算：可燃组分识别、归一化比例、LFL_i、y_i / LFL_i 贡献和 LFL_mix 结果展示。
- 实验报告生成：读取最近一次虚拟实验记录或手动选择参数，生成 Markdown / HTML 报告。

## 目录结构

```text
digital_and_intelligent_platform/
├─ app/
│  ├─ main.py
│  ├─ pages/
│  │  ├─ 1_实验导学.py
│  │  ├─ 2_文献数据库.py
│  │  ├─ 3_虚拟实验.py
│  │  ├─ 4_可燃极限计算.py
│  │  └─ 5_实验报告生成.py
│  └─ utils/
│     ├─ app_config.py
│     ├─ chart_utils.py
│     ├─ data_loader.py
│     ├─ lfl_calculator.py
│     ├─ report_generator.py
│     ├─ risk_model.py
│     ├─ ui_components.py
│     └─ ui_theme.py
├─ data/
│  ├─ gas_lfl_constants.csv
│  ├─ normalized_gas_data.csv
│  └─ virtual_scenarios.csv
├─ docs/
├─ tests/
├─ requirements.txt
└─ README.md
```

## 核心模型说明

混合可燃下限采用 Le Chatelier 混合规则进行教学估算：

```text
LFL_mix = 1 / Σ(y_i / LFL_i)
```

其中：

- `y_i` 为可燃组分内部归一化体积分数。
- `LFL_i` 为纯物质可燃下限，单位为 `% vol`，不转换为小数。
- CO2、HF、N2 以及无有效 LFL 数据的组分不参与求和。

虚拟空间浓度采用均匀混合假设估算。风险比值定义为：

```text
R = C / LFL_mix
```

R 值和风险等级仅用于教学讨论，不作为真实安全判据。

## 数据说明

当前数据位于 `data/` 目录：

- `normalized_gas_data.csv`：归一化产气组成样本。
- `gas_lfl_constants.csv`：气体 LFL / UFL 常数和可燃性标识。
- `virtual_scenarios.csv`：虚拟空间场景参数。

现有数据仍需要补充更完整的真实文献来源、LFL/UFL 数据来源、CAS 号和可靠性标识。请参见 `docs/待补充材料清单.md`。

## 安全边界

本平台仅用于化学实验教学、虚拟仿真和数据分析演示，不用于真实事故预测、消防应急或工程防爆设计。

本项目不提供真实热失控实验、过充、针刺、加热、点火、制备可燃气体或混合可燃气体等危险实验流程。报告和页面中的风险等级均为教学评价标签。

## 安装与运行

```bash
cd D:\code\digital_and_intelligent_platform
pip install -r requirements.txt
streamlit run app/main.py
```

启动后按终端提示访问本地地址，通常为：

```text
http://localhost:8501
```

## 测试

```bash
cd D:\code\digital_and_intelligent_platform
pytest tests/ -v
```

## 后续开发计划

以下内容为计划或待确认方向：

- 补充真实文献来源字段和数据可靠性标识。
- 支持用户上传符合字段规范的 CSV 文件。
- 增加学生实验记录和教师评价字段。
- 扩展报告模板，评估是否需要 Word 或 PDF 导出。
- 增加更多虚拟场景和样本对比图表。

## 免责声明

本项目为教学软件原型及课程项目代码，不构成真实安全评价工具。任何计算结果、图表和报告均不得用于真实事故预测、应急处置、设备设计或工程防爆决策。
