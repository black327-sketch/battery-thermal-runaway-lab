# DEEPSEEK_DIAGNOSTIC_REPORT

更新时间：2026-06-24 00:00

## 1. DeepSeek 失败根因

根因是本机代理配置不可用。系统环境变量将 Python/urllib 请求导向 `127.0.0.1:7897`，该端口拒绝连接，导致 DeepSeek 请求失败并回退本地规则。

直连 `api.deepseek.com:443` 成功，因此不是 API Key 错误、余额不足或模型名不可用。

## 2. Key 配置状态

- Key 是否存在：是
- 是否占位符：否
- Key 长度：35
- Key 掩码：`sk-***c78`

未在任何报告中输出完整 Key。

## 3. 当前 Base URL

`https://api.deepseek.com`

适配器自动拼接 `/chat/completions`。

## 4. 当前 Model

`deepseek-v4-flash`

官方文档当前模型为 `deepseek-v4-flash` / `deepseek-v4-pro`。旧模型名 `deepseek-chat` 和 `deepseek-reasoner` 当前兼容，但将在 2026-07-24 15:59 UTC 后弃用。

## 5. 最小连通性测试

脚本：

```powershell
python scripts\check_deepseek_api.py
```

结果：

```text
result: success
category: ok
reply_preview: 连接成功
```

2026-06-24 复测结果仍为 `result: success`、`category: ok`、`reply_preview: 连接成功`。诊断脚本使用 `deepseek-v4-flash`，并默认关闭 thinking mode。

## 5.1 自动化测试

- `python -m compileall -q app tests scripts`：通过
- `pytest -q`：`277 passed`
- 覆盖占位 Key 不请求、无 Key 不请求、401、402、400/422、timeout、connection error、瞬时 HTTP 错误重试、空响应回退、成功响应、`reasoning_content` 兼容、Key 不泄露、AI 提问后实验状态不被修改。

## 6. 修复文件

- `app/utils/llm_chat_adapter.py`
- `scripts/check_deepseek_api.py`
- `.streamlit/secrets.toml`
- `.streamlit/secrets.example.toml`
- `tests/test_llm_chat_adapter.py`
- `tests/test_ai_api_configuration.py`
- `AI_API_CONFIGURATION.md`
- `AI_ASSISTANT_REPORT.md`
- `ITERATION_REPORT.md`
- `DEPLOYMENT_GUIDE.md`

## 7. UI 错误提示

已从泛化“调用失败”改为分类提示：

- 未配置真实 Key
- Key 鉴权失败
- 账户余额不足
- 模型名或请求参数错误
- 频率限制
- 网络超时
- 网络连接失败

## 8. 本地兜底

仍保留。任何 Key 缺失、占位 Key、鉴权失败、余额不足、模型参数错误、频率限制、超时或网络错误都会回退本地规则，不会阻塞实验进度。

2026-06-24 额外修复：前端 bridge 重试不再和本地兜底回答竞速；状态灯改为显示最近一次问答的实际模式；前端超时保护延长到 45 秒，避免后端重试期间误报失败。

## 9. Key 泄露风险

已控制：

- 诊断脚本只显示 Key 存在性、占位符判断、长度和掩码。
- 公开 provider 不返回 `api_key`。
- 错误结果不包含 Key。
- 报告和最终输出不包含完整 Key。

## 10. 后续修改方式

修改 Key：

```toml
[deepseek]
api_key = "你的真实 DeepSeek API Key"
```

修改模型：

```toml
[ai_companion]
model = "deepseek-v4-flash"
```

修改 Base URL：

```toml
[ai_companion]
base_url = "https://api.deepseek.com"
```

如确需代理：

```toml
[ai_companion]
use_proxy = true
```
