# PERFORMANCE_OPTIMIZATION_REPORT

更新时间：2026-06-19 12:08

## 本轮目标

面向平板横屏演示，减少默认渲染内容、降低 AI 和报告链路等待感，并为公网部署准备轻量方案。

## 优化结果

- AI 学伴默认只显示悬浮电池桌宠，展开后只保留标题、状态点、当前问答、输入框和最多三个快捷问题。
- 历史记录、学习评价、Markdown/JSON 导出、清空历史、结束对话、当前模式都移入 `⋯` 更多菜单。
- 默认渲染不再生成完整学习评价，也不再导出完整学习记录 JSON。
- 报告页拆分为三段按需生成：报告预览生成 Markdown，HTML 按钮生成 HTML，Word 按钮生成 docx bytes。
- DeepSeek 适配器新增 OpenAI-compatible SSE 流式解析能力，Key 仍只在后端使用。
- 桌宠请求仍通过受控 Streamlit component bridge 进入后端，不向浏览器下发 Key。
- 新增浏览器 localStorage 进度快照和显式恢复提示，刷新后不自动覆盖当前有效进度。
- 新增 `?demo=tablet` 平板演示模式，优化横屏宽度、触控按钮、侧边栏收起、表格横向滚动和聊天窗高度。

## 耗时记录

本轮修改前的可量化基线来自上一轮状态和本轮初始检查：报告页会在预览区内同时准备 Markdown、HTML、docx，AI 学伴默认会生成学习评价快照和完整 trace JSON。

本轮修改后轻量 HTTP 测量：

| 指标 | 修改前风险 | 修改后 |
| --- | --- | --- |
| 首页首次响应 | 页面资产正常，AI 默认附加信息较多 | 约 2081 ms |
| 二维实验台首次响应 | AI 提问可能带动页面重跑，但状态不丢 | 约 2040 ms |
| 报告页首次响应 | 有提前准备正式报告链路的风险 | 约 2055 ms |
| AI 首屏反馈 | 等完整回答时等待感明显 | 约 1.38 s 内出现轻量加载反馈 |
| 完整 AI 回答 | 取决于 DeepSeek 网络和模型 | 后端 timeout 12 s，失败快速本地兜底 |
| 点击生成报告 | 只在按钮后生成 Markdown | session 内缓存 |
| docx 生成 | 仅点击“生成 Word 下载文件”后执行 | session 内缓存 |
| 当前监听进程内存 | 上一轮约 167 MB 观测值 | 当前约 61.6 MB |

## 仍存在的瓶颈

- 当前桌宠是注入父页面的 Streamlit custom component，后端回答仍会触发一次 Streamlit rerun。已通过按需生成和缓存降低重算成本，但还不是完整双向 WebSocket token 级流式 UI。
- 真实首字时间取决于 DeepSeek 网络质量。适配器已支持流式解析，若后续需要真正 token 级更新到浮窗，需要增加受控的双向组件或小型后端 streaming endpoint。
- 二维实验台仍包含大型 SVG 和多标签内容，已避免 AI 默认触发报告/docx/评价生成，但复杂画布本身仍是主要页面成本。

## 验证

- `python -m compileall -q app tests`：通过
- `pytest -q`：`284 passed`
- 截图已生成到 `artifacts/screenshots/`
