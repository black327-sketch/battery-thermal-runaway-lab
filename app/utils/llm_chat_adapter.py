"""DeepSeek/OpenAI-compatible chat adapter for the floating companion.

Streamlit secrets are the default configuration source. Missing keys, invalid
placeholder keys, network failures, and unsafe model responses all fall back to
the local teaching rule base.
"""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any, Iterator

from app.utils.teaching_ai_assistant import AssistantContext, answer_question


LOCAL_MODE = "本地规则兜底模式"
LEGACY_LOCAL_MODE = "本地规则模式"
DEEPSEEK_MODE = "DeepSeek 智能伴学模式"
GENERIC_MODE = "外接大模型增强模式"
DEEPSEEK_MISSING_KEY_MODE = "本地规则兜底模式：未配置真实 DeepSeek Key"
DEEPSEEK_AUTH_FAILED_MODE = "本地规则兜底模式：DeepSeek Key 鉴权失败"
DEEPSEEK_BALANCE_MODE = "本地规则兜底模式：DeepSeek 账户余额不足"
DEEPSEEK_BAD_REQUEST_MODE = "本地规则兜底模式：DeepSeek 模型名或请求参数错误"
DEEPSEEK_RATE_LIMIT_MODE = "本地规则兜底模式：DeepSeek 频率限制"
DEEPSEEK_TIMEOUT_MODE = "本地规则兜底模式：DeepSeek 网络超时"
DEEPSEEK_CONNECTION_MODE = "本地规则兜底模式：DeepSeek 网络连接失败"
DEEPSEEK_FAILURE_MODE = "本地规则兜底模式：DeepSeek 调用失败"
GENERIC_FAILURE_MODE = "外接失败，已回退本地规则模式"

DEFAULT_AI_COMPANION_CONFIG: dict[str, Any] = {
    "provider": "deepseek",
    "enabled": True,
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-v4-flash",
    "timeout_seconds": 12.0,
    "max_tokens": 900,
    "temperature": 0.3,
    "fallback_to_local": True,
    "use_proxy": False,
}

PLACEHOLDER_KEY_MARKERS = (
    "请在这里填入真实",
    "你的 key",
    "你的key",
    "your key",
    "sk-xxxxxxxx",
    "xxxxxxxx",
    "placeholder",
    "example",
)

BOUNDARY_TERMS = ("真实操作步骤", "消防处置步骤", "工程防爆设计依据", "事故预测结论")
BLOCKED_TOPICS = ("灭火", "消防处置", "真实实验操作", "工程防爆", "事故预测", "危险化学品处置")
REFERENCE_FACTS = (
    "实验对象为 22Ah 方壳磷酸铁锂电池。",
    "四次采样节点为 T2=100℃、安全阀喷阀、温度峰值、压力稳定/反应结束。",
    "热失控判据为温升速率 >=1℃/s 且持续 3s。",
    "0%SOC 可喷阀，但参考文献实验中未发生热失控；安全阀喷阀不等于一定热失控。",
    "SOC 越高，热失控越剧烈，可燃气体浓度通常越高。",
    "H2 和 CO2 是主要气体；CO 和碳氢化合物会随热失控发展上升。",
    "LFL_mix 是平台内的教学估算，不是真实工程防爆依据。",
)


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return _truthy(value)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_nested(mapping: Mapping[str, Any] | None, section: str, key: str, default: Any = None) -> Any:
    if not mapping:
        return default
    try:
        section_value = mapping.get(section, {})  # type: ignore[attr-defined]
    except AttributeError:
        return default
    if not isinstance(section_value, Mapping):
        return default
    try:
        return section_value.get(key, default)
    except AttributeError:
        return default


def _get_section(mapping: Mapping[str, Any] | None, section: str) -> Mapping[str, Any]:
    if not mapping:
        return {}
    try:
        section_value = mapping.get(section, {})  # type: ignore[attr-defined]
    except AttributeError:
        return {}
    return section_value if isinstance(section_value, Mapping) else {}


def _load_streamlit_secrets() -> Mapping[str, Any] | None:
    """Read Streamlit secrets when available without making tests depend on Streamlit runtime."""

    try:
        import streamlit as st

        secrets = st.secrets
        if not secrets:
            return None
        return secrets
    except Exception:
        return None


