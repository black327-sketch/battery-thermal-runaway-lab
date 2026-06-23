# TABLET_DEMO_REPORT

更新时间：2026-06-19 12:08

## 平板演示模式

启用方式：

- 首页点击“进入演示模式”
- 或直接访问 `?demo=tablet`

## UI 调整

- 页面主容器加宽到 1480px。
- 侧边栏默认收起到左侧，触摸/聚焦时仍可打开。
- 主要按钮最小触控高度 44px。
- 顶部 hero 间距压缩，适合横屏首屏展示。
- 表格和 DataFrame 允许横向滚动。
- 二维实验台和工作台内边距收敛。
- 桌宠支持 pointer 事件拖拽，适配鼠标和触摸。
- 聊天窗在横屏平板尺寸下限制最大高度。

## 已验证尺寸

- 1024×768
- 1180×820
- 1366×1024

## 截图

- `artifacts/screenshots/tablet-home-clean.png`
- `artifacts/screenshots/tablet-lab-ai-collapsed.png`
- `artifacts/screenshots/tablet-lab-ai-chat-only.png`
- `artifacts/screenshots/tablet-ai-streaming-answer.png`
- `artifacts/screenshots/tablet-report-on-demand.png`
- `artifacts/screenshots/tablet-progress-restore.png`

## 推荐现场演示流程

1. 用平板横屏打开 `/?demo=tablet`。
2. 从首页说明两个实验部分和安全边界。
3. 进入二维交互实验台，展示桌宠默认收起状态。
4. 拖动桌宠并点击打开，只展示聊天核心。
5. 点击“下一步做什么”或输入问题，展示 AI 伴学反馈。
6. 完成若干实验步骤，刷新页面，展示恢复进度提示。
7. 进入报告页，先展示普通加载不生成 docx。
8. 点击“生成报告预览”，再按需生成 Word 或 HTML 下载文件。
