from app.utils.llm_evaluation_adapter import (
    build_anonymized_summary,
    get_external_llm_supplement,
    is_external_llm_enabled,
)


def test_external_llm_disabled_by_default_without_key():
    env = {}
    assert is_external_llm_enabled(env) is False
    result = get_external_llm_supplement({"metrics": {}}, env=env)
    assert result["used"] is False
    assert result["status"] == "disabled"


def test_external_llm_missing_model_falls_back():
    env = {"ENABLE_EXTERNAL_LLM_EVALUATION": "true", "LLM_API_KEY": "secret"}
    assert is_external_llm_enabled(env) is False
    result = get_external_llm_supplement({"metrics": {}}, env=env)
    assert result["enabled"] is False
    assert result["used"] is False
    assert result["status"] == "disabled"


def test_external_llm_enabled_with_openai_compatible_env_but_not_called():
    env = {
        "ENABLE_EXTERNAL_LLM_EVALUATION": "true",
        "LLM_API_KEY": "secret",
        "LLM_BASE_URL": "https://example.test/v1",
        "LLM_MODEL": "chat-model",
    }
    assert is_external_llm_enabled(env) is True
    result = get_external_llm_supplement({"metrics": {}}, env=env)
    assert result["enabled"] is True
    assert result["used"] is False
    assert result["status"] == "not_called"


def test_anonymized_summary_excludes_raw_qa_logs():
    evaluation = {
        "metrics": {
            "total_operations": 3,
            "qa_count": 2,
            "warning_count": 1,
            "raw_question": "完整原始问题不应上传",
        },
        "levels": {"completion": "进行中"},
        "suggestions": ["复习四次采样"],
    }
    summary = build_anonymized_summary(evaluation)
    text = str(summary)

    assert "完整原始问题" not in text
    assert summary["metrics"]["total_operations"] == 3
    assert summary["privacy_note"]
