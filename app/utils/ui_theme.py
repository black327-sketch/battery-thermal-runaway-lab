"""
app/utils/ui_theme.py —— Streamlit 全局视觉主题

提供统一 CSS 变量、页面基础样式和全局页脚。
"""

from __future__ import annotations

import streamlit as st

from app.utils.app_config import APP_NAME, APP_VERSION, SAFETY_NOTICE


LIGHT_TOKENS = {
    "primary": "#0b3a63",
    "primary_light": "#1565c0",
    "cyan": "#00838f",
    "green": "#2e7d32",
    "yellow": "#b7791f",
    "orange": "#c05621",
    "red": "#c62828",
    "bg": "#f4f8fb",
    "surface": "#ffffff",
    "surface_soft": "#f8fbfe",
    "border": "#d9e4ef",
    "text": "#213547",
    "muted": "#607485",
    "shadow": "0 8px 24px rgba(11, 58, 99, 0.08)",
    "radius": "12px",
    "equipment_fill": "#e8f2fb",
    "equipment_stroke": "#385f7a",
    "pipeline_idle": "#8aa2b4",
    "pipeline_active": "#00a8b5",
}

DARK_TOKENS = {
    "primary": "#8ecbff",
    "primary_light": "#58a6ff",
    "cyan": "#35d0df",
    "green": "#7bd88f",
    "yellow": "#f2c94c",
    "orange": "#ff9f43",
    "red": "#ff6b6b",
    "bg": "#0f1720",
    "surface": "#17212b",
    "surface_soft": "#202c37",
    "border": "#334555",
    "text": "#e9f2f8",
    "muted": "#a8bbc9",
    "shadow": "0 10px 28px rgba(0, 0, 0, 0.34)",
    "radius": "12px",
    "equipment_fill": "#223241",
    "equipment_stroke": "#9fc3dc",
    "pipeline_idle": "#6f8797",
    "pipeline_active": "#37d7e5",
}


def get_current_theme() -> str:
    """返回当前主题模式。"""
    mode = st.session_state.get("theme_mode", "light")
    if mode not in {"light", "dark"}:
        mode = "light"
        st.session_state["theme_mode"] = mode
    return mode


def toggle_theme() -> str:
    """切换昼夜模式并返回新模式。"""
    st.session_state["theme_mode"] = "dark" if get_current_theme() == "light" else "light"
    return st.session_state["theme_mode"]


def render_theme_toggle(label: str = "昼夜模式", key: str = "theme_mode_toggle") -> str:
    """渲染主题切换控件，返回当前主题。"""
    current = get_current_theme()
    dark_enabled = st.toggle(
        label,
        value=current == "dark",
        key=key,
        help="切换平台亮色/暗色显示",
    )
    next_mode = "dark" if dark_enabled else "light"
    if next_mode != current:
        st.session_state["theme_mode"] = next_mode
        st.rerun()
    st.session_state["theme_mode"] = next_mode
    return st.session_state["theme_mode"]


def get_theme_tokens(theme_mode: str | None = None) -> dict[str, str]:
    """返回页面视觉系统使用的颜色、圆角和阴影令牌。"""
    mode = theme_mode or get_current_theme()
    return DARK_TOKENS.copy() if mode == "dark" else LIGHT_TOKENS.copy()


def get_plotly_theme_tokens(theme_mode: str | None = None) -> dict[str, str]:
    """返回 Plotly 图表主题令牌。"""
    t = get_theme_tokens(theme_mode)
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font_color": t["text"],
        "grid_color": t["border"],
        "axis_color": t["muted"],
        "primary": t["primary_light"],
        "cyan": t["cyan"],
        "green": t["green"],
        "yellow": t["yellow"],
        "orange": t["orange"],
        "red": t["red"],
        "muted": t["muted"],
        "surface": t["surface"],
    }


def is_tablet_demo_mode() -> bool:
    """Return whether the app should use the tablet landscape demo layout."""

    try:
        demo = st.query_params.get("demo", "")
    except Exception:
        demo = ""
    enabled = str(demo).lower() == "tablet" or bool(st.session_state.get("tablet_demo_mode"))
    if enabled:
        st.session_state["tablet_demo_mode"] = True
    return enabled


def render_tablet_demo_entry() -> None:
    """Render a compact entry into tablet demo mode without affecting normal mode."""

    if is_tablet_demo_mode():
        st.caption("平板演示模式已启用")
        return
    st.link_button("进入演示模式", "?demo=tablet", width="stretch")


