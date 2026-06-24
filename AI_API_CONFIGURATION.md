# AI_API_CONFIGURATION

更新时间：2026-06-19 10:22

## 当前默认引擎

AI 学伴默认读取 Streamlit secrets：

`.streamlit/secrets.toml`

当前配置为 DeepSeek：

```toml
[ai_companion]
provider = "deepseek"
enabled = true
base_url = "https://api.deepseek.com"
model = "deepseek-v4-flash"
timeout_seconds = 12
max_tokens = 900
temperature = 0.3
fallback_to_local = true
use_proxy = false
max_retries = 2
retry_base_delay_seconds = 1.0
thinking_enabled = false
```

当前 Key 状态：已配置真实值，长度 35，掩码 `sk-***c78`。不要把真实 Key 写入 `.py`、报告、截图、README 或测试输出。

## 本轮诊断结论

DeepSeek 调用失败的根因不是 Key、余额或模型名，而是 Python 请求自动使用了不可用的本地代理：

```text
HTTP_PROXY / HTTPS_PROXY = http://127.0.0.1:7897
ALL_PROXY = socks5://127.0.0.1:7897
```

该代理端口拒绝连接，导致 `connection_error`。直连 `api.deepseek.com:443` 成功。适配器已默认 `use_proxy = false`，通过无代理 opener 发送 DeepSeek 请求。

2026-06-24 补充：适配器会对 408、409、425、429、5xx 等瞬时错误进行短重试；DeepSeek V4 默认关闭 thinking mode，用于 AI 学伴即时问答，减少长推理带来的等待和多轮 reasoning_content 兼容问题。若 DeepSeek 返回空内容，也会明确回退本地规则并提示 DeepSeek 调用失败。

## 修改 API Key

打开 `.streamlit/secrets.toml`，修改：

```toml
[deepseek]
api_key = "你的真实 DeepSeek API Key"
```

## 修改模型

打开 `.streamlit/secrets.toml`，修改：

```toml
[ai_companion]
model = "deepseek-v4-flash"
```

官方当前模型包括 `deepseek-v4-flash` 和 `deepseek-v4-pro`。旧模型名 `deepseek-chat` / `deepseek-reasoner` 当前兼容映射到 V4 Flash，但官方文档显示将在 2026-07-24 15:59 UTC 后弃用。

## 修改 Base URL

打开 `.streamlit/secrets.toml`，修改：

```toml
[ai_companion]
base_url = "https://api.deepseek.com"
```

适配器会自动拼接 `/chat/completions`。不要在 `base_url` 中重复写 `/chat/completions`。

## 代理设置

默认：

```toml
use_proxy = false
```

如确实需要走本机代理，并确认代理端口可用，可以改为：

```toml
use_proxy = true
```

## 关闭 DeepSeek

```toml
[ai_companion]
enabled = false
```

关闭后 AI 学伴使用本地规则兜底。

## 临时环境变量方式

PowerShell 示例：

```powershell
$env:ENABLE_DEEPSEEK_CHAT="true"
$env:DEEPSEEK_API_KEY="你的 Key"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
$env:DEEPSEEK_USE_PROXY="false"
$env:DEEPSEEK_MAX_RETRIES="2"
$env:DEEPSEEK_RETRY_BASE_DELAY_SECONDS="1.0"
$env:DEEPSEEK_THINKING_ENABLED="false"
```

## 配置优先级

1. Streamlit secrets
2. DeepSeek 环境变量
3. 通用 OpenAI-compatible 环境变量
4. 本地规则知识库兜底

## 安全注意

- `.streamlit/secrets.toml`、`.env`、`.env.local` 已加入 `.gitignore`。
- `.streamlit/secrets.example.toml` 只包含占位 Key。
- 公开 provider 解析结果不返回 `api_key`。
- 诊断脚本只显示 Key 是否存在、是否占位符、长度和前后 3 位掩码。
- API 失败、超时、Key 缺失、Key 仍为占位值时，自动回退本地规则。

## 诊断脚本

运行：

```powershell
python scripts\check_deepseek_api.py
```

脚本发送最小请求：`请只回复：连接成功`，并分类 401、402、400/422、429、timeout、connection error 和 unknown。

## 官方依据

- DeepSeek 官方 API 文档显示 OpenAI 格式 Base URL 为 `https://api.deepseek.com`，当前模型为 `deepseek-v4-flash` / `deepseek-v4-pro`。
- DeepSeek 官方 Chat Completion 文档显示创建聊天补全使用 `POST /chat/completions`。
