"""Draggable floating AI companion injected as a lightweight Streamlit component."""

from __future__ import annotations

import html
import json
from pathlib import Path
from collections.abc import Mapping
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from streamlit.components.v1 import declare_component

from app.utils.ai_process_advisor import build_process_advice
from app.utils.learning_evaluation import evaluate_learning
from app.utils.learning_trace import (
    export_learning_trace_json,
    get_learning_trace,
    record_operation,
    record_qa,
    sync_warnings_from_assessment,
    update_learning_state_from_experiment,
)
from app.utils.llm_chat_adapter import answer_with_optional_llm
from app.utils.llm_chat_adapter import current_chat_mode
from app.utils.llm_evaluation_adapter import get_external_llm_supplement
from app.utils.progress_snapshot import apply_progress_snapshot_to_session
from app.utils.teaching_ai_assistant import (
    AssistantContext,
    assistant_status,
    build_assistant_context,
    quick_questions,
    stage_tip,
)


HISTORY_LIMIT = 80
SNAPSHOT_VERSION = 1
_BRIDGE_COMPONENT = declare_component(
    "floating_ai_companion_bridge",
    path=str(Path(__file__).parent / "ai_companion_bridge"),
)


def _state_key(prefix: str, name: str) -> str:
    return f"{prefix}_floating_ai_{name}"


def _trace_summary() -> dict[str, int]:
    trace = get_learning_trace()
    return {
        "operation_count": len(trace.get("operation_events", [])),
        "qa_count": len(trace.get("qa_events", [])),
        "warning_count": len(trace.get("warning_events", [])),
    }


def _context_dict(context: AssistantContext, mode: str) -> dict[str, str]:
    return {
        "page_name": context.page_name,
        "current_stage": context.current_stage,
        "current_soc": context.current_soc,
        "stage_tip": stage_tip(context),
        "mode": mode,
    }


def _compact_experiment_snapshot(experiment_context: Mapping[str, Any] | None) -> dict[str, Any]:
    state = dict(experiment_context or {})
    sampling = state.get("sampling_completed", {})
    completed = [
        key
        for key in [
            "battery_loaded",
            "arc_door_closed",
            "leak_test_passed",
            "gas_bag_filled",
            "gc_finished",
            "gas_volume_calculated",
            "lel_calculated",
            "report_generated",
        ]
        if state.get(key)
    ]
    return {
        "version": SNAPSHOT_VERSION,
        "soc": state.get("selected_soc"),
        "stage": state.get("current_state"),
        "completed_steps": completed,
        "sampling": sampling if isinstance(sampling, Mapping) else {},
        "gc_done": bool(state.get("gc_finished")),
        "lfl_done": bool(state.get("lel_calculated") or state.get("lel_risk_evaluated")),
        "report_done": bool(state.get("report_generated") or state.get("current_state") == "report_generated"),
    }


def _status_visual(status: str) -> dict[str, str]:
    if status == "alert":
        return {"stroke": "#c62828", "fill": "#ff9f43", "label": "安全提醒"}
    if status == "warning":
        return {"stroke": "#c05621", "fill": "#f2c94c", "label": "流程提醒"}
    if status == "complete":
        return {"stroke": "#2e7d32", "fill": "#35d0df", "label": "完成鼓励"}
    if status == "tip":
        return {"stroke": "#1565c0", "fill": "#35d0df", "label": "学习提示"}
    return {"stroke": "#00838f", "fill": "#2e7d32", "label": "待机"}