def _is_placeholder_key(value: Any) -> bool:
    key = str(value or "").strip()
    if not key:
        return True
    lower = key.lower()
    return any(marker in lower for marker in PLACEHOLDER_KEY_MARKERS)


def _sanitize_provider(provider: Mapping[str, Any]) -> dict[str, Any]:
    safe = {key: value for key, value in provider.items() if key != "api_key"}
    safe["has_api_key"] = not _is_placeholder_key(provider.get("api_key"))
    return safe


def _provider_mode(provider_name: str) -> str:
    return DEEPSEEK_MODE if provider_name == "deepseek" else GENERIC_MODE


def _missing_key_mode(provider_name: str) -> str:
    return DEEPSEEK_MISSING_KEY_MODE if provider_name == "deepseek" else LOCAL_MODE


def _failure_mode(provider_name: str) -> str:
    return DEEPSEEK_FAILURE_MODE if provider_name == "deepseek" else GENERIC_FAILURE_MODE


def _build_chat_endpoint(base_url: str) -> str:
    url = str(base_url or DEFAULT_AI_COMPANION_CONFIG["base_url"]).strip().rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    return f"{url}/chat/completions"


def _classify_http_error(provider_name: str, status: int, body: str = "") -> str:
    if provider_name != "deepseek":
        return GENERIC_FAILURE_MODE
    lower = (body or "").lower()
    if status == 401:
        return DEEPSEEK_AUTH_FAILED_MODE
    if status == 402:
        return DEEPSEEK_BALANCE_MODE
    if status in {400, 422}:
        return DEEPSEEK_BAD_REQUEST_MODE
    if status == 429:
        return DEEPSEEK_RATE_LIMIT_MODE
    if "model" in lower and ("not" in lower or "invalid" in lower or "不存在" in lower):
        return DEEPSEEK_BAD_REQUEST_MODE
    return DEEPSEEK_FAILURE_MODE


def _open_url(request: urllib.request.Request, *, timeout: float, use_proxy: bool) -> Any:
    if use_proxy:
        return urllib.request.urlopen(request, timeout=timeout)  # nosec - user-configured endpoint
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(request, timeout=timeout)


def _extract_chat_content(data: Mapping[str, Any]) -> str:
    choices = data.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, Mapping):
        return ""
    message = first.get("message", {})
    if not isinstance(message, Mapping):
        return ""
    content = str(message.get("content") or "").strip()
    if content:
        return content
    return str(message.get("reasoning_content") or "").strip()


def _extract_stream_delta(data: Mapping[str, Any]) -> str:
    choices = data.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, Mapping):
        return ""
    delta = first.get("delta", {})
    if not isinstance(delta, Mapping):
        return ""
    return str(delta.get("content") or delta.get("reasoning_content") or "")


def _resolve_from_secrets(secrets: Mapping[str, Any] | None) -> dict[str, Any] | None:
    ai = _get_section(secrets, "ai_companion")
    if not ai:
        return None

    provider_name = str(ai.get("provider", DEFAULT_AI_COMPANION_CONFIG["provider"])).strip() or "deepseek"
    enabled = _to_bool(ai.get("enabled", DEFAULT_AI_COMPANION_CONFIG["enabled"]), True)
    if not enabled:
        return {"enabled": False, "provider": "local", "mode": LOCAL_MODE, "source": "streamlit_secrets_disabled"}

    api_key = (
        _get_nested(secrets, provider_name, "api_key")
        or _get_nested(secrets, "deepseek", "api_key")
        or ai.get("api_key")
    )
    base_url = str(ai.get("base_url", DEFAULT_AI_COMPANION_CONFIG["base_url"])).strip()
    model = str(ai.get("model", DEFAULT_AI_COMPANION_CONFIG["model"])).strip()
    fallback_to_local = _to_bool(ai.get("fallback_to_local", True), True)
    provider = {
        "enabled": not _is_placeholder_key(api_key),
        "provider": provider_name,
        "mode": _provider_mode(provider_name),
        "source": "streamlit_secrets",
        "api_key": str(api_key or "").strip(),
        "base_url": base_url or str(DEFAULT_AI_COMPANION_CONFIG["base_url"]),
        "model": model or str(DEFAULT_AI_COMPANION_CONFIG["model"]),
        "timeout_seconds": _to_float(ai.get("timeout_seconds"), float(DEFAULT_AI_COMPANION_CONFIG["timeout_seconds"])),
        "max_tokens": _to_int(ai.get("max_tokens"), int(DEFAULT_AI_COMPANION_CONFIG["max_tokens"])),
        "temperature": _to_float(ai.get("temperature"), float(DEFAULT_AI_COMPANION_CONFIG["temperature"])),
        "fallback_to_local": fallback_to_local,
        "use_proxy": _to_bool(ai.get("use_proxy", DEFAULT_AI_COMPANION_CONFIG["use_proxy"]), False),
    }
    if provider["enabled"]:
        return provider
    if fallback_to_local:
        return {
            "enabled": False,
            "provider": "local",
            "mode": _missing_key_mode(provider_name),
            "source": "streamlit_secrets",
            "base_url": provider["base_url"],
            "model": provider["model"],
            "timeout_seconds": provider["timeout_seconds"],
            "max_tokens": provider["max_tokens"],
            "temperature": provider["temperature"],
            "fallback_to_local": True,
            "use_proxy": False,
        }
    return None


