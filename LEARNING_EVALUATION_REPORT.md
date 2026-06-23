# LEARNING_EVALUATION_REPORT

更新时间：2026-06-18 23:59

## 本轮结论

学习评价功能保留。为减少页面刷新和长内容重绘，桌宠前端默认不再展示完整聊天历史，只显示当前问题、当前回答、当前模式和进程建议。后台评价仍基于操作记录、问答记录、报警记录和学习状态快照。

## 数据来源

- 操作记录：`operation_events`
- 问答记录：`qa_events`
- 报警记录：`warning_events`
- 学习状态：`learning_state`

记录不足时继续显示“记录不足”，不做主观评价。

## 与轻量 UI 的关系

- 前端当前只展示最近一次问答。
- 历史默认折叠，避免长聊天记录拖慢页面。
- JSON 导出仍保留完整学习轨迹。
- Markdown 评价仍由本地规则生成。

## DeepSeek/外接模型

评价适配器仍默认不联网。聊天适配器新增 DeepSeek 支持，但学习评价仍以本地客观记录为主，避免把外部模型输出当作评分依据。

## 测试

- `tests/test_learning_trace.py`
- `tests/test_learning_evaluation.py`
- `tests/test_floating_ai_companion.py`
- `tests/test_ai_process_advisor.py`

结果：`pytest -q`，`263 passed`。