def _render_component_html(
    *,
    component_id: str,
    context: dict[str, str],
    visual: dict[str, str],
    history: list[dict[str, str]],
    latest_question: str,
    latest_answer: str,
    process_advice: dict[str, str],
    local_answers: dict[str, str],
    quick: list[str],
    evaluation_markdown: str,
    trace_json: str,
    progress_snapshot: dict[str, Any] | None = None,
) -> str:
    payload = {
        "componentId": component_id,
        "context": context,
        "visual": visual,
        "history": history,
        "latestQuestion": latest_question,
        "latestAnswer": latest_answer,
        "processAdvice": process_advice,
        "localAnswers": local_answers,
        "quick": quick,
        "evaluationMarkdown": evaluation_markdown,
        "traceJson": trace_json,
        "progressSnapshot": progress_snapshot or {},
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    stroke = html.escape(visual["stroke"])
    fill = html.escape(visual["fill"])
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<style>
html, body {{ margin:0; padding:0; width:0; height:0; overflow:hidden; background:transparent; }}
</style>
</head>
<body>
<style id="floatingAiCompanionStyleSource">
.floating-ai-root {{ position: fixed; left: auto; right: 24px; bottom: 24px; z-index: 2147483000; color: #213547; user-select: none; font-family: "Microsoft YaHei", Arial, sans-serif; }}
.floating-ai-root.dragging, .floating-ai-root.dragging * {{ user-select: none; cursor: grabbing !important; }}
.floating-ai-pet {{ width:64px; height:64px; border:0; padding:0; border-radius:18px; background:#fff; box-shadow:0 8px 14px rgba(11,58,99,.16); cursor:grab; display:grid; place-items:center; touch-action:none; }}
.floating-ai-pet:hover {{ box-shadow:0 10px 16px rgba(11,58,99,.2); }}
.floating-ai-pet:focus-visible {{ outline: 3px solid rgba(21,101,192,.28); outline-offset: 3px; }}
.floating-ai-status {{ position:absolute; right:-2px; top:-2px; min-width:18px; height:18px; border-radius:999px; background:#fff; border:2px solid var(--floating-ai-stroke); box-sizing:border-box; }}
.floating-ai-panel {{ position:absolute; right:76px; bottom:0; width:min(390px, calc(100vw - 104px)); max-height:min(680px, calc(100vh - 40px)); display:none; overflow:hidden; border:1px solid #d9e4ef; border-radius:14px; background:#fff; box-shadow:0 10px 18px rgba(11,58,99,.18); }}
.floating-ai-root.panel-right .floating-ai-panel {{ right:auto; left:76px; }}
.floating-ai-panel.open {{ display:flex; flex-direction:column; }}
.floating-ai-head {{ display:flex; gap:10px; align-items:center; padding:10px 12px; background:#f8fbfe; border-bottom:1px solid #d9e4ef; }}
.floating-ai-titlebox {{ min-width:0; display:flex; align-items:center; gap:8px; }}
.floating-ai-title {{ font-weight:850; color:#0b3a63; font-size:15px; line-height:1.25; }}
.floating-ai-online {{ width:8px; height:8px; border-radius:999px; background:var(--floating-ai-stroke); box-shadow:0 0 0 3px rgba(21,101,192,.12); flex:0 0 auto; transition: background .4s; }}.floating-ai-online.connected {{ background:#2e7d32; box-shadow:0 0 0 3px rgba(46,125,50,.18); }}.floating-ai-online.fallback {{ background:#e6a817; box-shadow:0 0 0 3px rgba(230,168,23,.18); }}.floating-ai-online.offline {{ background:#c62828; box-shadow:0 0 0 3px rgba(198,40,40,.18); }}
.floating-ai-meta, .floating-ai-tip {{ display:none; }}
.floating-ai-actions {{ margin-left:auto; display:flex; gap:6px; }}
.floating-ai-iconbtn {{ border:1px solid #d9e4ef; background:#fff; border-radius:8px; min-width:30px; height:30px; cursor:pointer; color:#213547; font-size:16px; line-height:1; }}
.floating-ai-iconbtn:hover, .floating-ai-menu button:hover, .floating-ai-menu a:hover, .floating-ai-quick button:hover {{ background:#eef6ff; }}
.floating-ai-body {{ padding:10px 12px; overflow:auto; min-height:0; }}
.floating-ai-mode, .floating-ai-advice {{ display:none; }}
.floating-ai-quick {{ display:flex; flex-wrap:wrap; gap:6px; margin-bottom:9px; }}
.floating-ai-quick button {{ border:1px solid #d9e4ef; background:#f8fbfe; border-radius:999px; padding:6px 9px; font-size:12px; color:#213547; cursor:pointer; min-height:32px; }}
.floating-ai-chat {{ max-height:min(360px, calc(100vh - 220px)); overflow:auto; padding-right:3px; }}
.floating-ai-msg {{ border:1px solid #d9e4ef; border-radius:10px; padding:9px 10px; margin:7px 0; white-space:pre-wrap; font-size:13px; line-height:1.58; }}
.floating-ai-msg.user {{ background:#eef6ff; margin-left:18px; }}
.floating-ai-msg.assistant {{ background:#f8fbfe; margin-right:18px; }}
.floating-ai-history {{ display:none; margin-top:8px; max-height:160px; overflow:auto; border-top:1px solid #d9e4ef; padding-top:6px; }}
.floating-ai-history.show {{ display:block; }}
.floating-ai-label {{ color:#536879; font-size:11px; font-weight:800; margin-bottom:3px; }}
.floating-ai-form {{ display:flex; gap:7px; padding:10px 12px 12px; border-top:1px solid #d9e4ef; background:#fff; }}
.floating-ai-input {{ flex:1; resize:none; min-height:42px; max-height:92px; border:1px solid #d9e4ef; border-radius:10px; padding:9px 10px; font:14px/1.45 "Microsoft YaHei", Arial, sans-serif; color:#213547; }}
.floating-ai-input::placeholder {{ color:#66798a; opacity:1; }}
.floating-ai-send {{ border:1px solid #1565c0; background:#1565c0; color:#fff; border-radius:10px; padding:0 15px; cursor:pointer; font-weight:700; min-width:58px; }}
.floating-ai-send:disabled {{ opacity:.65; cursor:wait; }}
.floating-ai-menu {{ display:none; flex-wrap:wrap; gap:7px; padding:0 12px 10px; border-top:1px solid #eef3f8; }}
.floating-ai-menu.show {{ display:flex; }}
.floating-ai-menu button, .floating-ai-menu a {{ border:1px solid #d9e4ef; background:#fff; color:#213547; border-radius:9px; padding:7px 9px; font-size:12px; text-decoration:none; cursor:pointer; min-height:32px; }}
.floating-ai-toast {{ display:none; margin:8px 12px 0; padding:7px 9px; border:1px solid #d9e4ef; border-radius:9px; background:#fff8e1; color:#6a4b00; font-size:12px; line-height:1.45; }}
.floating-ai-toast.show {{ display:block; }}
.floating-ai-restore {{ display:none; margin:8px 12px 0; padding:8px 9px; border:1px solid #d9e4ef; border-radius:9px; background:#f8fbfe; font-size:12px; line-height:1.45; }}
.floating-ai-restore.show {{ display:block; }}
.floating-ai-restore button {{ margin-left:6px; border:1px solid #d9e4ef; border-radius:8px; background:#fff; color:#213547; min-height:30px; cursor:pointer; }}
.floating-ai-eval {{ display:none; margin-top:9px; max-height:220px; overflow:auto; border:1px solid #d9e4ef; background:#f8fbfe; border-radius:10px; padding:8px; white-space:pre-wrap; font-size:12px; line-height:1.55; }}
.floating-ai-eval.show {{ display:block; }}
.pet-wrap {{ animation: pet-float 3.2s ease-in-out infinite; }}
.pet-eye {{ animation: pet-blink 5s infinite; transform-origin:center; }}
@keyframes pet-float {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-4px); }} }}
@keyframes pet-blink {{ 0%, 92%, 100% {{ transform: scaleY(1); }} 95% {{ transform: scaleY(.1); }} }}
@media (max-width: 760px) {{
  .floating-ai-root {{ right: 12px; bottom: 12px; }}
  .floating-ai-panel {{ right:0; left:auto; bottom:76px; width:calc(100vw - 24px); }}
  .floating-ai-root.panel-right .floating-ai-panel {{ right:0; left:auto; }}
}}
@media (min-width: 900px) and (max-width: 1400px) {{
  .floating-ai-pet {{ width:68px; height:68px; }}
  .floating-ai-panel {{ width:min(430px, calc(100vw - 112px)); max-height:calc(100vh - 32px); }}
  .floating-ai-chat {{ max-height:min(420px, calc(100vh - 230px)); }}
  .floating-ai-input {{ font-size:15px; min-height:46px; }}
  .floating-ai-send, .floating-ai-iconbtn {{ min-height:36px; }}
}}
@media (prefers-reduced-motion: reduce) {{ .pet-wrap, .pet-eye {{ animation:none; }} }}
</style>
<template id="floatingAiCompanionTemplate">
  <div class="floating-ai-root" style="--floating-ai-stroke:{stroke}">
    <button class="floating-ai-pet" data-el="pet" aria-label="打开电池实验 AI 学伴" title="拖动移动，点击提问">
      <span class="pet-wrap">
        <svg width="56" height="56" viewBox="0 0 92 78" aria-hidden="true">
          <rect x="18" y="18" width="54" height="40" rx="13" fill="#fff" stroke="{stroke}" stroke-width="4"/>
          <rect x="73" y="31" width="8" height="14" rx="4" fill="{stroke}"/>
          <circle cx="28" cy="15" r="4" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
          <circle cx="62" cy="15" r="4" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
          <path d="M28 19 L30 24 M62 19 L60 24" stroke="{stroke}" stroke-width="2" stroke-linecap="round"/>
          <rect x="25" y="26" width="34" height="20" rx="8" fill="{fill}" opacity=".22"/>
          <circle class="pet-eye" cx="35" cy="37" r="3" fill="#213547"/>
          <circle class="pet-eye" cx="54" cy="37" r="3" fill="#213547"/>
          <path d="M36 47 Q45 52 54 47" fill="none" stroke="#213547" stroke-width="3" stroke-linecap="round"/>
          <path d="M66 14 L61 25 H68 L63 36" fill="none" stroke="{fill}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
      <span class="floating-ai-status" data-el="status"></span>
    </button>
    <section class="floating-ai-panel" data-el="panel" aria-label="电池实验 AI 学伴聊天窗">
      <div class="floating-ai-head">
        <div class="floating-ai-titlebox">
          <span class="floating-ai-online" data-el="online"></span>
          <div class="floating-ai-title">电池实验 AI 学伴</div>
          <div class="floating-ai-meta" data-el="meta"></div>
          <div class="floating-ai-tip" data-el="tip"></div>
        </div>
        <div class="floating-ai-actions">
          <button class="floating-ai-iconbtn" type="button" data-el="more" title="更多">⋯</button>
          <button class="floating-ai-iconbtn" type="button" data-el="min" title="最小化">－</button>
          <button class="floating-ai-iconbtn" type="button" data-el="close" title="关闭">×</button>
        </div>
      </div>
      <div class="floating-ai-toast" data-el="toast"></div>
      <div class="floating-ai-restore" data-el="restore">
        检测到未完成实验，是否恢复进度？
        <button type="button" data-el="restoreYes">恢复</button>
        <button type="button" data-el="restoreNo">忽略</button>
      </div>
      <div class="floating-ai-body">
        <div class="floating-ai-mode" data-el="mode"></div>
        <div class="floating-ai-advice" data-el="advice"></div>
        <div class="floating-ai-quick" data-el="quick"></div>
        <div class="floating-ai-chat" data-el="chat"></div>
        <div class="floating-ai-history" data-el="history"></div>
        <div class="floating-ai-eval" data-el="eval"></div>
      </div>
      <div class="floating-ai-menu" data-el="menu">
        <button type="button" data-el="modeBtn">查看当前模式</button>
        <button type="button" data-el="historyBtn">查看历史记录</button>
        <button type="button" data-el="evalBtn">生成学习评价</button>
        <a data-el="evalDownload" download="电池实验AI学伴学习评价清单.md">下载评价 Markdown</a>
        <a data-el="jsonDownload" download="电池实验AI学伴学习记录.json">导出学习记录 JSON</a>
        <button type="button" data-el="restart">重新开始实验</button>
        <button type="button" data-el="end">结束本轮对话</button>
        <button type="button" data-el="clear">清空历史</button>
      </div>
      <form class="floating-ai-form" data-el="form">
        <textarea class="floating-ai-input" data-el="input" placeholder="随时问：T2=100℃ 为什么要采样？"></textarea>
        <button class="floating-ai-send" data-el="send" type="submit">发送</button>
      </form>
    </section>
  </div>
</template>
<script>
(function() {{
  const data = {payload_json};
  const parentWindow = window.parent;
  const parentDocument = parentWindow.document;
  const styleId = 'floating-ai-companion-style-v2';
  const rootId = 'floatingAiRoot-' + String(data.componentId || 'global').replace(/[^a-zA-Z0-9_-]/g, '');
  const positionKey = 'floating-ai-companion-position-v2';
  const openKey = 'floating-ai-companion-open-v2';
  const snapshotKey = 'battery-lab-progress-snapshot-v1';

  function ensureStyle() {{
    const css = document.getElementById('floatingAiCompanionStyleSource').textContent;
    let style = parentDocument.getElementById(styleId);
    if (!style) {{
      style = parentDocument.createElement('style');
      style.id = styleId;
      parentDocument.head.appendChild(style);
    }}
    style.textContent = css;
  }}

  function mountRoot() {{
    const previous = parentDocument.getElementById(rootId);
    if (previous) previous.remove();
    const template = document.getElementById('floatingAiCompanionTemplate');
    const root = template.content.firstElementChild.cloneNode(true);
    root.id = rootId;
    parentDocument.body.appendChild(root);
    return root;
  }}

  ensureStyle();
  mountRoot();
  const bootId = rootId + '-script';
  const previousBoot = parentDocument.getElementById(bootId);
  if (previousBoot) previousBoot.remove();
  const boot = parentDocument.createElement('script');
  boot.id = bootId;
  boot.textContent = '(' + function(payload, mountedRootId, positionStorageKey, openStorageKey, progressSnapshotKey) {{
    const root = document.getElementById(mountedRootId);
    if (!root) return;
    const $ = (name) => root.querySelector(`[data-el="${{name}}"]`);
    const pet = $('pet');
    const panel = $('panel');
    const meta = $('meta');
    const tip = $('tip');
    const mode = $('mode');
    const advice = $('advice');
    const quick = $('quick');
    const chat = $('chat');
    const history = $('history');
    const input = $('input');
    const form = $('form');
    const send = $('send');
    const evalBox = $('eval');
    const evalBtn = $('evalBtn');
    const evalDownload = $('evalDownload');
    const jsonDownload = $('jsonDownload');
    const historyBtn = $('historyBtn');
    const modeBtn = $('modeBtn');
    const menu = $('menu');
    const toast = $('toast');
    const restore = $('restore');
    const restoreYes = $('restoreYes');
    const restoreNo = $('restoreNo');
    const moreBtn = $('more');
    const clearBtn = $('clear');
    const endBtn = $('end');
    const restartBtn = $('restart');
    const minBtn = $('min');
    const closeBtn = $('close');
    let dragging = false, moved = false, sending = false, lastSubmitted = '', startX = 0, startY = 0, startLeft = 0, startTop = 0, sendingTimeoutId = 0;

    function esc(s) {{ return String(s || '').replace(/[&<>"']/g, m => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m])); }}
    function clamp(n, min, max) {{ return Math.max(min, Math.min(max, n)); }}
    function viewportWidth() {{ return window.innerWidth || document.documentElement.clientWidth || 1024; }}
    function viewportHeight() {{ return window.innerHeight || document.documentElement.clientHeight || 768; }}

    function applySavedPosition() {{
      try {{
        const saved = JSON.parse(localStorage.getItem(positionStorageKey) || 'null');
        if (saved && Number.isFinite(saved.left) && Number.isFinite(saved.top)) {{
          root.style.left = clamp(saved.left, 8, viewportWidth() - 76) + 'px';
          root.style.top = clamp(saved.top, 8, viewportHeight() - 76) + 'px';
          root.style.right = 'auto';
          root.style.bottom = 'auto';
        }}
      }} catch (e) {{}}
    }}

    function savePosition() {{
      const r = root.getBoundingClientRect();
      localStorage.setItem(positionStorageKey, JSON.stringify({{ left: Math.round(r.left), top: Math.round(r.top) }}));
    }}

    function repositionIntoViewport() {{
      const r = root.getBoundingClientRect();
      const left = clamp(r.left, 8, viewportWidth() - 76);
      const top = clamp(r.top, 8, viewportHeight() - 76);
      if (left !== r.left || top !== r.top) {{
        root.style.left = left + 'px';
        root.style.top = top + 'px';
        root.style.right = 'auto';
        root.style.bottom = 'auto';
        savePosition();
      }}
      placePanel();
    }}

    function placePanel() {{
      const r = root.getBoundingClientRect();
      root.classList.toggle('panel-right', r.left < 410);
    }}

    function setPanelOpen(open) {{
      panel.classList.toggle('open', open);
      localStorage.setItem(openStorageKey, open ? '1' : '0');
      if (open) placePanel();
    }}

    function render() {{
      // Clear the sending timeout guard — fresh data arrived from backend
      if (sendingTimeoutId) {{ window.clearTimeout(sendingTimeoutId); sendingTimeoutId = 0; }}
      sending = false;
      send.disabled = false;
      const c = payload.context;
      // Update connection status indicator
      const online = $('online');
      online.className = 'floating-ai-online';
      if (c.mode.indexOf('DeepSeek') !== -1 || c.mode.indexOf('外接') !== -1) {{
        online.classList.add('connected');
        online.title = 'AI 服务已连接';
      }} else if (c.mode.indexOf('兜底') !== -1 || c.mode.indexOf('回退') !== -1) {{
        online.classList.add('fallback');
        online.title = '已切换到本地知识模式';
      }} else {{
        online.classList.add('offline');
        online.title = 'AI 服务未连接';
      }}
      meta.textContent = `页面：${{c.page_name}} · 阶段：${{c.current_stage}} · SOC：${{c.current_soc}}`;
      tip.textContent = c.stage_tip || '';
      mode.textContent = `当前模式：${{c.mode}}`;
      advice.textContent = payload.processAdvice.next_step_suggestion || c.stage_tip || '我会根据当前进度给出下一步建议。';
      quick.innerHTML = '';
      (payload.quick || []).slice(0, 3).forEach((q) => {{
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = q;
        btn.addEventListener('click', () => answerQuestion(q));
        quick.appendChild(btn);
      }});
      renderCurrent(payload.latestQuestion || '', payload.latestAnswer || '');
      renderHistory(payload.history || []);
      setDownload(evalDownload, payload.evaluationMarkdown || '请先在更多菜单中点击“生成学习评价”。', 'text/markdown');
      setDownload(jsonDownload, payload.traceJson || '{{}}', 'application/json');
      if (payload.evaluationMarkdown) {{
        evalBox.textContent = payload.evaluationMarkdown;
        evalBox.classList.add('show');
      }}
      if (localStorage.getItem(openStorageKey) === '1') setPanelOpen(true);
      maybePromptRestore();
      persistProgressSnapshot();
    }}

    function renderCurrent(question, answer) {{
      chat.innerHTML = '';
      if (!question && !answer) {{
        const empty = document.createElement('div');
        empty.className = 'floating-ai-msg assistant';
        empty.innerHTML = '<div class="floating-ai-label">AI 学伴</div>' + esc('你好，我可以陪你完成实验、解释原理，也可以回答其他学习问题。');
        chat.appendChild(empty);
        return;
      }}
      if (question) {{
        const user = document.createElement('div');
        user.className = 'floating-ai-msg user';
        user.innerHTML = `<div class="floating-ai-label">你</div>${{esc(question)}}`;
        chat.appendChild(user);
      }}
      if (answer) {{
        const assistant = document.createElement('div');
        assistant.className = 'floating-ai-msg assistant';
        assistant.innerHTML = `<div class="floating-ai-label">AI 学伴</div>${{esc(answer)}}`;
        chat.appendChild(assistant);
      }}
      chat.scrollTop = chat.scrollHeight;
    }}

    function renderHistory(items) {{
      history.innerHTML = '';
      items.forEach(item => {{
        const div = document.createElement('div');
        div.className = 'floating-ai-msg ' + (item.role === 'user' ? 'user' : 'assistant');
        div.innerHTML = `<div class="floating-ai-label">${{item.role === 'user' ? '你' : 'AI 学伴'}}</div>${{esc(item.content)}}`;
        history.appendChild(div);
      }});
    }}

    function setDownload(anchor, text, mime) {{
      const blob = new Blob([text], {{ type: mime + ';charset=utf-8' }});
      const old = anchor.dataset.url;
      if (old) URL.revokeObjectURL(old);
      const url = URL.createObjectURL(blob);
      anchor.href = url;
      anchor.dataset.url = url;
    }}

    function showToast(text, timeout = 2800) {{
      if (!toast) return;
      toast.textContent = text;
      toast.classList.add('show');
      window.setTimeout(() => toast.classList.remove('show'), timeout);
    }}

    function hasUsefulSnapshot(snapshot) {{
      return snapshot && snapshot.version === 1 && (snapshot.stage || snapshot.soc || (snapshot.completed_steps || []).length);
    }}

    function persistProgressSnapshot() {{
      try {{
        const snapshot = payload.progressSnapshot || {{}};
        if (hasUsefulSnapshot(snapshot)) {{
          const saved = getSavedSnapshot();
          const savedCount = saved && Array.isArray(saved.completed_steps) ? saved.completed_steps.length : 0;
          const currentCount = Array.isArray(snapshot.completed_steps) ? snapshot.completed_steps.length : 0;
          if (saved && savedCount > currentCount && !snapshot.report_done) return;
          localStorage.setItem(progressSnapshotKey, JSON.stringify({{ ...snapshot, saved_at: new Date().toISOString() }}));
        }}
      }} catch (e) {{}}
    }}

    function getSavedSnapshot() {{
      try {{
        const saved = JSON.parse(localStorage.getItem(progressSnapshotKey) || 'null');
        return hasUsefulSnapshot(saved) ? saved : null;
      }} catch (e) {{
        return null;
      }}
    }}

    function maybePromptRestore() {{
      const saved = getSavedSnapshot();
      if (!saved || sessionStorage.getItem(progressSnapshotKey + ':dismissed') === '1') return;
      const current = payload.progressSnapshot || {{}};
      const differs = String(saved.stage || '') !== String(current.stage || '') || String(saved.soc || '') !== String(current.soc || '');
      if (differs) restore.classList.add('show');
    }}

    function postEvent(eventType, extra) {{
      try {{
        const bridgeFrame = Array.from(document.querySelectorAll('iframe'))
          .find(frame => String(frame.title || '').includes('floating_ai_companion_bridge'));
        if (!bridgeFrame || !bridgeFrame.contentWindow) return false;
        bridgeFrame.contentWindow.postMessage({{
          kind: 'floating-ai-event',
          eventType,
          componentId: payload.componentId,
          ...(extra || {{}})
        }}, '*');
        return true;
      }} catch (e) {{
        return false;
      }}
    }}

    function pickLocalAnswer(question) {{
      const q = String(question || '').toLowerCase();
      const answers = payload.localAnswers || {{}};
      const entries = [
        ['下一步', 'next_step'],
        ['应该做', 'next_step'],
        ['怎么继续', 'next_step'],
        ['t2', 't2_sampling'],
        ['100', 't2_sampling'],
        ['lfl', 'lfl_mix'],
        ['防爆', 'lfl_mix'],
        ['报告', 'report_source'],
        ['报警', 'alarm'],
        ['soc', 'soc'],
        ['喷阀', 'venting']
      ];
      for (const [needle, key] of entries) {{
        if (q.includes(needle) && answers[key]) return answers[key];
      }}
      return answers.default_answer || '这个问题我会先按本地规则解释：请把问题限定在 SOC、四次采样、GC 组分、LFL_mix、报警理由或报告数据来源范围内。注意：这是虚拟仿真教学解释，不是真实实验操作建议。';
    }}

    function persistLocalHistory(question, answer) {{
      try {{
        const key = 'floating-ai-companion-backend-history-v2-' + payload.componentId;
        const historyItems = JSON.parse(localStorage.getItem(key) || '[]');
        historyItems.push({{ role: 'user', content: question }}, {{ role: 'assistant', content: answer, mode: payload.context.mode }});
        localStorage.setItem(key, JSON.stringify(historyItems.slice(-80)));
      }} catch (e) {{}}
    }}

    function submitToBackend(question) {{
      try {{
        sending = true;
        send.disabled = true;
        renderCurrent(question, '正在生成回答...');
        // Retry postMessage up to 3 times with backoff delays
        var retries = 0;
        var maxPostRetries = 3;
        var delays = [200, 500, 1000];
        function tryPost() {{
          if (postEvent('question', {{ question }})) {{
            // Keep this longer than the backend request timeout plus retries to avoid false timeout hints.
            sendingTimeoutId = window.setTimeout(function() {{
              if (sending) {{
                sending = false;
                send.disabled = false;
                showToast('AI 响应超时，请重试。发送按钮已自动复位。', 4200);
              }}
            }}, 45000);
            return true;
          }}
          retries++;
          if (retries < maxPostRetries) {{
            window.setTimeout(tryPost, delays[retries - 1]);
          }} else {{
            showToast('AI 通信暂时不可达，已使用本地知识回答。', 3200);
            answerLocally(question);
          }}
          return false;
        }}
        tryPost();
        return true;
      }} catch (e) {{
        showToast('发送失败，已使用本地知识回答。', 3200);
        answerLocally(question);
        return false;
      }}
    }}

    function answerLocally(question) {{
      setPanelOpen(true);
      sending = false;
      send.disabled = false;
      const answer = pickLocalAnswer(question);
      showToast('当前使用本地知识库回答。', 2500);
      payload.latestQuestion = question;
      payload.latestAnswer = answer;
      payload.history = (payload.history || []).concat([
        {{ role: 'user', content: question }},
        {{ role: 'assistant', content: answer, mode: payload.context.mode }}
      ]).slice(-80);
      renderCurrent(question, answer);
      renderHistory(payload.history);
      persistLocalHistory(question, answer);
    }}

    function answerQuestion(question) {{
      setPanelOpen(true);
      if (sending || question === lastSubmitted) return;
      lastSubmitted = question;
      if (submitToBackend(question)) return;
      answerLocally(question);
    }}

    pet.addEventListener('pointerdown', (e) => {{
      dragging = true;
      moved = false;
      root.classList.add('dragging');
      pet.setPointerCapture(e.pointerId);
      const r = root.getBoundingClientRect();
      startX = e.clientX;
      startY = e.clientY;
      startLeft = r.left;
      startTop = r.top;
    }});

    pet.addEventListener('pointermove', (e) => {{
      if (!dragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
      root.style.left = clamp(startLeft + dx, 8, viewportWidth() - 76) + 'px';
      root.style.top = clamp(startTop + dy, 8, viewportHeight() - 76) + 'px';
      root.style.right = 'auto';
      root.style.bottom = 'auto';
      placePanel();
    }});

    pet.addEventListener('pointerup', () => {{
      dragging = false;
      root.classList.remove('dragging');
      savePosition();
      if (!moved) setPanelOpen(true);
    }});

    form.addEventListener('submit', (e) => {{
      e.preventDefault();
      const q = input.value.trim();
      if (!q) return;
      input.value = '';
      answerQuestion(q);
    }});

    input.addEventListener('keydown', (e) => {{
      if (e.key === 'Enter' && !e.shiftKey) {{
        e.preventDefault();
        form.requestSubmit();
      }}
    }});

    evalBtn.addEventListener('click', () => {{
      if (!payload.evaluationMarkdown) {{
        if (postEvent('generate_evaluation')) {{
          showToast('正在生成学习评价...');
          return;
        }}
      }}
      evalBox.textContent = payload.evaluationMarkdown || '请稍后再试。';
      evalBox.classList.add('show');
    }});
    jsonDownload.addEventListener('click', (e) => {{
      if (!payload.traceJson) {{
        e.preventDefault();
        if (postEvent('export_trace')) showToast('正在准备学习记录 JSON...');
      }}
    }});
    restoreYes.addEventListener('click', () => {{
      const saved = getSavedSnapshot();
      if (saved && postEvent('restore_snapshot', {{ snapshot: saved }})) {{
        restore.classList.remove('show');
        showToast('正在恢复实验进度...');
      }}
    }});
    restoreNo.addEventListener('click', () => {{
      sessionStorage.setItem(progressSnapshotKey + ':dismissed', '1');
      restore.classList.remove('show');
    }});
    moreBtn.addEventListener('click', () => menu.classList.toggle('show'));
    modeBtn.addEventListener('click', () => showToast('当前模式：' + payload.context.mode, 3600));
    historyBtn.addEventListener('click', () => history.classList.toggle('show'));
    endBtn.addEventListener('click', () => {{
      renderCurrent('', '本轮对话已结束。后台问答记录仍会保留，再次输入即可继续。');
      setPanelOpen(false);
    }});
    restartBtn.addEventListener('click', () => {{
      if (window.confirm('确认重新开始实验？当前浏览器进度快照会被清除。')) {{
        try {{ localStorage.removeItem(progressSnapshotKey); }} catch (e) {{}}
        postEvent('restart_experiment');
        showToast('已清除进度快照。');
      }}
    }});
    clearBtn.addEventListener('click', () => {{
      if (window.confirm('确认清空 AI 聊天历史？不会清空实验进度。')) {{
        payload.history = [];
        payload.latestQuestion = '';
        payload.latestAnswer = '';
        try {{ localStorage.removeItem('floating-ai-companion-backend-history-v2-' + payload.componentId); }} catch (e) {{}}
        renderCurrent('', '');
        renderHistory([]);
      }}
    }});
    minBtn.addEventListener('click', () => setPanelOpen(false));
    closeBtn.addEventListener('click', () => setPanelOpen(false));
    window.addEventListener('resize', repositionIntoViewport);
    applySavedPosition();
    render();
    repositionIntoViewport();
  }}.toString() + ')('
    + JSON.stringify(data).replace(/</g, '\\u003c') + ','
    + JSON.stringify(rootId) + ','
    + JSON.stringify(positionKey) + ','
    + JSON.stringify(openKey) + ','
    + JSON.stringify(snapshotKey) + ');';
  parentDocument.body.appendChild(boot);
  boot.remove();
}})();
</script>
</body>
</html>"""


def _sync_history_to_learning_trace(history: list[dict[str, str]]) -> None:
    """Ensure chat messages are reflected in the objective learning trace."""

    trace = get_learning_trace()
    existing_questions = {str(item.get("question", "")) for item in trace.get("qa_events", [])}
    for index, item in enumerate(history):
        if item.get("role") != "user":
            continue
        question = str(item.get("content", "")).strip()
        if not question or question in existing_questions:
            continue
        answer = ""
        if index + 1 < len(history) and history[index + 1].get("role") == "assistant":
            answer = str(history[index + 1].get("content", ""))
        record_qa(question=question, answer=answer)
        existing_questions.add(question)


def ensure_ai_companion_state(key_prefix: str) -> dict[str, Any]:
    """Create isolated AI companion state without touching experiment state."""

    history_key = _state_key(key_prefix, "history")
    st.session_state.setdefault(history_key, [])
    st.session_state.setdefault(_state_key(key_prefix, "latest_question"), "")
    st.session_state.setdefault(_state_key(key_prefix, "latest_answer"), "")
    st.session_state.setdefault(_state_key(key_prefix, "latest_mode"), current_chat_mode())
    st.session_state.setdefault(_state_key(key_prefix, "evaluation_markdown"), "")
    return {
        "history": st.session_state[history_key],
        "latest_question": st.session_state[_state_key(key_prefix, "latest_question")],
        "latest_answer": st.session_state[_state_key(key_prefix, "latest_answer")],
        "latest_mode": st.session_state[_state_key(key_prefix, "latest_mode")],
        "evaluation_markdown": st.session_state[_state_key(key_prefix, "evaluation_markdown")],
    }


def handle_ai_question_event(
    *,
    key_prefix: str,
    question: str,
    context: AssistantContext,
    page_name: str,
    experiment_context: Mapping[str, Any] | None,
    process_advice: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Handle an AI question without mutating experiment progress state."""

    value = str(question or "").strip()
    if not value:
        return {"answer": "", "mode": current_chat_mode(), "used_external": False}

    history_key = _state_key(key_prefix, "history")
    st.session_state.setdefault(history_key, [])
    result = answer_with_optional_llm(value, context, trace_summary=_trace_summary(), process_advice=process_advice)
    answer = result["answer"]
    st.session_state[_state_key(key_prefix, "latest_question")] = value
    st.session_state[_state_key(key_prefix, "latest_answer")] = answer
    st.session_state[_state_key(key_prefix, "latest_mode")] = result["mode"]
    st.session_state[history_key].append({"role": "user", "content": value})
    st.session_state[history_key].append({"role": "assistant", "content": answer, "mode": result["mode"]})
    st.session_state[history_key] = st.session_state[history_key][-HISTORY_LIMIT:]
    record_qa(question=value, answer=answer)
    record_operation(
        page_name=page_name,
        action_type="assistant",
        action_name="ask_question",
        experiment_state=experiment_context,
        ok=True,
    )
    return result


def generate_learning_evaluation_for_companion(
    *,
    key_prefix: str,
    page_name: str,
    experiment_context: Mapping[str, Any] | None,
) -> str:
    history_key = _state_key(key_prefix, "history")
    _sync_history_to_learning_trace(st.session_state.get(history_key, []))
    evaluation = evaluate_learning(get_learning_trace())
    supplement = get_external_llm_supplement(evaluation)
    markdown = evaluation["markdown"]
    if supplement.get("message"):
        markdown += f"\n\n> {supplement['message']}\n"
    st.session_state[_state_key(key_prefix, "evaluation_markdown")] = markdown
    record_operation(
        page_name=page_name,
        action_type="assistant",
        action_name="generate_learning_evaluation",
        experiment_state=experiment_context,
        ok=True,
    )
    return markdown


def build_learning_evaluation_snapshot() -> str:
    """Build a read-only evaluation snapshot for lightweight front-end display."""

    evaluation = evaluate_learning(get_learning_trace())
    supplement = get_external_llm_supplement(evaluation)
    markdown = evaluation["markdown"]
    if supplement.get("message"):
        markdown += f"\n\n> {supplement['message']}\n"
    return markdown


def _fallback_notice_for_mode(mode: str) -> str:
    if not mode.startswith("本地规则兜底模式："):
        return ""
    if "未配置真实 DeepSeek Key" in mode:
        return "本地规则兜底模式：未配置真实 DeepSeek Key"
    if "鉴权失败" in mode:
        return "本地规则兜底模式：DeepSeek Key 鉴权失败"
    if "余额不足" in mode:
        return "本地规则兜底模式：DeepSeek 账户余额不足"
    if "网络超时" in mode:
        return "本地规则兜底模式：DeepSeek 网络超时"
    return "网络暂时不可用，已切换到本地知识模式。"


def _handle_bridge_event(
    *,
    key_prefix: str,
    event_type: str,
    question: str,
    snapshot: Mapping[str, Any] | None,
    context: AssistantContext,
    page_name: str,
    experiment_context: Mapping[str, Any] | None,
    process_advice: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Route front-end companion events without doing expensive work by default."""

    if event_type == "question":
        return handle_ai_question_event(
            key_prefix=key_prefix,
            question=question,
            context=context,
            page_name=page_name,
            experiment_context=experiment_context,
            process_advice=process_advice,
        )
    if event_type == "generate_evaluation":
        generate_learning_evaluation_for_companion(
            key_prefix=key_prefix,
            page_name=page_name,
            experiment_context=experiment_context,
        )
        return {"mode": current_chat_mode(), "used_external": False, "answer": ""}
    if event_type == "export_trace":
        st.session_state[_state_key(key_prefix, "trace_json")] = export_learning_trace_json(trace)
        record_operation(
            page_name=page_name,
            action_type="assistant",
            action_name="export_learning_trace_json",
            experiment_state=experiment_context,
            ok=True,
        )
        return {"mode": current_chat_mode(), "used_external": False, "answer": ""}
    if event_type == "restore_snapshot":
        restored = apply_progress_snapshot_to_session(snapshot or {})
        record_operation(
            page_name=page_name,
            action_type="assistant",
            action_name="restore_progress_snapshot",
            experiment_state=experiment_context,
            ok=restored,
        )
        if restored:
            st.toast("已恢复浏览器中的实验进度快照。")
        return {"mode": current_chat_mode(), "used_external": False, "answer": ""}
    if event_type == "restart_experiment":
        st.session_state.pop("interactive_experiment_last", None)
        st.session_state.pop("virtual_experiment_last", None)
        st.toast("已清除演示进度快照。")
        return {"mode": current_chat_mode(), "used_external": False, "answer": ""}
    return None


def render_floating_ai_companion(
    page_name: str,
    experiment_context: Mapping[str, Any] | None = None,
    *,
    assessment: Mapping[str, Any] | None = None,
    enable_drag: bool = True,
    default_position: str = "bottom-right",
    key_prefix: str = "global",
) -> None:
    """Render a draggable floating AI companion without occupying page layout."""

    del enable_drag, default_position
    ai_state = ensure_ai_companion_state(key_prefix)
    trace = get_learning_trace()
    update_learning_state_from_experiment(trace, experiment_context)
    sync_warnings_from_assessment(trace, assessment)
    context = build_assistant_context(page_name=page_name, experiment_state=experiment_context, assessment=assessment)
    process_advice = build_process_advice(page_name=page_name, experiment_state=experiment_context, trace=trace, assessment=assessment)
    status = "complete" if trace["learning_state"].get("report_generated") else assistant_status(context)
    if status == "idle" and context.current_soc != "未选择":
        status = "tip"
    visual = _status_visual(status)
    evaluation_markdown = st.session_state.get(_state_key(key_prefix, "evaluation_markdown"), "")
    trace_json = st.session_state.get(_state_key(key_prefix, "trace_json"), "")
    bridge_event = _BRIDGE_COMPONENT(component_id=key_prefix, default=None, key=_state_key(key_prefix, "bridge"))
    if isinstance(bridge_event, Mapping):
        bridge_nonce_key = _state_key(key_prefix, "last_bridge_nonce")
        bridge_nonce = str(bridge_event.get("nonce", ""))
        event_type = str(bridge_event.get("event_type", "question") or "question")
        bridge_question = str(bridge_event.get("question", "")).strip()
        bridge_snapshot = bridge_event.get("snapshot")
        should_handle = bool(bridge_nonce and st.session_state.get(bridge_nonce_key) != bridge_nonce)
    else:
        bridge_nonce_key = _state_key(key_prefix, "last_bridge_nonce")
        bridge_nonce = ""
        event_type = ""
        bridge_question = ""
        bridge_snapshot = None
        should_handle = False
    if should_handle:
        st.session_state[bridge_nonce_key] = bridge_nonce
        result = _handle_bridge_event(
            key_prefix=key_prefix,
            event_type=event_type,
            question=bridge_question,
            snapshot=bridge_snapshot if isinstance(bridge_snapshot, Mapping) else None,
            context=context,
            page_name=page_name,
            experiment_context=experiment_context,
            process_advice=process_advice,
            trace=trace,
        )
        if result:
            notice = _fallback_notice_for_mode(str(result.get("mode", "")))
            if notice:
                st.toast(notice)
        ai_state = ensure_ai_companion_state(key_prefix)
        evaluation_markdown = st.session_state.get(_state_key(key_prefix, "evaluation_markdown"), "")
        trace_json = st.session_state.get(_state_key(key_prefix, "trace_json"), "")
    local_answers = {
        "next_step": process_advice["next_step_suggestion"],
        "t2_sampling": "结论：T2=100℃ 是第一次采气节点，用来记录早期受热阶段的气体组成。原因：此时尚未进入明显喷阀或温度峰值阶段，样本可用于和后续喷阀、峰值、压力稳定阶段比较。注意：这是虚拟仿真教学解释，不是真实实验操作指导。",
        "lfl_mix": "结论：LFL_mix 是混合气体可燃下限的教学估算结果，不能作为工程防爆设计或消防处置依据。原因：平台采用 Le Chatelier 混合规则和均匀混合等简化假设，只服务课堂比较。真实工程需要标准、实测、边界条件和合规人员判断。",
        "report_source": "结论：报告中参考文献部分来自已整理的实验对象、采样节点、SOC 影响和气体事实；教学演示数据、空间浓度、LFL_mix 和风险比值来自平台计算或用户输入。生成报告前建议检查数据来源和模型局限。",
        "alarm": "结论：报警通常来自流程前置条件、采样节点或教学边界校验。请先看报警理由，再按当前步骤补齐前置条件。所有报警只服务虚拟仿真教学，不是真实工程处置建议。",
        "soc": "结论：SOC 会影响热失控强度和产气风险。一般来说 SOC 越高，最高温度、温升速率和可燃气体浓度在教学数据中越突出。0%SOC 可喷阀，但喷阀不等于一定发生热失控。",
        "venting": "结论：安全阀喷阀是第二次采样节点，但不等于必然热失控。它说明电池内部压力释放，后续仍需观察温度峰值和压力稳定节点。",
        "default_answer": "结论：当前问题我先按本地规则回答。请围绕 SOC、四次采样、GC 组分、LFL_mix、报警理由或报告数据来源提问。注意：本平台只提供虚拟仿真教学解释，不提供真实危险实验操作、消防处置或工程防爆设计建议。",
    }

    components.html(
        _render_component_html(
            component_id=key_prefix,
            context=_context_dict(context, st.session_state.get(_state_key(key_prefix, "latest_mode"), current_chat_mode())),
            visual=visual,
            history=ai_state["history"],
            latest_question=ai_state["latest_question"],
            latest_answer=ai_state["latest_answer"],
            process_advice=process_advice,
            local_answers=local_answers,
            quick=list(quick_questions()),
            evaluation_markdown=evaluation_markdown,
            trace_json=trace_json,
            progress_snapshot=_compact_experiment_snapshot(experiment_context),
        ),
        height=0,
        scrolling=False,
    )