def is_external_chat_enabled(env: Mapping[str, str] | None = None) -> bool:
    env = env or os.environ
    return (
        _truthy(env.get("ENABLE_EXTERNAL_LLM_CHAT"))
        and not _is_placeholder_key(env.get("LLM_API_KEY"))
        and bool(env.get("LLM_BASE_URL"))
        and bool(env.get("LLM_MODEL"))
    )


def is_deepseek_chat_enabled(env: Mapping[str, str] | None = None) -> bool:
    env = env or os.environ
    return _truthy(env.get("ENABLE_DEEPSEEK_CHAT")) and not _is_placeholder_key(env.get("DEEPSEEK_API_KEY"))


def _resolve_from_env(env: Mapping[str, str] | None) -> dict[str, Any]:
    env = env or os.environ
    if is_deepseek_chat_enabled(env):
        return {
            "enabled": True,
            "provider": "deepseek",
            "mode": DEEPSEEK_MODE,
            "source": "environment",
            "api_key": str(env["DEEPSEEK_API_KEY"]),
            "base_url": env.get("DEEPSEEK_BASE_URL", str(DEFAULT_AI_COMPANION_CONFIG["base_url"])),
            "model": env.get("DEEPSEEK_MODEL", str(DEFAULT_AI_COMPANION_CONFIG["model"])),
            "timeout_seconds": _to_float(env.get("DEEPSEEK_TIMEOUT_SECONDS"), float(DEFAULT_AI_COMPANION_CONFIG["timeout_seconds"])),
            "max_tokens": _to_int(env.get("DEEPSEEK_MAX_TOKENS"), int(DEFAULT_AI_COMPANION_CONFIG["max_tokens"])),
            "temperature": _to_float(env.get("DEEPSEEK_TEMPERATURE"), float(DEFAULT_AI_COMPANION_CONFIG["temperature"])),
            "fallback_to_local": True,
            "use_proxy": _truthy(env.get("DEEPSEEK_USE_PROXY")),
        }
    if is_external_chat_enabled(env):
        return {
            "enabled": True,
            "provider": "openai_compatible",
            "mode": GENERIC_MODE,
            "source": "environment",
            "api_key": str(env["LLM_API_KEY"]),
            "base_url": str(env["LLM_BASE_URL"]),
            "model": str(env["LLM_MODEL"]),
            "timeout_seconds": _to_float(env.get("LLM_TIMEOUT_SECONDS"), float(DEFAULT_AI_COMPANION_CONFIG["timeout_seconds"])),
            "max_tokens": _to_int(env.get("LLM_MAX_TOKENS"), int(DEFAULT_AI_COMPANION_CONFIG["max_tokens"])),
            "temperature": _to_float(env.get("LLM_TEMPERATURE"), float(DEFAULT_AI_COMPANION_CONFIG["temperature"])),
            "fallback_to_local": True,
            "use_proxy": _truthy(env.get("LLM_USE_PROXY")),
        }
    return {"enabled": False, "provider": "local", "mode": LOCAL_MODE, "source": "local_rules"}


