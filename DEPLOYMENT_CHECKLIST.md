# 部署检查清单

- [ ] `.streamlit/secrets.toml` 未提交到 Git。
- [ ] 真实 DeepSeek Key 只在服务器 `/etc/digital-lab/digital-lab.env` 或平台 Secrets 中配置。
- [ ] `deploy/start_streamlit.sh` 可执行。
- [ ] systemd 服务监听 `127.0.0.1:8501`。
- [ ] Nginx 已配置 WebSocket Upgrade。
- [ ] HTTPS 证书有效。
- [ ] `deploy/check_health.sh` 返回 ok。
- [ ] 无真实 Key 出现在浏览器源码、日志、截图、下载报告中。
- [ ] 无运行时硬编码 `D:\` 路径。
- [ ] 无 Key 时可启动并回退本地规则。
- [ ] 有 Key 时桌宠显示 DeepSeek 智能伴学模式。
- [ ] 报告、HTML、docx、学习评价均按需生成。
- [ ] 平板访问 `/?demo=tablet` 无明显错位。
- [ ] 现场演示前限制分享范围或增加访问密码。
