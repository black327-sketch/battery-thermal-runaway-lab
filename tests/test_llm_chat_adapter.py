import json
import socket
import urllib.error

from app.utils.llm_chat_adapter import (
    DEEPSEEK_MODE,
    DEEPSEEK_MISSING_KEY_MODE,
    LOCAL_MODE,
    answer_with_optional_llm,
    build_chat_payload_summary,
    current_chat_mode,
    enforce_chat_safety,
    is_deepseek_chat_enabled,
    is_external_chat_enabled,
    resolve_chat_provider,
)
from app.utils.teaching_ai_assistant import AssistantContext


def _deepseek_secrets(api_key: str = "sk-test-valid-key") -> dict:
    return {
        "ai_companion": {
            "provider": "deepseek",
            "enabled": True,
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-v4-flash",
            "timeout_seconds": 30,
            "max_tokens": 900,
            "temperature": 0.3,
            "fallback_to_local": True,
        },
        "deepseek": {"api_key": api_key},
    }


def test_external_chat_disabled_by_default():
    assert is_external_chat_enabled({}) is False

    result = answer_with_optional_llm("LFL_mix 是什么？", AssistantContext(), env={}, secrets={})

    assert result["used_external"] is False
    assert result["mode"] == LOCAL_MODE
    assert "LFL_mix" in result["answer"]


def test_external_chat_requires_complete_openai_compatible_env():
    assert is_external_chat_enabled({"ENABLE_EXTERNAL_LLM_CHAT": "true", "LLM_API_KEY": "k"}) is False
    assert (
        is_external_chat_enabled(
            {
                "ENABLE_EXTERNAL_LLM_CHAT": "true",
                "LLM_API_KEY": "k",
                "LLM_BASE_URL": "https://example.test/v1",
                "LLM_MODEL": "chat-model",
            }
        )
        is True
    )


def test_chat_payload_summary_excludes_raw_logs_and_sets_teaching_boundary():
    summary = build_chat_payload_summary(
        "为什么报警？",
        AssistantContext(page_name="二维交互实验台", current_stage="ARC 就绪", current_soc="100"),
        {"operation_count": 4, "qa_count": 2, "warning_count": 1, "raw_log": "不应上传完整日志"},
    )
    text = json.dumps(summary, ensure_ascii=False)

    assert "不应上传完整日志" not in text
    assert summary["trace_summary"]["operation_count"] == 4
    assert summary["page_name"] == "二维交互实验台"
    assert "电池实验 AI 学伴" in summary["knowledge_boundary"]
    assert "LFL_mix 是平台内的教学估算" in summary["knowledge_boundary"]
    assert "不提供真实危险实验操作步骤" in summary["knowledge_boundary"]


def test_external_chat_failure_falls_back(monkeypatch):
    def raise_url_error(*args, **kwargs):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("app.utils.llm_chat_adapter._open_url", raise_url_error)
    result = answer_with_optional_llm(
        "T2=100℃ 为什么采样？",
        AssistantContext(),
        env={
            "ENABLE_EXTERNAL_LLM_CHAT": "true",
            "LLM_API_KEY": "k",
            "LLM_BASE_URL": "https://example.test/v1",
            "LLM_MODEL": "chat-model",
        },
        secrets={},
    )

    assert result["used_external"] is False
    assert result["mode"] == "外接失败，已回退本地规则模式"
    assert "T2=100℃" in result["answer"]


def test_streamlit_secrets_enable_deepseek_by_default_without_leaking_key():
    provider = resolve_chat_provider(env={}, secrets=_deepseek_secrets("sk-realistic-secret-value"))

    assert provider["provider"] == "deepseek"
    assert provider["source"] == "streamlit_secrets"
    assert provider["enabled"] is True
    assert provider["mode"] == DEEPSEEK_MODE
    assert provider["base_url"] == "https://api.deepseek.com"
    assert provider["model"] == "deepseek-v4-flash"
    assert provider["timeout_seconds"] == 30
    assert provider["max_tokens"] == 900
    assert provider["temperature"] == 0.3
    assert "api_key" not in provider
    assert "sk-realistic-secret-value" not in str(provider)


def test_streamlit_secrets_placeholder_key_falls_back_to_local_mode():
    secrets = _deepseek_secrets("请在这里填入真实 DeepSeek API Key")
    provider = resolve_chat_provider(env={}, secrets=secrets)

    assert provider["enabled"] is False
    assert provider["provider"] == "local"
    assert provider["mode"] == DEEPSEEK_MISSING_KEY_MODE
    assert current_chat_mode(env={}, secrets=secrets) == "本地规则兜底模式：未配置真实 DeepSeek Key"


