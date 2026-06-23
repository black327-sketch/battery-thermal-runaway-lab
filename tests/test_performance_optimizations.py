from pathlib import Path


def test_report_page_generates_formal_report_only_on_demand():
    source = Path("app/pages/7_实验报告生成.py").read_text(encoding="utf-8")

    helper_pos = source.index("def _get_formal_report_markdown")
    preview_pos = source.index('if st.session_state.get("show_formal_report_preview", False):')
    direct_generation_pos = source.find("formal_md = generate_formal_report(report_ctx)")

    assert helper_pos < preview_pos
    assert direct_generation_pos == -1
    assert "formal_md = _get_formal_report_markdown(report_ctx)" in source
    assert "st.button(\"生成 Word 下载文件\"" in source
    assert "st.button(\"生成 HTML 下载文件\"" in source
    assert "_get_formal_report_docx(report_ctx)" in source
    preview_block = source[source.index('if st.session_state.get("show_formal_report_preview", False):') :]
    assert "docx_bytes = generate_docx(report_ctx)" not in preview_block


def test_lightweight_chat_does_not_render_history_by_default():
    source = Path("app/components/floating_ai_companion.py").read_text(encoding="utf-8")

    assert ".floating-ai-history {{ display:none;" in source
    assert "renderCurrent" in source
    assert "renderHistory" in source
    assert "window.location.assign" not in source
    render_block = source[source.index("def render_floating_ai_companion") :]
    assert "build_learning_evaluation_snapshot()" not in render_block
    assert "export_learning_trace_json(trace)," not in source


def test_data_loaders_use_streamlit_cache():
    lab_source = Path("app/pages/5_二维交互实验台.py").read_text(encoding="utf-8")
    report_source = Path("app/pages/7_实验报告生成.py").read_text(encoding="utf-8")

    assert "@st.cache_data" in lab_source
    assert "@st.cache_data" in report_source
