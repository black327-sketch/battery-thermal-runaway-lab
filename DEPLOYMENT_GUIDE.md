# 部署指南

## 方案 A：国内云服务器正式演示方案

推荐环境：Ubuntu 22.04/24.04、Python 3.10+、Nginx、systemd、HTTPS 证书。DeepSeek Key 只放在服务器安全位置，不提交到 Git。

1. 创建服务用户和目录：

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin digital-lab
sudo mkdir -p /opt/digital-lab /etc/digital-lab
sudo chown -R digital-lab:digital-lab /opt/digital-lab
```

2. 上传项目到 `/opt/digital-lab`，创建 venv 并安装依赖：

```bash
cd /opt/digital-lab
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
chmod +x deploy/start_streamlit.sh deploy/check_health.sh
```

3. 配置 DeepSeek 和 Streamlit 环境文件 `/etc/digital-lab/digital-lab.env`：

```bash
APP_DIR=/opt/digital-lab
VENV_DIR=/opt/digital-lab/.venv
STREAMLIT_HOST=127.0.0.1
STREAMLIT_PORT=8501
ENABLE_DEEPSEEK_CHAT=true
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=12
DEEPSEEK_USE_PROXY=false
DEEPSEEK_API_KEY=sk-REPLACE_WITH_REAL_KEY
```

设置权限：

```bash
sudo chown root:digital-lab /etc/digital-lab/digital-lab.env
sudo chmod 640 /etc/digital-lab/digital-lab.env
```

4. 安装 systemd 服务：

```bash
sudo cp deploy/digital-lab.service.example /etc/systemd/system/digital-lab.service
sudo systemctl daemon-reload
sudo systemctl enable --now digital-lab
sudo systemctl status digital-lab
```

5. 配置 Nginx 和 HTTPS：

```bash
sudo cp deploy/nginx-streamlit.conf.example /etc/nginx/sites-available/digital-lab.conf
sudo ln -s /etc/nginx/sites-available/digital-lab.conf /etc/nginx/sites-enabled/digital-lab.conf
sudo nginx -t
sudo systemctl reload nginx
```

将 `example.com` 替换为你的域名。证书可用 Certbot 或云厂商证书服务签发。

6. 健康检查：

```bash
/opt/digital-lab/deploy/check_health.sh
curl -I https://你的域名/
```

还需要你提供：云服务器 IP、SSH 登录方式、域名、HTTPS 证书方案。未提供前，本项目只准备部署包和文档，不购买或连接云资源。

## 方案 B：Streamlit Community Cloud 备用方案

1. 确认仓库入口为 `app/main.py`。
2. 不上传 `.streamlit/secrets.toml`、`.env`、`backups/`、`artifacts/`。
3. 在 Community Cloud Secrets 管理界面填写：

```toml
[ai_companion]
enabled = true
provider = "deepseek"
base_url = "https://api.deepseek.com"
model = "deepseek-v4-flash"
timeout_seconds = 12
max_tokens = 900
temperature = 0.3
fallback_to_local = true
use_proxy = false

[deepseek]
api_key = "sk-REPLACE_WITH_REAL_KEY"
```

4. 部署后访问公网 URL，验证首页、二维实验台、AI 学伴、报告按需生成和 Word 下载。

该方案适合临时分享。正式课堂演示优先使用国内云服务器，便于访问速度、HTTPS、Nginx WebSocket 和服务自恢复控制。