def test_deepseek_env_used_when_secrets_absent():
    env = {
        "ENABLE_DEEPSEEK_CHAT": "true",
        "DEEPSEEK_API_KEY": "deepseek-key",
        "ENABLE_EXTERNAL_LLM_CHAT": "true",
        "LLM_API_KEY": "generic-key",
        "LLM_BASE_URL": "https://example.test/v1",
        "LLM_MODEL": "generic-model",
    }

    provider = resolve_chat_provider(env, secrets={})

    assert is_deepseek_chat_enabled(env) is True
    assert provider["provider"] == "deepseek"
    assert provider["base_url"] == "https://api.deepseek.com"
    assert provider["model"] == "deepseek-v4-flash"
    assert provider["mode"] == DEEPSEEK_MODE
    assert "deepseek-key" not in str(provider)


def test_generic_openai_compatible_env_available_when_deepseek_absent():
    provider = resolve_chat_provider(
        {
            "ENABLE_EXTERNAL_LLM_CHAT": "true",
            "LLM_API_KEY": "generic-key",
            "LLM_BASE_URL": "https://example.test/v1",
            "LLM_MODEL": "chat-model",
        },
        secrets={},
    )

    assert provider["enabled"] is True
    assert provider["provider"] == "openai_compatible"
    assert provider["base_url"] == "https://example.test/v1"
    assert provider["model"] == "chat-model"
    assert "generic-key" not in str(provider)


def test_deepseek_success_uses_openai_compatible_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "这是虚拟仿真教学回答。"}}]}).encode("utf-8")

    def fake_open_url(request, timeout, use_proxy):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        captured["use_proxy"] = use_proxy
        captured["auth"] = request.headers.get("Authorization")
        return FakeResponse()

    monkeypatch.setattr("app.utils.llm_chat_adapter._open_url", fake_open_url)
    result = answer_with_optional_llm(
        "我下一步该做什么？",
        AssistantContext(page_name="二维交互实验台", current_stage="ARC 就绪", current_soc="100"),
        trace_summary={"operation_count": 5, "raw_log": "不应上传"},
        process_advice={"next_step_suggestion": "可以启动加热。"},
        env={},
        secrets=_deepseek_secrets("sk-valid-for-request"),
    )

    text = json.dumps(captured["body"], ensure_ascii=False)
    assert result["mode"] == DEEPSEEK_MODE
    assert result["used_external"] is True
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["body"]["model"] == "deepseek-v4-flash"
    assert captured["body"]["max_tokens"] == 900
    assert captured["body"]["temperature"] == 0.3
    assert captured["timeout"] == 30
    assert captured["use_proxy"] is False
    assert captured["auth"] == "Bearer sk-valid-for-request"
    assert "不应上传" not in text


def test_deepseek_failure_falls_back_without_leaking_key(monkeypatch):
    def raise_url_error(*args, **kwargs):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("app.utils.llm_chat_adapter._open_url", raise_url_error)
    result = answer_with_optional_llm(
        "LFL_mix 能作工程防爆依据吗？",
        AssistantContext(),
        env={},
        secrets=_deepseek_secrets("sk-secret-that-must-not-leak"),
    )

    assert result["used_external"] is False
    assert result["mode"] == "本地规则兜底模式：DeepSeek 网络连接失败"
    assert result["provider"] == "local"
    assert "sk-secret-that-must-not-leak" not in str(result)
    assert "LFL_mix" in result["answer"]


def test_deepseek_reasoning_content_is_used_when_content_empty(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "", "reasoning_content": "连接成功"}}]}
            ).encode("utf-8")

    monkeypatch.setattr("app.utils.llm_chat_adapter._open_url", lambda *args, **kwargs: FakeResponse())
    result = answer_with_optional_llm("测试", AssistantContext(), secrets=_deepseek_secrets("sk-secret"))

    assert result["mode"] == DEEPSEEK_MODE
    assert result["used_external"] is True
    assert result["answer"] == "连接成功"


