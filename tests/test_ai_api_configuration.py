from pathlib import Path

from app.utils.llm_chat_adapter import LOCAL_MODE, current_chat_mode, resolve_chat_provider


def test_secrets_templates_exist_without_real_key():
    secrets = Path(".streamlit/secrets.toml").read_text(encoding="utf-8")
    example = Path(".streamlit/secrets.example.toml").read_text(encoding="utf-8")

    assert 'provider = "deepseek"' in secrets
    assert 'enabled = true' in secrets
    assert 'base_url = "https://api.deepseek.com"' in secrets
    assert 'model = "deepseek-v4-flash"' in secrets
    assert "api_key =" in secrets
    assert "请在这里填入真实 DeepSeek API Key" not in secrets
    assert 'api_key = "sk-xxxxxxxxxxxxxxxx"' in example
    assert 'max_tokens = 900000' not in secrets
    assert "sk-test" not in secrets


def test_gitignore_keeps_private_secret_files_out_of_git():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert ".streamlit/secrets.toml" in gitignore
    assert ".env" in gitignore
    assert ".env.local" in gitignore


def test_default_placeholder_secrets_resolve_to_local_fallback():
    secrets = {
        "ai_companion": {
            "provider": "deepseek",
            "enabled": True,
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "timeout_seconds": 12,
            "max_tokens": 900,
            "temperature": 0.3,
            "fallback_to_local": True,
        },
        "deepseek": {"api_key": "请在这里填入真实 DeepSeek API Key"},
    }

    provider = resolve_chat_provider(env={}, secrets=secrets)

    assert provider["enabled"] is False
    assert provider["mode"] == "本地规则兜底模式：未配置真实 DeepSeek Key"
    assert current_chat_mode(env={}, secrets=secrets) == "本地规则兜底模式：未配置真实 DeepSeek Key"
