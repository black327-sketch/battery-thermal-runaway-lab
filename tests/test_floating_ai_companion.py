from app.components.floating_ai_companion import _render_component_html, _sync_history_to_learning_trace
from app.components.floating_ai_companion import handle_ai_question_event
from app.utils.learning_trace import new_trace
from app.utils.teaching_ai_assistant import AssistantContext


def _html() -> str:
    return _render_component_html(
        component_id="test_page",
        context={
            "page_name": "首页",
            "current_stage": "未记录",
            "current_soc": "未选择",
            "stage_tip": "先选择 SOC。",
            "mode": "本地规则兜底模式",
        },
        visual={"stroke": "#1565c0", "fill": "#35d0df", "label": "学习提示"},
        history=[],
        latest_question="",
        latest_answer="",
        process_advice={
            "next_step_suggestion": "先选择 SOC。",
            "safety_hint": "仅用于虚拟仿真教学。",
            "learning_hint": "从样品准备开始。",
            "risk_hint": "保持教学估算边界。",
            "suggestion_level": "idle",
        },
        local_answers={"next_step": "先选择 SOC。", "default_answer": "本地规则回答。"},
        quick=["下一步该做什么？"],
        evaluation_markdown="",
        trace_json="{}",
        progress_snapshot={"version": 1, "soc": 100, "stage": "arc_ready", "completed_steps": ["battery_loaded"]},
    )


def test_floating_companion_injects_into_parent_document():
    html = _html()

    assert "floatingAiCompanionTemplate" in html
    assert "parentDocument.body.appendChild(root)" in html
    assert "floating-ai-root" in html
    assert "floating-ai-pet" in html
    assert "parentDocument.getElementById(rootId)" in html
    assert "components.html(" not in html


def test_floating_companion_has_drag_and_position_persistence():
    html = _html()

    assert "pointerdown" in html
    assert "pointermove" in html
    assert "pointerup" in html
    assert "localStorage" in html
    assert "floating-ai-companion-position-v3" in html
    assert "bottom: 96px" in html
    assert "bottom: 88px" in html
    assert "clamp(" in html
    assert "viewportWidth()" in html
    assert "viewportHeight()" in html


def test_floating_companion_click_open_and_clear_confirmation():
    html = _html()

    assert "if (!moved) setPanelOpen(true)" in html
    assert "确认清空 AI 聊天历史" in html
    assert "answerQuestion(q)" in html
    assert "window.location.assign" not in html
    assert "form.requestSubmit()" in html


def test_floating_companion_uses_backend_bridge_without_url_navigation():
    html = _html()

    assert "floating-ai-event" in html
    assert "postEvent('question'" in html
    assert "submitToBackend(question)" in html
    assert "bridgeFrame.contentWindow.postMessage" in html
    assert "正在生成回答" in html
    assert "tryPost();" in html
    assert "return true;" in html
    assert "45000" in html
    assert "buttonEl.click()" not in html
    assert "window.location.assign" not in html


def test_floating_companion_escapes_chat_content_and_avoids_old_panel_names():
    html = _html()

    assert "function esc(s)" in html
    assert "${esc(item.content)}" in html
    assert "teaching-ai-shell" not in html
    assert "ai-pet-shell" not in html
    assert "AI 学伴栏目" not in html


def test_floating_companion_defaults_to_lightweight_current_answer():
    html = _html()

    assert "latestQuestion" in html
    assert "latestAnswer" in html
    assert "renderCurrent" in html
    assert "renderHistory" in html
    assert "floating-ai-history" in html


def test_floating_companion_moves_extra_features_to_more_menu_and_snapshot():
    html = _html()

    assert "floating-ai-menu" in html
    assert "生成学习评价" in html
    assert "导出学习记录 JSON" in html
    assert "battery-lab-progress-snapshot-v1" in html
    assert "检测到未完成实验，是否恢复进度？" in html
    assert "restore_snapshot" in html
    assert html.count('data-el="historyBtn"') == 1


def test_sync_history_to_learning_trace_adds_missing_qa(monkeypatch):
    trace = new_trace()

    def fake_get_learning_trace():
        return trace

    monkeypatch.setattr("app.components.floating_ai_companion.get_learning_trace", fake_get_learning_trace)
    monkeypatch.setattr("app.utils.learning_trace.get_learning_trace", fake_get_learning_trace)

    _sync_history_to_learning_trace(
        [
            {"role": "user", "content": "LFL_mix 是什么？"},
            {"role": "assistant", "content": "LFL_mix 是教学估算。"},
        ]
    )
    _sync_history_to_learning_trace(
        [
            {"role": "user", "content": "LFL_mix 是什么？"},
            {"role": "assistant", "content": "LFL_mix 是教学估算。"},
        ]
    )

    assert len(trace["qa_events"]) == 1
    assert trace["qa_events"][0]["question_category"] == "LFL_mix与模型边界"


def test_ai_question_event_preserves_experiment_state(monkeypatch):
    trace = new_trace()
    experiment_state = {
        "current_state": "arc_ready",
        "selected_soc": 100,
        "battery_loaded": True,
        "replacement_count": 3,
    }
    before = experiment_state.copy()

    def fake_get_learning_trace():
        return trace

    monkeypatch.setattr("app.components.floating_ai_companion.get_learning_trace", fake_get_learning_trace)
    monkeypatch.setattr("app.utils.learning_trace.get_learning_trace", fake_get_learning_trace)

    result = handle_ai_question_event(
        key_prefix="lab_page",
        question="我下一步该做什么？",
        context=AssistantContext(page_name="二维交互实验台", current_stage="ARC 就绪", current_soc="100"),
        page_name="二维交互实验台",
        experiment_context=experiment_state,
        process_advice={"next_step_suggestion": "可以启动加热。"},
    )

    assert result["answer"]
    assert experiment_state == before
    assert len(trace["qa_events"]) == 1
