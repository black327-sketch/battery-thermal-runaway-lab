"""Interactive lab canvas helpers for Streamlit pages."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

import streamlit as st
import streamlit.components.v1 as components

from app.utils.ui_theme import get_theme_tokens


SOURCE_FRAGMENT_PATTERNS = ("<polyline", "<text ", "<path ", "<line ", "<rect ")


@dataclass(frozen=True)
class CanvasSettings:
    """Current canvas display settings."""

    zoom: float
    fullscreen: bool
    detailed: bool
    show_device_labels: bool
    show_pipeline_labels: bool
    show_risk_overlay: bool
    runaway_focus: bool
    show_ports: bool = False


def _state_key(key_prefix: str, name: str) -> str:
    return f"{key_prefix}_{name}"


def init_canvas_state(key_prefix: str = "lab_canvas") -> None:
    """Initialize canvas session state with stable defaults."""
    defaults = {
        "zoom": 1.0,
        "fullscreen": False,
        "detailed": True,
        "show_device_labels": True,
        "show_pipeline_labels": True,
        "show_ports": False,
        "show_risk_overlay": True,
        "runaway_focus": False,
    }
    for name, value in defaults.items():
        st.session_state.setdefault(_state_key(key_prefix, name), value)


def get_canvas_settings(key_prefix: str = "lab_canvas") -> CanvasSettings:
    """Return current canvas settings."""
    init_canvas_state(key_prefix)
    return CanvasSettings(
        zoom=float(st.session_state[_state_key(key_prefix, "zoom")]),
        fullscreen=bool(st.session_state[_state_key(key_prefix, "fullscreen")]),
        detailed=bool(st.session_state[_state_key(key_prefix, "detailed")]),
        show_device_labels=bool(st.session_state[_state_key(key_prefix, "show_device_labels")]),
        show_pipeline_labels=bool(st.session_state[_state_key(key_prefix, "show_pipeline_labels")]),
        show_ports=bool(st.session_state[_state_key(key_prefix, "show_ports")]),
        show_risk_overlay=bool(st.session_state[_state_key(key_prefix, "show_risk_overlay")]),
        runaway_focus=bool(st.session_state[_state_key(key_prefix, "runaway_focus")]),
    )


def render_canvas_toolbar(key_prefix: str = "lab_canvas") -> CanvasSettings:
    """Render zoom, view and overlay controls for the lab canvas."""
    init_canvas_state(key_prefix)
    cols = st.columns(4, gap="small")
    with cols[0]:
        if st.button("放大", key=_state_key(key_prefix, "zoom_in"), use_container_width=True):
            st.session_state[_state_key(key_prefix, "zoom")] = min(
                1.75,
                float(st.session_state[_state_key(key_prefix, "zoom")]) + 0.15,
            )
            st.rerun()
    with cols[1]:
        if st.button("缩小", key=_state_key(key_prefix, "zoom_out"), use_container_width=True):
            st.session_state[_state_key(key_prefix, "zoom")] = max(
                0.7,
                float(st.session_state[_state_key(key_prefix, "zoom")]) - 0.15,
            )
            st.rerun()
    with cols[2]:
        if st.button("适应宽度", key=_state_key(key_prefix, "zoom_fit"), use_container_width=True):
            st.session_state[_state_key(key_prefix, "zoom")] = 1.0
            st.rerun()
    with cols[3]:
        full = bool(st.session_state[_state_key(key_prefix, "fullscreen")])
        label = "退出大画布" if full else "大画布"
        if st.button(label, key=_state_key(key_prefix, "fullscreen_btn"), use_container_width=True):
            st.session_state[_state_key(key_prefix, "fullscreen")] = not full
            st.rerun()
    toggles = st.columns(5, gap="small")
    with toggles[0]:
        st.toggle("详细视图", key=_state_key(key_prefix, "detailed"))
    with toggles[1]:
        st.toggle("设备标签", key=_state_key(key_prefix, "show_device_labels"))
    with toggles[2]:
        st.toggle("管路标签", key=_state_key(key_prefix, "show_pipeline_labels"))
    with toggles[3]:
        st.toggle("端口调试", key=_state_key(key_prefix, "show_ports"))
    with toggles[4]:
        st.toggle("风险叠加", key=_state_key(key_prefix, "show_risk_overlay"))
    return get_canvas_settings(key_prefix)


def validate_svg_markup(svg_markup: str) -> tuple[bool, str]:
    """Validate that markup contains exactly one complete SVG container."""
    text = svg_markup.strip()
    if "<svg" not in text or "</svg>" not in text:
        return False, "画布资源不是完整 SVG，已阻止源码片段显示。"
    if text.count("<svg") != text.count("</svg>"):
        return False, "画布资源 SVG 标签不完整，已阻止源码片段显示。"
    if text.find("<svg") > text.rfind("</svg>"):
        return False, "画布资源结构异常，已阻止源码片段显示。"
    return True, ""


def remove_source_fragments_for_text(markup: str) -> str:
    """Remove SVG/HTML tags and return text content for source-leak tests."""
    return re.sub(r"<[^>]+>", "", markup)


def build_svg_canvas_html(
    svg_markup: str,
    *,
    title: str,
    settings: CanvasSettings,
    height: int,
) -> str:
    """Build isolated HTML for the SVG canvas component."""
    scale = settings.zoom
    canvas_height = height
    safe_title = html.escape(title)
    mode_label = "大画布" if settings.fullscreen else "标准视图"
    tokens = get_theme_tokens()
    viewport_height = max(320, int((canvas_height - 43) * scale))
    classes = [
        "lab-canvas-shell",
        "is-fullscreen" if settings.fullscreen else "",
        "is-compact" if not settings.detailed else "",
        "hide-device-labels" if not settings.show_device_labels else "",
        "hide-pipeline-labels" if not settings.show_pipeline_labels else "",
        "show-port-debug" if settings.show_ports else "",
        "hide-risk-overlay" if not settings.show_risk_overlay else "",
        "runaway-focus" if settings.runaway_focus else "",
    ]
    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
:root {{
  --app-primary: {tokens["primary"]};
  --app-primary-light: {tokens["primary_light"]};
  --app-cyan: {tokens["cyan"]};
  --app-green: {tokens["green"]};
  --app-yellow: {tokens["yellow"]};
  --app-orange: {tokens["orange"]};
  --app-red: {tokens["red"]};
  --app-bg: {tokens["bg"]};
  --app-surface: {tokens["surface"]};
  --app-surface-soft: {tokens["surface_soft"]};
  --app-border: {tokens["border"]};
  --app-text: {tokens["text"]};
  --app-muted: {tokens["muted"]};
  --app-shadow: {tokens["shadow"]};
  --equipment-fill: {tokens["equipment_fill"]};
  --equipment-stroke: {tokens["equipment_stroke"]};
  --pipeline-idle: {tokens["pipeline_idle"]};
  --pipeline-active: {tokens["pipeline_active"]};
}}
html, body {{
  margin: 0;
  padding: 0;
  background: transparent;
  color: var(--app-text, #213547);
  font-family: "Microsoft YaHei", Arial, sans-serif;
}}
.lab-canvas-shell {{
  height: {canvas_height}px;
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid var(--app-border, #d9e4ef);
  border-radius: 12px;
  background: linear-gradient(180deg, var(--app-surface, #fff), var(--app-surface-soft, #f8fbfe));
  box-shadow: var(--app-shadow, 0 8px 24px rgba(11,58,99,.08));
}}
.lab-canvas-title {{
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 10px 14px;
  background: var(--app-surface, #fff);
  border-bottom: 1px solid var(--app-border, #d9e4ef);
  font-size: 14px;
  font-weight: 700;
}}
.lab-canvas-title span:last-child {{
  font-size: 12px;
  color: var(--app-muted, #607485);
  font-weight: 500;
}}
.lab-canvas-viewport {{
  box-sizing: border-box;
  width: calc(100% * {scale});
  min-width: 100%;
  height: {viewport_height}px;
  padding: 8px;
}}
.lab-canvas-viewport svg {{
  display: block;
  width: 100%;
  height: 100%;
  min-width: 0;
  max-width: none;
}}
.hide-device-labels svg text.device-label,
.hide-device-labels svg text.hotspot-label {{
  display: none;
}}
.hide-pipeline-labels svg text.pipeline-label {{
  display: none;
}}
.hide-risk-overlay .risk-overlay {{
  display: none;
}}
.port-debug-layer.hidden {{
  display: none;
}}
.show-port-debug .port-debug-layer.hidden {{
  display: block;
}}
.port-debug-node circle {{
  fill: var(--app-yellow, #f2c94c);
  stroke: var(--app-red, #c62828);
  stroke-width: 1.5;
}}
.port-debug-node text {{
  font-size: 10px;
  fill: var(--app-red, #c62828);
  paint-order: stroke;
  stroke: var(--app-surface, #fff);
  stroke-width: 3px;
}}
.is-compact .detail-layer {{
  display: none;
}}
.runaway-focus svg {{
  filter: saturate(1.08) contrast(1.04);
}}
.connection-line {{
  fill: none;
  stroke: var(--pipeline-idle, #6b7f90);
  stroke-width: 7;
  stroke-linecap: round;
  stroke-linejoin: round;
}}
.connection-line.physical {{
  stroke-dasharray: none;
}}
.connection-line.virtual {{
  stroke-width: 4;
  stroke-dasharray: 8 8;
}}
.connection-line.active {{
  stroke: var(--pipeline-active, #1f9bb4);
  stroke-dasharray: 13 10;
  animation: pipe-flow 0.9s linear infinite;
}}
.connection-line.alert {{
  stroke: var(--app-red, #c62828);
  stroke-dasharray: 12 8;
}}
.connection-label {{
  font-size: 15px;
  fill: var(--app-muted, #607485);
  paint-order: stroke;
  stroke: var(--app-surface, #fff);
  stroke-width: 4px;
}}
.connection-legend .legend-bg {{
  fill: var(--app-surface, #fff);
  stroke: var(--app-border, #d9e4ef);
  stroke-width: 1.5;
}}
.connection-legend .legend-title {{
  font-weight: 800;
  fill: var(--app-primary, #0b5cab);
}}
@keyframes pipe-flow {{
  to {{ stroke-dashoffset: -23; }}
}}
@media (prefers-reduced-motion: reduce) {{
  * {{ animation: none !important; transition: none !important; }}
}}
</style>
</head>
<body>
<div class="{' '.join(c for c in classes if c)}">
  <div class="lab-canvas-title">
    <span>{safe_title}</span>
    <span>缩放 {scale:.0%} · {mode_label}</span>
  </div>
  <div class="lab-canvas-viewport">
    {svg_markup}
  </div>
</div>
</body>
</html>
"""


def render_svg_canvas(
    svg_markup: str,
    *,
    title: str,
    key_prefix: str = "lab_canvas",
    height: int = 560,
) -> CanvasSettings:
    """Render a complete SVG inside an isolated HTML component."""
    settings = get_canvas_settings(key_prefix)
    ok, message = validate_svg_markup(svg_markup)
    if not ok:
        st.warning(message)
        return settings

    canvas_height = height
    svg_markup = re.sub(
        r"<svg\b(?![^>]*preserveAspectRatio=)",
        '<svg preserveAspectRatio="xMidYMid meet"',
        svg_markup,
        count=1,
    )
    html_doc = build_svg_canvas_html(svg_markup, title=title, settings=settings, height=canvas_height)
    components.html(html_doc, height=canvas_height + 8, scrolling=True)
    return settings
