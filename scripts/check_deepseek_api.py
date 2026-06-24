"""Safe DeepSeek connectivity diagnostic.

The script never prints the full API key, full headers, or full request body.
It reads Streamlit secrets first, then environment variables.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PLACEHOLDER_MARKERS = (
    "请在这里填入真实",
    "你的 key",
    "你的key",
    "your key",
    "sk-xxxxxxxx",
    "xxxxxxxx",
    "placeholder",
    "example",
)


def mask_key(value: str) -> str:
    key = str(value or "").strip()
    if not key:
        return "(empty)"
    if len(key) <= 6:
        return f"{key[:1]}***{key[-1:]}"
    return f"{key[:3]}***{key[-3:]}"


def looks_placeholder(value: str) -> bool:
    lower = str(value or "").strip().lower()
    return not lower or any(marker in lower for marker in PLACEHOLDER_MARKERS)


def read_config() -> dict[str, Any]:
    secrets_path = Path(".streamlit/secrets.toml")
    data: dict[str, Any] = {}
    if secrets_path.exists():
        data = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
    ai = data.get("ai_companion", {}) if isinstance(data.get("ai_companion", {}), dict) else {}
    deepseek = data.get("deepseek", {}) if isinstance(data.get("deepseek", {}), dict) else {}
    return {
        "source": "streamlit_secrets" if secrets_path.exists() else "environment",
        "enabled": ai.get("enabled", os.getenv("ENABLE_DEEPSEEK_CHAT", "").lower() == "true"),
        "provider": ai.get("provider", "deepseek"),
        "base_url": ai.get("base_url") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
        "model": ai.get("model") or os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash",
        "api_key": deepseek.get("api_key") or ai.get("api_key") or os.getenv("DEEPSEEK_API_KEY") or "",
        "timeout_seconds": float(ai.get("timeout_seconds") or os.getenv("DEEPSEEK_TIMEOUT_SECONDS") or 12),
        "use_proxy": bool(ai.get("use_proxy", False)) or os.getenv("DEEPSEEK_USE_PROXY", "").lower() == "true",
        "thinking_enabled": bool(ai.get("thinking_enabled", False))
        or os.getenv("DEEPSEEK_THINKING_ENABLED", "").lower() == "true",
    }


def classify_http_error(status: int, body: str) -> tuple[str, str]:
    lower = body.lower()
    if status == 401:
        return "auth_failed", "DeepSeek Key 鉴权失败"
    if status == 402:
        return "insufficient_balance", "DeepSeek 账户余额不足"
    if status in {400, 422}:
        if "model" in lower and ("not" in lower or "invalid" in lower or "不存在" in lower):
            return "model_or_parameter_error", "DeepSeek 模型名或请求参数错误"
        return "bad_request", "DeepSeek 请求格式或模型参数错误"
    if status == 429:
        return "rate_limited", "DeepSeek 频率限制"
    return "unknown_http_error", f"DeepSeek HTTP {status} 错误"


def main() -> int:
    cfg = read_config()
    api_key = str(cfg["api_key"]).strip()
    print(f"source: {cfg['source']}")
    print(f"enabled: {cfg['enabled']}")
    print(f"provider: {cfg['provider']}")
    print(f"base_url: {cfg['base_url']}")
    print(f"model: {cfg['model']}")
    print(f"key_exists: {bool(api_key)}")
    print(f"key_looks_placeholder: {looks_placeholder(api_key)}")
    print(f"key_length: {len(api_key)}")
    print(f"key_mask: {mask_key(api_key)}")
    print(f"use_proxy: {cfg['use_proxy']}")
    if looks_placeholder(api_key):
        print("result: skipped")
        print("category: missing_real_key")
        print("message: DeepSeek 未配置真实 Key，未发起请求")
        return 2

    url = str(cfg["base_url"]).rstrip("/")
    if url.endswith("/chat/completions"):
        endpoint = url
    else:
        endpoint = f"{url}/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": "你是实验教学助手。"},
            {"role": "user", "content": "请只回复：连接成功"},
        ],
        "temperature": 0,
        "max_tokens": 80,
        "thinking": {"type": "enabled" if cfg["thinking_enabled"] else "disabled"},
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        if cfg["use_proxy"]:
            opener = urllib.request.build_opener()
        else:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=float(cfg["timeout_seconds"])) as response:  # nosec - user-configured diagnostic
            data = json.loads(response.read().decode("utf-8"))
        message = data.get("choices", [{}])[0].get("message", {})
        content = str(message.get("content") or message.get("reasoning_content") or "").strip()
        print("result: success")
        print("category: ok")
        print(f"reply_preview: {content[:30]}")
        return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        category, message = classify_http_error(exc.code, body)
        print("result: failed")
        print(f"status: {exc.code}")
        print(f"category: {category}")
        print(f"message: {message}")
        print(f"safe_error_preview: {body}")
        return 1
    except (socket.timeout, TimeoutError):
        print("result: failed")
        print("category: timeout")
        print("message: DeepSeek 网络超时")
        return 1
    except urllib.error.URLError as exc:
        reason = str(getattr(exc, "reason", exc))[:240]
        print("result: failed")
        print("category: connection_error")
        print("message: DeepSeek 网络/代理/DNS 连接失败")
        print(f"safe_error_preview: {reason}")
        return 1
    except Exception as exc:  # pragma: no cover - diagnostic safety net
        print("result: failed")
        print("category: unknown")
        print(f"message: {type(exc).__name__}")
        print(f"safe_error_preview: {str(exc)[:240]}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
