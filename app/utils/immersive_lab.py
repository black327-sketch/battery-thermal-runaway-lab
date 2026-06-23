"""Immersive lab window helpers for the 2D interactive experiment page."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass(frozen=True)
class LabAction:
    """A Streamlit-backed action placed inside the lab operation panel."""

    action: str
    label: str
    key: str
    disabled: bool = False
    help: str = ""
    primary: bool = False
    payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class LabActionGroup:
    """A device or stage action group."""

    title: str
    subtitle: str
    actions: tuple[LabAction, ...]


def score_tone(summary: dict[str, Any]) -> tuple[str, str]:
    """Return semantic tone and label for a score summary."""
    score = int(summary.get("score", 100))
    safety_status = str(summary.get("safety_status", "规范"))
    if score < 60 or safety_status == "需重做":
        return "danger", "需重做"
    if score < 75 or not bool(summary.get("valid_data", True)) or safety_status == "需复核":
        return "warning", "有明显违规 / 勉强合格"
    if score < 90:
        return "good", "良好"
    return "excellent", "优秀"


def recent_deductions(summary: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    """Return the most recent visible deduction records."""
    return list(summary.get("deductions", []))[:limit]


def latest_safety_alert(summary: dict[str, Any]) -> dict[str, str] | None:
    """Return the latest serious alert for the central overlay."""
    alert = summary.get("latest_severe_warning") or summary.get("last_alert")
    if alert and alert.get("active", True):
        return {
            "reason": str(alert.get("message") or "操作顺序不符合虚拟实验规范。"),
            "consequence": str(alert.get("consequence") or "本轮数据有效性需复核。"),
            "severity": str(alert.get("severity") or "major"),
        }
    return None


def render_window_header(title: str, subtitle: str, *, fullscreen: bool, key_prefix: str) -> None:
    """Render the immersive lab window title bar."""
    mode_label = "退出大屏实验模式" if fullscreen else "大屏实验模式"
    st.markdown(
        f"""
<div class="immersive-titlebar">
  <div>
    <div class="immersive-title">{title}</div>
    <div class="immersive-subtitle">{subtitle}</div>
  </div>
  <div class="immersive-titlebar-note">操作、评分、画布和数据反馈均在本实验窗口内完成</div>
</div>
""",
        unsafe_allow_html=True,
    )
    if st.button(mode_label, key=f"{key_prefix}_immersive_fullscreen", use_container_width=True):
        st.session_state[f"{key_prefix}_fullscreen"] = not fullscreen
        st.rerun()


def render_score_overlay(summary: dict[str, Any], stage: str) -> None:
    """Render top-left score and deduction status inside the lab window."""
    tone, label = score_tone(summary)
    valid = "有效" if summary.get("valid_data", True) else "需复核"
    deductions = recent_deductions(summary)
    rows = ""
    for item in deductions:
        rows += (
            f'<div class="immersive-deduction">- {int(item.get("points", 0))}：'
            f'{item.get("reason", "扣分记录")}</div>'
        )
    if not rows:
        rows = '<div class="immersive-no-deduction">暂无扣分记录</div>'
    st.markdown(
        f"""
<div class="immersive-score immersive-score-{tone}">
  <div class="score-line">
    <span class="score-value">{int(summary.get("score", 100))}</span>
    <span class="score-grade">{label}</span>
  </div>
  <div class="score-meta">数据：{valid} · 阶段：{stage}</div>
  {rows}
</div>
""",
        unsafe_allow_html=True,
    )


def render_safety_overlay(summary: dict[str, Any]) -> None:
    """Render central safety alert when an unsafe virtual operation was attempted."""
    alert = latest_safety_alert(summary)
    if not alert:
        return
    st.markdown(
        f"""
<div class="immersive-safety-overlay">
  <div class="safety-title">注意实验安全！！！</div>
  <div class="safety-reason">{alert["reason"]}</div>
  <div class="safety-consequence">{alert["consequence"]}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_action_groups(groups: list[LabActionGroup], handler) -> None:
    """Render scrollable action groups and dispatch Streamlit button clicks."""
    for group in groups:
        st.markdown(
            f"""
<div class="immersive-action-heading">
  <div>{group.title}</div>
  <span>{group.subtitle}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        for action in group.actions:
            if st.button(
                action.label,
                key=action.key,
                disabled=action.disabled,
                type="primary" if action.primary and not action.disabled else "secondary",
                help=action.help or None,
                use_container_width=True,
            ):
                handler(action.action, action.payload)


def render_status_strip(items: list[tuple[str, str, str]]) -> None:
    """Render compact device status chips inside the lab window."""
    chips = ""
    for label, value, tone in items:
        chips += f'<span class="immersive-chip immersive-chip-{tone}"><b>{label}</b>{value}</span>'
    st.markdown(f'<div class="immersive-status-strip">{chips}</div>', unsafe_allow_html=True)