def apply_global_style() -> None:
    """注入全局 CSS，使各页面拥有一致的产品化观感。"""
    t = get_theme_tokens()
    tablet_demo_css = """
[data-testid="stSidebar"] {
    transform: translateX(-96%);
    opacity: 0.12;
    transition: opacity 0.16s ease-out, transform 0.16s ease-out;
}

[data-testid="stSidebar"]:hover,
[data-testid="stSidebar"]:focus-within {
    transform: none;
    opacity: 1;
}

.block-container {
    max-width: 1480px !important;
    padding: 1rem 1.2rem 2rem !important;
}

.app-hero {
    padding: 18px 22px;
    margin-bottom: 10px;
}

.app-hero h1 {
    font-size: 1.72rem;
}

.app-hero p {
    font-size: 0.96rem;
    line-height: 1.55;
}

.stButton button,
.stDownloadButton button,
button {
    min-height: 44px;
}

div[data-testid="stDataFrame"],
[data-testid="stTable"] {
    overflow-x: auto;
}

.lab-workbench,
.app-workbench {
    padding: 8px;
}

@media (orientation: landscape) and (min-width: 1000px) {
    .floating-ai-panel {
        max-height: calc(100vh - 28px);
    }
}
"""
    st.markdown(
        f"""
<style>
:root {{
    --app-primary: {t["primary"]};
    --app-primary-light: {t["primary_light"]};
    --app-cyan: {t["cyan"]};
    --app-green: {t["green"]};
    --app-yellow: {t["yellow"]};
    --app-orange: {t["orange"]};
    --app-red: {t["red"]};
    --app-bg: {t["bg"]};
    --app-surface: {t["surface"]};
    --app-surface-soft: {t["surface_soft"]};
    --app-border: {t["border"]};
    --app-text: {t["text"]};
    --app-muted: {t["muted"]};
    --app-radius: {t["radius"]};
    --app-shadow: {t["shadow"]};
    --equipment-fill: {t["equipment_fill"]};
    --equipment-stroke: {t["equipment_stroke"]};
    --pipeline-idle: {t["pipeline_idle"]};
    --pipeline-active: {t["pipeline_active"]};
}}

.stApp {{
    background: var(--app-bg);
    color: var(--app-text);
}}

[data-testid="stSidebar"] {{
    background: var(--app-surface);
    border-right: 1px solid var(--app-border);
}}

[data-testid="stHeader"] {{
    background: rgba(244, 248, 251, 0.92);
    background: color-mix(in srgb, var(--app-bg) 88%, transparent);
    backdrop-filter: blur(10px);
}}

.block-container {{
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1360px;
}}

h1, h2, h3 {{
    color: var(--app-primary);
    letter-spacing: 0;
}}

p, li, td, th, label, span {{
    letter-spacing: 0;
}}

p, li, td, th, label, span, div {{
    color: inherit;
}}

.app-hero {{
    border-radius: 18px;
    padding: 30px 32px;
    color: var(--app-text);
    background: linear-gradient(135deg, var(--app-surface), var(--app-surface-soft));
    box-shadow: var(--app-shadow);
    border: 1px solid var(--app-border);
    margin-bottom: 18px;
}}

.app-hero h1 {{
    color: var(--app-primary);
    font-size: 2.05rem;
    line-height: 1.32;
    margin: 0 0 10px;
}}

.app-hero p {{
    color: var(--app-text);
    font-size: 1rem;
    line-height: 1.72;
    margin: 0;
}}

.app-tag-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 18px;
}}

.app-tag {{
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    border-radius: 999px;
    background: var(--app-surface-soft);
    border: 1px solid var(--app-border);
    color: var(--app-text);
    font-size: 0.86rem;
}}

.app-card {{
    background: var(--app-surface);
    border: 1px solid var(--app-border);
    border-radius: var(--app-radius);
    padding: 18px 20px;
    box-shadow: var(--app-shadow);
    margin-bottom: 14px;
}}

.app-card-soft {{
    background: var(--app-surface-soft);
    border: 1px solid var(--app-border);
    border-radius: var(--app-radius);
    padding: 16px 18px;
    margin-bottom: 12px;
}}

.app-section-title {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 18px 0 10px;
}}

.app-section-title .mark {{
    width: 8px;
    height: 24px;
    border-radius: 999px;
    background: linear-gradient(180deg, var(--app-primary-light), var(--app-cyan));
}}

.app-section-title h3 {{
    margin: 0;
    font-size: 1.12rem;
}}

.app-section-title p {{
    margin: 2px 0 0;
    color: var(--app-muted);
    font-size: 0.88rem;
}}

.metric-card {{
    background: var(--app-surface);
    border: 1px solid var(--app-border);
    border-radius: 12px;
    padding: 16px 18px;
    box-shadow: 0 6px 18px rgba(11, 58, 99, 0.07);
    min-height: 116px;
}}

.metric-card .label {{
    color: var(--app-muted);
    font-size: 0.88rem;
    margin-bottom: 8px;
}}

.metric-card .value {{
    color: var(--app-primary);
    font-size: 1.65rem;
    line-height: 1.2;
    font-weight: 750;
}}

.metric-card .help {{
    color: var(--app-muted);
    font-size: 0.8rem;
    line-height: 1.45;
    margin-top: 7px;
}}

.feature-card {{
    background: var(--app-surface);
    border: 1px solid var(--app-border);
    border-radius: 12px;
    padding: 18px;
    box-shadow: 0 6px 18px rgba(11, 58, 99, 0.07);
    min-height: 148px;
}}

.feature-card .index {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border-radius: 8px;
    background: var(--app-surface-soft);
    color: var(--app-primary-light);
    font-weight: 750;
    margin-bottom: 10px;
}}

.feature-card h4 {{
    color: var(--app-primary);
    margin: 0 0 6px;
    font-size: 1rem;
}}

.feature-card p {{
    color: var(--app-muted);
    margin: 0;
    font-size: 0.88rem;
    line-height: 1.6;
}}

.warning-banner {{
    background: var(--app-surface-soft);
    border: 1px solid var(--app-border);
    border-left: 5px solid var(--app-orange);
    border-radius: 12px;
    padding: 14px 18px;
    color: var(--app-text);
    line-height: 1.65;
    margin: 14px 0;
}}

.model-notice {{
    background: var(--app-surface-soft);
    border: 1px solid var(--app-border);
    border-left: 5px solid var(--app-cyan);
    border-radius: 12px;
    padding: 14px 18px;
    color: var(--app-text);
    line-height: 1.65;
    margin: 14px 0;
}}

.risk-badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 7px 14px;
    border-radius: 999px;
    font-weight: 750;
    font-size: 0.9rem;
    border: 1px solid currentColor;
}}

.stepper {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: stretch;
    margin: 12px 0 18px;
}}

.stepper .step {{
    flex: 1 1 130px;
    min-width: 120px;
    background: var(--app-surface);
    border: 1px solid var(--app-border);
    border-radius: 12px;
    padding: 12px 12px;
    box-shadow: 0 4px 14px rgba(11, 58, 99, 0.06);
}}

.stepper .step .num {{
    color: var(--app-primary-light);
    font-weight: 800;
    font-size: 0.82rem;
    margin-bottom: 5px;
}}

.stepper .step .name {{
    color: var(--app-text);
    font-size: 0.88rem;
    line-height: 1.45;
}}

.result-card {{
    background: linear-gradient(180deg, var(--app-surface), var(--app-surface-soft));
    border: 1px solid var(--app-border);
    border-radius: 14px;
    padding: 20px;
    box-shadow: var(--app-shadow);
}}

.result-card .headline {{
    color: var(--app-muted);
    font-size: 0.9rem;
    margin-bottom: 8px;
}}

.result-card .big {{
    color: var(--app-primary);
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.2;
}}

.app-footer {{
    text-align: center;
    color: var(--app-muted);
    font-size: 0.82rem;
    line-height: 1.7;
    margin-top: 28px;
    padding-top: 16px;
    border-top: 1px solid var(--app-border);
}}

div[data-testid="stMetric"] {{
    background: var(--app-surface);
    border: 1px solid var(--app-border);
    border-radius: 12px;
    padding: 12px 14px;
    box-shadow: 0 5px 16px rgba(11, 58, 99, 0.06);
}}

.stDownloadButton button, .stButton button {{
    border-radius: 10px;
    border: 1px solid var(--app-primary-light);
    min-height: 2.45rem;
    white-space: normal;
}}

.stButton button:disabled, .stDownloadButton button:disabled {{
    border-color: var(--app-border);
    color: var(--app-muted);
    background: var(--app-surface-soft);
    opacity: 0.82;
}}

.stDataFrame, [data-testid="stTable"] {{
    color: var(--app-text);
}}

.app-workbench {{
    background: var(--app-surface);
    border: 1px solid var(--app-border);
    border-radius: var(--app-radius);
    box-shadow: var(--app-shadow);
    padding: 12px;
}}

.equipment-svg text {{
    fill: var(--app-text);
    font-family: "Microsoft YaHei", Arial, sans-serif;
}}

.equipment-svg .device-fill {{
    fill: var(--equipment-fill);
    stroke: var(--equipment-stroke);
}}

.equipment-svg .pipeline {{
    stroke: var(--pipeline-idle);
    fill: none;
    stroke-width: 6;
    stroke-linecap: round;
}}

.equipment-svg .pipeline.active {{
    stroke: var(--pipeline-active);
    stroke-dasharray: 10 8;
    animation: pipe-flow 0.8s linear infinite;
}}

@keyframes pipe-flow {{
    to {{ stroke-dashoffset: -18; }}
}}

.immersive-shell {{
    display: none;
}}

.immersive-shell.is-fullscreen {{
    display: none;
}}

.immersive-titlebar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
    padding: 10px 12px;
    border: 1px solid var(--app-border);
    border-radius: 10px;
    background: var(--app-surface-soft);
    margin-bottom: 10px;
}}

.immersive-title {{
    color: var(--app-primary);
    font-size: 1.04rem;
    font-weight: 800;
    line-height: 1.35;
}}

.immersive-subtitle,
.immersive-titlebar-note {{
    color: var(--app-muted);
    font-size: 0.82rem;
    line-height: 1.45;
}}

.immersive-score {{
    position: sticky;
    top: 58px;
    z-index: 4;
    border-radius: 10px;
    padding: 12px 13px;
    margin-bottom: 10px;
    background: var(--app-surface);
    border: 2px solid var(--app-green);
}}

.immersive-score-danger {{
    border-color: var(--app-red);
}}

.immersive-score-warning {{
    border-color: var(--app-orange);
}}

.immersive-score-good,
.immersive-score-excellent {{
    border-color: var(--app-green);
}}

.score-line {{
    display: flex;
    align-items: baseline;
    gap: 10px;
}}

.score-value {{
    color: var(--app-primary);
    font-size: 2rem;
    line-height: 1;
    font-weight: 850;
}}

.score-grade {{
    color: var(--app-text);
    font-size: 0.95rem;
    font-weight: 750;
}}

.score-meta {{
    color: var(--app-muted);
    font-size: 0.8rem;
    margin: 6px 0 8px;
}}

.immersive-deduction {{
    color: var(--app-red);
    font-size: 0.8rem;
    line-height: 1.48;
    font-weight: 700;
    margin-top: 4px;
}}

.immersive-no-deduction {{
    color: var(--app-muted);
    font-size: 0.8rem;
}}

.immersive-safety-overlay {{
    position: sticky;
    top: 118px;
    z-index: 5;
    max-width: 620px;
    margin: 0 auto 10px;
    text-align: center;
    background: color-mix(in srgb, var(--app-surface) 88%, var(--app-red));
    border: 2px solid var(--app-red);
    border-radius: 12px;
    padding: 16px 18px;
}}

.immersive-safety-overlay .safety-title {{
    color: var(--app-red);
    font-size: 1.45rem;
    font-weight: 900;
    line-height: 1.2;
    margin-bottom: 8px;
}}

.immersive-safety-overlay .safety-reason {{
    color: var(--app-red);
    font-size: 0.98rem;
    font-weight: 760;
    line-height: 1.5;
}}

.immersive-safety-overlay .safety-consequence {{
    color: var(--app-text);
    font-size: 0.86rem;
    line-height: 1.55;
    margin-top: 5px;
}}

.immersive-status-strip {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 8px 0 10px;
}}

.immersive-chip {{
    display: inline-flex;
    gap: 6px;
    align-items: center;
    border: 1px solid var(--app-border);
    border-radius: 999px;
    padding: 6px 10px;
    background: var(--app-surface-soft);
    color: var(--app-text);
    font-size: 0.78rem;
}}

.immersive-chip-done {{
    border-color: var(--app-green);
}}

.immersive-chip-active {{
    border-color: var(--app-primary-light);
}}

.immersive-chip-alert {{
    border-color: var(--app-red);
    color: var(--app-red);
}}

.immersive-action-panel {{
    max-height: 690px;
    overflow-y: auto;
    padding: 10px;
    border: 1px solid var(--app-border);
    border-radius: 10px;
    background: var(--app-surface-soft);
}}

.immersive-shell.is-fullscreen .immersive-action-panel {{
    max-height: calc(100vh - 260px);
}}

.immersive-action-heading {{
    padding: 9px 10px;
    border: 1px solid var(--app-border);
    border-radius: 9px;
    margin: 10px 0 8px;
    background: var(--app-surface);
}}

.immersive-action-heading div {{
    color: var(--app-primary);
    font-size: 0.92rem;
    font-weight: 800;
    line-height: 1.35;
}}

.immersive-action-heading span {{
    color: var(--app-muted);
    display: block;
    font-size: 0.76rem;
    line-height: 1.45;
    margin-top: 2px;
}}

.immersive-stage-left {{
    max-height: 690px;
    overflow-y: auto;
}}

.immersive-shell.is-fullscreen .immersive-stage-left {{
    max-height: calc(100vh - 260px);
}}

.immersive-data-zone {{
    margin-top: 12px;
    border: 1px solid var(--app-border);
    border-radius: 10px;
    padding: 10px;
    background: var(--app-surface-soft);
}}

.lab-workbench {{
    border: 1px solid var(--app-border);
    border-radius: 12px;
    background: var(--app-surface);
    padding: 12px;
    margin: 10px 0 12px;
}}

.lab-workbench.is-fullscreen {{
    min-height: calc(100vh - 170px);
    padding: 10px;
    background: var(--app-surface-soft);
}}

.lab-workbench .stColumn {{
    min-width: 0;
}}

.workbench-stage {{
    min-width: 0;
}}

.workbench-panel,
.workbench-action-panel {{
    border: 1px solid var(--app-border);
    border-radius: 10px;
    background: var(--app-surface);
    padding: 10px;
}}

.workbench-action-panel {{
    max-height: 780px;
    overflow-y: auto;
}}

.lab-workbench.is-fullscreen .workbench-action-panel {{
    max-height: calc(100vh - 245px);
}}

.arc-browser-fullscreen [data-testid="stSidebar"],
.arc-browser-fullscreen [data-testid="stHeader"],
.arc-browser-fullscreen [data-testid="stToolbar"],
.arc-browser-fullscreen [data-testid="stDecoration"],
.arc-browser-fullscreen #MainMenu,
.arc-browser-fullscreen footer {{
    display: none !important;
}}

.arc-browser-fullscreen .block-container {{
    max-width: 100vw !important;
    width: 100vw !important;
    height: 100vh !important;
    overflow: auto !important;
    padding: 0.5rem 0.75rem !important;
    background: var(--app-bg);
}}

.workbench-panel-title {{
    color: var(--app-primary);
    font-size: 0.92rem;
    font-weight: 850;
    line-height: 1.3;
    margin-bottom: 8px;
}}

.workbench-panel-hint {{
    color: var(--app-muted);
    font-size: 0.78rem;
    line-height: 1.45;
    margin-bottom: 8px;
}}

.workbench-data-grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
    margin-bottom: 10px;
}}

.workbench-data-row {{
    border: 1px solid var(--app-border);
    border-radius: 8px;
    background: var(--app-surface-soft);
    padding: 7px 8px;
    min-width: 0;
}}

.workbench-data-row span {{
    display: block;
    color: var(--app-muted);
    font-size: 0.72rem;
    line-height: 1.2;
}}

.workbench-data-row b {{
    display: block;
    color: var(--app-text);
    font-size: 0.82rem;
    line-height: 1.25;
    margin-top: 2px;
    word-break: break-word;
}}

.immersive-shell.is-fullscreen .immersive-data-zone {{
    max-height: 360px;
    overflow-y: auto;
}}

@media (max-width: 900px) {{
    .immersive-titlebar {{
        align-items: flex-start;
        flex-direction: column;
    }}
    .immersive-score {{
        position: static;
    }}
}}
{tablet_demo_css if is_tablet_demo_mode() else ""}
</style>
""",
        unsafe_allow_html=True,
    )


def render_global_footer() -> None:
    """渲染统一页脚。"""
    st.markdown(
        f"""
<div class="app-footer">
    <strong>{APP_NAME}</strong> · {APP_VERSION}<br>
    {SAFETY_NOTICE}
</div>
""",
        unsafe_allow_html=True,
    )