def _resolve_chat_provider_with_secret(
    env: Mapping[str, str] | None = None,
    secrets: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve the active provider including the API key for internal request construction."""

    loaded_secrets = secrets if secrets is not None else _load_streamlit_secrets()
    provider = _resolve_from_secrets(loaded_secrets)
    if provider is not None:
        return provider
    return _resolve_from_env(env)


def resolve_chat_provider(
    env: Mapping[str, str] | None = None,
    secrets: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve the active chat provider without exposing API keys or making a network call."""

    return _sanitize_provider(_resolve_chat_provider_with_secret(env=env, secrets=secrets))


def current_chat_mode(env: Mapping[str, str] | None = None, secrets: Mapping[str, Any] | None = None) -> str:
    provider = resolve_chat_provider(env=env, secrets=secrets)
    return str(provider.get("mode", LOCAL_MODE))


def build_chat_payload_summary(
    question: str,
    context: AssistantContext,
    trace_summary: Mapping[str, Any] | None = None,
    process_advice: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a limited, anonymized teaching payload for an external model."""

    return {
        "page_name": context.page_name,
        "current_stage": context.current_stage,
        "current_soc": context.current_soc,
        "question": question[:500],
        "trace_summary": {
            "operation_count": int((trace_summary or {}).get("operation_count", 0)),
            "qa_count": int((trace_summary or {}).get("qa_count", 0)),
            "warning_count": int((trace_summary or {}).get("warning_count", 0)),
        },
        "process_advice": {
            "next_step_suggestion": str((process_advice or {}).get("next_step_suggestion", ""))[:240],
            "safety_hint": str((process_advice or {}).get("safety_hint", ""))[:240],
            "risk_hint": str((process_advice or {}).get("risk_hint", ""))[:240],
        },
        "reference_facts": REFERENCE_FACTS,
        "knowledge_boundary": (
            "你是“电池实验 AI 学伴”，服务于锂离子电池热失控数智化虚拟仿真实验教学。"
            "主线任务是围绕实验目的、流程、SOC 影响、四次采样节点、气体组分、LFL_mix、报警理由、"
            "报告数据来源和学习评价进行答疑与引导。你也可以回答一般学习问题，但要优先回到本实验上下文。"
            "回答时先给结论，再解释原因，必要时给出“你现在可以做什么”。"
            "尽量结合当前页面、当前 SOC、当前实验阶段、已完成步骤、报警记录和报告完成情况。"
            f"必须遵守事实依据：{'；'.join(REFERENCE_FACTS)}。"
            "安全边界：本平台只用于虚拟仿真教学；不提供真实危险实验操作步骤、消防处置建议、"
            "工程防爆设计方案或事故预测结论；不得把教学风险等级写成真实工程判断。"
            "如果资料不足，请说明“当前资料不足，建议查看参考文献或教师说明”。"
        ),
    }


def enforce_chat_safety(answer: str, fallback: str) -> str:
    text = answer or ""
    if any(term in text for term in BOUNDARY_TERMS):
        return fallback
    if any(topic in text for topic in BLOCKED_TOPICS) and "虚拟仿真教学" not in text:
        return fallback
    if "真实" in text and ("步骤" in text or "处置" in text) and "不提供" not in text:
        return fallback
    return text.strip() or fallback


def answer_with_optional_llm(
    question: str,
    context: AssistantContext,
    *,
    trace_summary: Mapping[str, Any] | None = None,
    process_advice: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
    secrets: Mapping[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Answer with local rules, optionally trying DeepSeek/OpenAI-compatible API."""

    local_answer = answer_question(question, context)
    provider = _resolve_chat_provider_with_secret(env=env, secrets=secrets)
    if not provider["enabled"]:
        mode = str(provider.get("mode", LOCAL_MODE))
        return {
            "mode": mode if mode != LEGACY_LOCAL_MODE else LOCAL_MODE,
            "used_external": False,
            "answer": local_answer,
            "provider": "local",
        }

    payload_summary = build_chat_payload_summary(question, context, trace_summary, process_advice)
    url = _build_chat_endpoint(str(provider["base_url"]))
    body = {
        "model": provider["model"],
        "messages": [
            {"role": "system", "content": payload_summary["knowledge_boundary"]},
            {"role": "user", "content": json.dumps(payload_summary, ensure_ascii=False)},
        ],
        "temperature": float(provider.get("temperature", DEFAULT_AI_COMPANION_CONFIG["temperature"])),
        "max_tokens": int(provider.get("max_tokens", DEFAULT_AI_COMPANION_CONFIG["max_tokens"])),
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {provider['api_key']}",
        },
        method="POST",
    )
    request_timeout = float(timeout if timeout is not None else provider.get("timeout_seconds", DEFAULT_AI_COMPANION_CONFIG["timeout_seconds"]))
    try:
        with _open_url(request, timeout=request_timeout, use_proxy=bool(provider.get("use_proxy", False))) as response:
            data = json.loads(response.read().decode("utf-8"))
        external = _extract_chat_content(data)
        return {
            "mode": provider["mode"],
            "used_external": True,
            "answer": enforce_chat_safety(external, local_answer),
            "provider": provider["provider"],
        }
    except urllib.error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:400]
        mode = _classify_http_error(str(provider.get("provider", "")), exc.code, safe_body)
        return {
            "mode": mode,
            "used_external": False,
            "answer": local_answer,
            "provider": "local",
            "error_category": "http_error",
            "status_code": exc.code,
        }
    except (socket.timeout, TimeoutError):
        return {
            "mode": DEEPSEEK_TIMEOUT_MODE if provider.get("provider") == "deepseek" else GENERIC_FAILURE_MODE,
            "used_external": False,
            "answer": local_answer,
            "provider": "local",
            "error_category": "timeout",
        }
    except urllib.error.URLError:
        return {
            "mode": DEEPSEEK_CONNECTION_MODE if provider.get("provider") == "deepseek" else GENERIC_FAILURE_MODE,
            "used_external": False,
            "answer": local_answer,
            "provider": "local",
            "error_category": "connection_error",
        }
    except (OSError, KeyError, json.JSONDecodeError):
        return {
            "mode": _failure_mode(str(provider.get("provider", ""))),
            "used_external": False,
            "answer": local_answer,
            "provider": "local",
            "error_category": "unknown",
        }


