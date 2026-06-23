# ACCEPTANCE_CHECKLIST

更新时间：2026-06-19 12:08

## AI 学伴

- [x] 默认只显示悬浮电池桌宠
- [x] 桌宠可拖拽
- [x] 点击打开聊天窗
- [x] 展开后只突出当前聊天
- [x] 历史记录默认隐藏
- [x] 学习评价默认隐藏且按需生成
- [x] JSON 导出默认隐藏且按需准备
- [x] 当前模式移入更多菜单
- [x] DeepSeek 失败时只短暂提示
- [x] 本地规则兜底保留
- [x] AI 提问不清空实验进度

## 性能与按需生成

- [x] 报告预览按钮后才生成 Markdown
- [x] HTML 下载按钮后才生成 HTML
- [x] Word 下载按钮后才生成 docx bytes
- [x] 学习评价按钮后才生成完整评价
- [x] 普通页面加载不生成 docx
- [x] 普通 AI 提问不生成报告/docx/评价
- [x] CSV 和页面资产继续使用 `st.cache_data`
- [x] DeepSeek timeout 保持 12 秒
- [x] DeepSeek 上下文保持精简

## 平板演示

- [x] 支持 `?demo=tablet`
- [x] 首页有“进入演示模式”入口
- [x] 主内容宽布局
- [x] 侧边栏默认收起但可打开
- [x] 触控按钮不小于 44px
- [x] 聊天窗不超过可视区
- [x] 表格可横向滚动
- [x] 已验证 1024×768、1180×820、1366×1024

## 进度保护

- [x] localStorage 保存轻量快照
- [x] 快照包含 SOC、阶段、完成步骤、采样、GC、LFL、报告状态
- [x] 快照不保存 API Key
- [x] 刷新后提示是否恢复
- [x] 不未经确认覆盖当前有效进度
- [x] 提供重新开始实验入口

## 部署

- [x] 国内云服务器部署脚本准备完成
- [x] systemd 模板准备完成
- [x] Nginx WebSocket 模板准备完成
- [x] 健康检查脚本准备完成
- [x] Streamlit Community Cloud 备用方案文档完成
- [x] `.gitignore` 排除 secrets、backups、artifacts

## 验证

- [x] `python -m compileall -q app tests`
- [x] `pytest -q`：`284 passed`
- [x] 关键截图已生成
