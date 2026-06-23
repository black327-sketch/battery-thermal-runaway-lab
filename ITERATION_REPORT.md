# ITERATION_REPORT

更新时间：2026-06-19 12:08

## 本轮完成项

1. 创建修改前备份：`backups/pre-tablet-demo-deployment-20260619-114621/`
2. 精简 AI 学伴主界面，只保留桌宠、当前问答、输入框和最多三个快捷入口。
3. 将历史、评价、导出、清空、结束、模式查看等移入 `⋯` 菜单或按需事件。
4. 报告 Markdown、HTML、docx 拆分为按需生成。
5. 新增 DeepSeek/OpenAI-compatible 流式 SSE 解析函数。
6. 新增 `?demo=tablet` 平板演示模式。
7. 新增 localStorage 进度快照与显式恢复。
8. 新增国内云服务器部署模板和 Streamlit Community Cloud 备用说明。
9. 更新 `.gitignore`，排除 secrets、备份和截图产物。
10. 增加测试覆盖并完成全量验证。

## 修改文件摘要

- `app/components/floating_ai_companion.py`
- `app/components/ai_companion_bridge/index.html`
- `app/utils/llm_chat_adapter.py`
- `app/utils/progress_snapshot.py`
- `app/utils/ui_theme.py`
- `app/main.py`
- `app/pages/7_实验报告生成.py`
- `deploy/start_streamlit.sh`
- `deploy/check_health.sh`
- `deploy/digital-lab.service.example`
- `deploy/nginx-streamlit.conf.example`
- `DEPLOYMENT_GUIDE.md`
- `DEPLOYMENT_CHECKLIST.md`
- `PERFORMANCE_OPTIMIZATION_REPORT.md`
- `TABLET_DEMO_REPORT.md`
- `ACCEPTANCE_CHECKLIST.md`

## 关键取舍

`st.fragment` 当前环境支持，但本项目 AI 桌宠已采用注入父页面的 custom component。为避免重写成页面内面板，本轮保留受控 bridge，并通过按需生成、缓存、隐藏历史和轻量上下文降低 rerun 成本。适配器已具备流式解析能力，后续如要 token 级逐字进入浮窗，需要进一步扩展双向组件。

## 验证

- `python -m compileall -q app tests`：通过
- `pytest -q`：`284 passed`
- 平板尺寸浏览器验证：1024×768、1180×820、1366×1024 已用于截图和交互检查
- 报告页普通打开不生成 docx，预览后才显示 HTML/Word 生成按钮
- localStorage 恢复提示已截图验证