def stream_answer_with_optional_llm(
    question: str,
    context: AssistantContext,
    *,
    trace_summary: Mapping[str, Any] | None = None,
    process_advice: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
    secrets: Mapping[str, Any] | None = None,
    timeout: float | None = None,
) -> Iterator[str]:
    """Yield a DeepSeek/OpenAI-compatible streaming answer, or local fallback text."""

    local_answer = answer_question(question, context)
    provider = _resolve_chat_provider_with_secret(env=env, secrets=secrets)
    if not provider["enabled"]:
        yield local_answer
        return

    payload_summary = build_chat_payload_summary(question, context, trace_summary, process_advice)
    url = _build_chat_endpoint(str(provider["base_url"]))
    body = {
        "model": provider["model"],
        "messages": [
            {"role": "system", "content": payload_summary["knowledge_boundary"]},
            {"role": "user", "content": json.dumps(payload_summary, ensure_ascii=False)},
        ],
        "temperature": float(provider.get("temperature", DEFAULT_AI_COMPANION_CONFIG["temperature"])),
        "max_tokens": int(provider.get("max_tokens", DEFAULT_AI_COMPANION_CONFIG["max_tokens"])),
        "stream": True,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {provider['api_key']}",
        },
        method="POST",
    )
    request_timeout = float(timeout if timeout is not None else provider.get("timeout_seconds", DEFAULT_AI_COMPANION_CONFIG["timeout_seconds"]))
    chunks: list[str] = []
    try:
        with _open_url(request, timeout=request_timeout, use_proxy=bool(provider.get("use_proxy", False))) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data_text = line[5:].strip()
                if data_text == "[DONE]":
                    break
                try:
                    piece = _extract_stream_delta(json.loads(data_text))
                except json.JSONDecodeError:
                    continue
                if piece:
                    chunks.append(piece)
                    yield piece
    except Exception:
        if not chunks:
            yield local_answer