def test_placeholder_key_does_not_send_request(monkeypatch):
    called = {"value": False}

    def fake_open_url(*args, **kwargs):
        called["value"] = True
        raise AssertionError("placeholder key should not call external API")

    monkeypatch.setattr("app.utils.llm_chat_adapter._open_url", fake_open_url)
    result = answer_with_optional_llm(
        "实验目的是什么？",
        AssistantContext(),
        env={},
        secrets=_deepseek_secrets("sk-xxxxxxxxxxxxxxxx"),
    )

    assert called["value"] is False
    assert result["used_external"] is False
    assert result["mode"] == "本地规则兜底模式：未配置真实 DeepSeek Key"


def test_missing_key_does_not_send_request(monkeypatch):
    called = {"value": False}

    def fake_open_url(*args, **kwargs):
        called["value"] = True
        raise AssertionError("missing key should not call external API")

    monkeypatch.setattr("app.utils.llm_chat_adapter._open_url", fake_open_url)
    result = answer_with_optional_llm(
        "实验目的是什么？",
        AssistantContext(),
        env={},
        secrets=_deepseek_secrets(""),
    )

    assert called["value"] is False
    assert result["used_external"] is False
    assert result["mode"] == "本地规则兜底模式：未配置真实 DeepSeek Key"


def _http_error(status: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://api.deepseek.com/chat/completions", status, "error", {}, None)


def test_deepseek_401_reports_auth_failure(monkeypatch):
    monkeypatch.setattr("app.utils.llm_chat_adapter._open_url", lambda *args, **kwargs: (_ for _ in ()).throw(_http_error(401)))

    result = answer_with_optional_llm("实验目的是什么？", AssistantContext(), secrets=_deepseek_secrets("sk-secret"))

    assert result["mode"] == "本地规则兜底模式：DeepSeek Key 鉴权失败"
    assert "sk-secret" not in str(result)


def test_deepseek_402_reports_balance_failure(monkeypatch):
    monkeypatch.setattr("app.utils.llm_chat_adapter._open_url", lambda *args, **kwargs: (_ for _ in ()).throw(_http_error(402)))

    result = answer_with_optional_llm("实验目的是什么？", AssistantContext(), secrets=_deepseek_secrets("sk-secret"))

    assert result["mode"] == "本地规则兜底模式：DeepSeek 账户余额不足"
    assert "sk-secret" not in str(result)


def test_deepseek_400_reports_model_or_parameter_error(monkeypatch):
    monkeypatch.setattr("app.utils.llm_chat_adapter._open_url", lambda *args, **kwargs: (_ for _ in ()).throw(_http_error(400)))

    result = answer_with_optional_llm("实验目的是什么？", AssistantContext(), secrets=_deepseek_secrets("sk-secret"))

    assert result["mode"] == "本地规则兜底模式：DeepSeek 模型名或请求参数错误"
    assert "sk-secret" not in str(result)


def test_deepseek_timeout_reports_timeout(monkeypatch):
    monkeypatch.setattr("app.utils.llm_chat_adapter._open_url", lambda *args, **kwargs: (_ for _ in ()).throw(socket.timeout("timed out")))

    result = answer_with_optional_llm("实验目的是什么？", AssistantContext(), secrets=_deepseek_secrets("sk-secret"))

    assert result["mode"] == "本地规则兜底模式：DeepSeek 网络超时"
    assert "sk-secret" not in str(result)


def test_stream_answer_parses_openai_compatible_sse(monkeypatch):
    from app.utils.llm_chat_adapter import stream_answer_with_optional_llm

    class FakeResponse:
        def __enter__(self):
            return iter(
                [
                    'data: {"choices":[{"delta":{"content":"连接"}}]}\n\n'.encode("utf-8"),
                    'data: {"choices":[{"delta":{"content":"成功"}}]}\n\n'.encode("utf-8"),
                    b"data: [DONE]\n\n",
                ]
            )

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.utils.llm_chat_adapter._open_url", lambda *args, **kwargs: FakeResponse())
    chunks = list(
        stream_answer_with_optional_llm(
            "测试",
            AssistantContext(),
            secrets=_deepseek_secrets("sk-realistic-test-key"),
        )
    )

    assert chunks == ["连接", "成功"]
    assert "sk-realistic-test-key" not in str(chunks)


def test_chat_safety_enforces_local_fallback():
    fallback = "本地安全边界回答"

    assert enforce_chat_safety("真实操作步骤：第一步...", fallback) == fallback
    assert enforce_chat_safety("消防处置建议如下", fallback) == fallback
    assert enforce_chat_safety("这是虚拟仿真教学中的边界提醒。", fallback) != fallback
