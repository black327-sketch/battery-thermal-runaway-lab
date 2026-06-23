"""
app/utils/ui_components.py —— 页面通用 UI 组件

封装页面标题、卡片、指标、风险标签、步骤条和模型提示。
"""

from __future__ import annotations

import html
from typing import Iterable, Sequence

import streamlit as st

from app.utils.app_config import RISK_LEVEL_CONFIG, SAFETY_NOTICE


def _escape(value: object) -> str:
    """HTML 转义。"""
    return html.escape("" if value is None else str(value))


def render_page_header(
    title: str,
    description: str,
    eyebrow: str = "虚拟仿真实验教学模块",
    tags: Sequence[str] | None = None,
    show_safety: bool = True,
) -> None:
    """渲染统一页面标题区。"""
    tags_html = ""
    if tags:
        tags_html = '<div class="app-tag-row">' + "".join(
            f'<span class="app-tag">{_escape(tag)}</span>' for tag in tags
        ) + "</div>"

    safety_html = (
        f'<div class="app-tag-row"><span class="app-tag">安全边界：{_escape(SAFETY_NOTICE)}</span></div>'
        if show_safety
        else ""
    )

    st.markdown(
        f"""
<div class="app-hero">
    <div style="font-size:0.88rem;color:#bfefff;margin-bottom:8px;">{_escape(eyebrow)}</div>
    <h1>{_escape(title)}</h1>
    <p>{_escape(description)}</p>
    {tags_html}
    {safety_html}
</div>
""",
        unsafe_allow_html=True,
    )


def render_section_title(title: str, description: str | None = None) -> None:
    """渲染统一二级区块标题。"""
    desc_html = f"<p>{_escape(description)}</p>" if description else ""
    st.markdown(
        f"""
<div class="app-section-title">
    <span class="mark"></span>
    <div>
        <h3>{_escape(title)}</h3>
        {desc_html}
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_info_card(title: str, body: str, accent: str = "#1565c0") -> None:
    """渲染说明卡。body 支持安全的简单 HTML。"""
    st.markdown(
        f"""
<div class="app-card" style="border-left:5px solid {accent};">
    <h4 style="margin:0 0 8px;color:var(--app-primary);">{_escape(title)}</h4>
    <div style="color:var(--app-text);line-height:1.75;font-size:0.92rem;">{body}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_metric_card(
    label: str,
    value: str | int | float,
    unit: str = "",
    help_text: str = "",
) -> None:
    """渲染统一指标卡。"""
    unit_html = f' <span style="font-size:0.9rem;color:var(--app-muted);">{_escape(unit)}</span>' if unit else ""
    help_html = f'<div class="help">{_escape(help_text)}</div>' if help_text else ""
    st.markdown(
        f"""
<div class="metric-card">
    <div class="label">{_escape(label)}</div>
    <div class="value">{_escape(value)}{unit_html}</div>
    {help_html}
</div>
""",
        unsafe_allow_html=True,
    )


def render_kpi_grid(items: Sequence[dict[str, object]], columns: int = 4) -> None:
    """以多列网格渲染指标卡。"""
    cols = st.columns(columns)
    for idx, item in enumerate(items):
        with cols[idx % columns]:
            render_metric_card(
                label=str(item.get("label", "")),
                value=item.get("value", ""),
                unit=str(item.get("unit", "")),
                help_text=str(item.get("help", "")),
            )


def render_warning_banner(message: str, title: str = "安全边界声明") -> None:
    """渲染黄色安全提示横幅。"""
    st.markdown(
        f"""
<div class="warning-banner">
    <strong>{_escape(title)}：</strong>{_escape(message)}
</div>
""",
        unsafe_allow_html=True,
    )


def render_risk_badge(level: str) -> None:
    """根据风险等级渲染颜色标签。"""
    cfg = RISK_LEVEL_CONFIG.get(level, RISK_LEVEL_CONFIG["无法评价"])
    st.markdown(
        f"""
<span class="risk-badge" style="color:{cfg['color']};background:{cfg['bg']};border-color:{cfg['border']};">
    {_escape(level)} · {_escape(cfg.get("range", ""))}
</span>
""",
        unsafe_allow_html=True,
    )


def render_stepper(steps: Iterable[str]) -> None:
    """渲染教学流程步骤条。"""
    step_html = []
    for idx, step in enumerate(steps, start=1):
        step_html.append(
            f"""
<div class="step">
    <div class="num">{idx:02d}</div>
    <div class="name">{_escape(step)}</div>
</div>
"""
        )
    st.markdown(f'<div class="stepper">{"".join(step_html)}</div>', unsafe_allow_html=True)


def render_feature_card(index: str, title: str, description: str) -> None:
    """渲染功能模块卡片。"""
    st.markdown(
        f"""
<div class="feature-card">
    <div class="index">{_escape(index)}</div>
    <h4>{_escape(title)}</h4>
    <p>{_escape(description)}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_result_card(title: str, value: str, subtitle: str = "") -> None:
    """渲染强调型结果卡。"""
    subtitle_html = (
        f'<div style="color:var(--app-muted);font-size:0.86rem;line-height:1.6;margin-top:8px;">{_escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
<div class="result-card">
    <div class="headline">{_escape(title)}</div>
    <div class="big">{_escape(value)}</div>
    {subtitle_html}
</div>
""",
        unsafe_allow_html=True,
    )


def render_model_notice(message: str, title: str = "模型说明") -> None:
    """渲染模型假设或局限性提示。"""
    st.markdown(
        f"""
<div class="model-notice">
    <strong>{_escape(title)}：</strong>{_escape(message)}
</div>
""",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════
# 工业控制面板与设备操作系统（隐藏代码痕迹，呈现实验台体验）
# ═══════════════════════════════════════════════════════════════

_STATE_LABELS: dict[str, str] = {
    "sample_preparation": "样品准备",
    "battery_loaded": "电池已装入",
    "leak_test": "气密性检测",
    "vacuuming": "抽真空中",
    "nitrogen_filling": "氮气置换中",
    "nitrogen_filled": "氮气已充入",
    "atmosphere_replacement": "置换完成",
    "arc_ready": "ARC 就绪",
    "arc_heating": "ARC 升温中",
    "thermal_runaway": "热失控阶段",
    "cooling": "冷却阶段",
    "gas_sampling": "采样阶段",
    "gc_analysis": "GC 分析中",
    "gas_volume_calculation": "产气量记录",
    "lel_risk_evaluation": "可燃风险评价",
    "report_generated": "报告已生成",
    "soc_selection": "SOC 选择",
    "cell_loaded": "电池已放入",
    "sensors_placed": "传感器已布置",
    "chamber_closed": "舱门已关闭",
    "heating": "加热中",
    "t2_100": "T₂ 达到 100℃",
    "venting": "安全阀喷阀",
    "temperature_peak": "温度峰值",
    "pressure_stable": "压力稳定",
    "sampling_complete": "采气完成",
}

_STATE_DESCRIPTIONS: dict[str, str] = {
    "sample_preparation": "准备电池样品，选择 SOC 并装入 ARC 腔体。",
    "battery_loaded": "电池已放入腔内，请关闭舱门并进行气密性检测。",
    "leak_test": "请打开真空阀并启动真空泵，开始抽真空。",
    "vacuuming": "舱内抽真空中，压力正在下降。",
    "nitrogen_filling": "充入氮气恢复大气压，准备下一轮置换或启动 ARC。",
    "nitrogen_filled": "氮气已充入舱内，可开启加热教学演示。",
    "atmosphere_replacement": "置换完成，需完成三轮置换后才能启动 ARC。",
    "arc_ready": "三轮置换已完成，可以启动 ARC 升温。",
    "arc_heating": "ARC 加速量热仪升温中，监测温度和温升速率。",
    "thermal_runaway": "热失控阶段：温度急剧上升，压力升高。",
    "cooling": "系统冷却中，温度回降至常温。",
    "gas_sampling": "连接集气袋并打开采样阀，采集气体样品。",
    "gc_analysis": "GC 气相色谱仪分析中，等待色谱峰出现。",
    "gas_volume_calculation": "记录产气量计算状态。",
    "lel_risk_evaluation": "进行 LFL 可燃风险教学评价。",
    "report_generated": "实验流程已完成，报告已生成。",
    "soc_selection": "选择电池荷电状态 SOC，准备放入方壳 LFP 电池。",
    "cell_loaded": "方壳 LFP 电池样品已放入防爆舱，请布置热电偶。",
    "sensors_placed": "热电偶已布置，请连接电压采集线和检查压力。",
    "chamber_closed": "防爆舱门已关闭，请抽真空并充氮气。",
    "heating": "加热教学演示中，观察 T2 温度变化。",
    "t2_100": "T2 已达到 100℃，可以进行第一次采气。",
    "venting": "安全阀已喷阀，请进行第二次采气。",
    "temperature_peak": "热失控温度已达到峰值，请进行第三次采气。",
    "pressure_stable": "舱内压力已稳定，请进行第四次采气。",
    "sampling_complete": "四个阶段采气均已完成，可送入 GC 分析。",
}

_PREVIOUS_STATE_ORDER: list[str] = [
    "soc_selection",
    "cell_loaded",
    "sensors_placed",
    "chamber_closed",
    "vacuuming",
    "nitrogen_filled",
    "heating",
    "t2_100",
    "venting",
    "temperature_peak",
    "pressure_stable",
    "sampling_complete",
    "gc_analysis",
]


def state_label(state_key: str) -> str:
    """将内部状态标识转换为中文教学阶段名称。"""
    return _STATE_LABELS.get(state_key, state_key)


def state_description(state_key: str) -> str:
    """返回当前阶段的推荐操作说明。"""
    return _STATE_DESCRIPTIONS.get(state_key, "按实验流程继续操作。")


def render_control_button(
    label: str,
    key: str,
    *,
    disabled: bool = False,
    status: str = "idle",
    help_text: str = "",
    device_id: str = "",
    primary: bool = False,
) -> bool:
    """渲染工业控制风格按钮。

    status: 'idle' | 'ready' | 'active' | 'done' | 'blocked'
    device_id: 关联设备标识，仅保留为调用兼容字段。
    """
    status_icon = {
        "ready": "●",
        "active": "◉",
        "done": "✓",
        "blocked": "⊘",
        "idle": "○",
    }.get(status, "○")
    button_label = f"{status_icon} {label}"
    button_type = "primary" if primary and not disabled else "secondary"
    if disabled and not help_text:
        help_text = "当前步骤尚未满足前置条件。"
    return st.button(
        button_label,
        key=key,
        disabled=disabled,
        help=help_text,
        type=button_type,
        use_container_width=True,
    )


def render_device_control_cluster(
    title: str,
    device_name: str,
    device_id: str,
    buttons: list[dict],
) -> None:
    """渲染设备侧控制面板。

    buttons: [{"label": "关闭舱门", "key": "btn_close_door", "status": "ready", "help": "..."}, ...]
    """
    st.markdown(
        f"""
<div class="device-control-cluster" style="
  background:var(--app-surface); border:1px solid var(--app-border);
  border-radius:12px; padding:14px 16px; margin:8px 0;
  box-shadow:0 4px 16px rgba(11,58,99,0.06);
">
  <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
    <span style="width:8px;height:8px;border-radius:50%;background:var(--app-cyan);"></span>
    <span style="font-weight:bold; font-size:0.9rem; color:var(--app-primary);">{_escape(title)}</span>
    <span style="font-size:0.75rem; color:var(--app-muted); margin-left:auto;">{_escape(device_name)}</span>
  </div>
  <div id="device-buttons-{_escape(device_id)}">
""",
        unsafe_allow_html=True,
    )
    for btn in buttons:
        render_control_button(
            label=btn["label"],
            key=btn["key"],
            disabled=btn.get("disabled", False),
            status=btn.get("status", "idle"),
            help_text=btn.get("help", ""),
            device_id=device_id,
            primary=btn.get("primary", False),
        )
    st.markdown("</div></div>", unsafe_allow_html=True)


def _instrument_assessment_values(
    state: dict,
    assessment_summary: dict | None = None,
) -> dict[str, object]:
    """Return instrument-panel assessment fields from one authoritative source."""
    summary = assessment_summary or {}
    score_value = summary["score"] if "score" in summary else state.get("score", 100)
    score = int(100 if score_value is None else score_value)
    deductions = list(summary.get("deductions", state.get("deductions", [])) or [])
    latest_reasons = [
        str(item.get("reason", "扣分记录"))
        for item in deductions[:3]
    ]
    latest_reason = "<br>".join(_escape(reason) for reason in latest_reasons) if latest_reasons else "暂无扣分"
    return {
        "score": score,
        "grade": summary.get("grade", state.get("grade", "优秀" if score >= 90 else "待评价")),
        "safety_status": summary.get("safety_status", state.get("safety_status", "规范")),
        "latest_reason": latest_reason,
    }


def render_instrument_panel(
    state: dict,
    mode: str = "arc",
    assessment_summary: dict | None = None,
) -> None:
    """渲染右侧仪器控制屏，模拟真实设备操作面板风格。

    显示：实验模式、当前阶段、关键参数（T/P/SOC/气氛）、采样状态、GC状态、评分。
    """
    current_state = state.get("current_state", "")
    if mode == "literature":
        t2 = float(state.get("temperature_t2_c", 25.0) or 25.0)
        pressure = float(state.get("pressure_kpa", 101.3) or 101.3)
        soc = state.get("selected_soc")
        atmosphere = (
            "N₂" if state.get("nitrogen_filled") else
            ("真空" if state.get("vacuum_done") and not state.get("nitrogen_filled") else "空气")
        )
        sampled = state.get("sampling_completed", {}) or {}
        sampled_count = sum(1 for v in sampled.values() if v)
        gc_status = "已完成" if state.get("gc_finished") else ("分析中" if state.get("gc_started") else "待分析")
    else:
        t2 = float(state.get("temperature", 25.0) or 25.0)
        pressure = float(state.get("pressure", 101.3) or 101.3)
        soc = state.get("selected_soc")
        atmosphere = (
            "N₂" if state.get("nitrogen_valve_open") else
            ("真空" if state.get("vacuum_valve_open") else "空气")
        )
        sampled_count = 1 if state.get("gas_bag_filled") else 0
        gc_status = "已完成" if state.get("gc_finished") else ("分析中" if state.get("gc_started") else "待分析")

    risk_level = "待评价"
    if state.get("lel_calculated"):
        risk_level = "已评价"
    elif state.get("lel_risk_evaluated"):
        risk_level = "已评价"

    assessment_view = _instrument_assessment_values(state, assessment_summary)
    score = int(assessment_view["score"])
    grade = str(assessment_view["grade"])
    safety_status = str(assessment_view["safety_status"])
    latest_reason = str(assessment_view["latest_reason"])

    st.markdown(
        f"""
<div style="
  background: linear-gradient(180deg, var(--app-surface-soft), var(--app-surface));
  border: 2px solid var(--app-border); border-radius: 14px;
  padding: 16px 18px; margin-bottom: 12px;
  box-shadow: 0 4px 18px rgba(11,58,99,0.08);
  font-family: 'Consolas', 'Microsoft YaHei', monospace;
">
  <div style="
    text-align: center; padding-bottom: 10px; margin-bottom: 12px;
    border-bottom: 1px solid var(--app-border);
    font-size: 1.05rem; font-weight: bold; color: var(--app-primary);
    letter-spacing: 2px;
  ">▌仪器控制屏</div>

  <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px 14px; font-size:0.85rem;">
    <div><span style="color:var(--app-muted)">实验模式</span><br>
      <b>{'文献装置' if mode == 'literature' else '教学 ARC'}</b></div>
    <div><span style="color:var(--app-muted)">当前阶段</span><br>
      <b style="color:var(--app-primary-light)">{_escape(state_label(current_state))}</b></div>
    <div><span style="color:var(--app-muted)">温度 T₂</span><br>
      <b style="color:{'var(--app-red)' if t2 > 80 else 'var(--app-text)'}">{t2:.1f} ℃</b></div>
    <div><span style="color:var(--app-muted)">舱内压力</span><br>
      <b>{pressure:.1f} kPa</b></div>
    <div><span style="color:var(--app-muted)">SOC</span><br>
      <b>{_escape(soc) if soc is not None else '—'}%</b></div>
    <div><span style="color:var(--app-muted)">舱内气氛</span><br>
      <b style="color:{'var(--app-cyan)' if atmosphere == 'N₂' else 'var(--app-orange)'}">{_escape(atmosphere)}</b></div>
    <div><span style="color:var(--app-muted)">采气进度</span><br>
      <b>{sampled_count}/4</b></div>
    <div><span style="color:var(--app-muted)">GC 状态</span><br>
      <b style="color:{'var(--app-green)' if gc_status == '已完成' else 'var(--app-muted)'}">{_escape(gc_status)}</b></div>
    <div><span style="color:var(--app-muted)">风险等级</span><br>
      <b>{_escape(risk_level)}</b></div>
    <div><span style="color:var(--app-muted)">当前得分</span><br>
      <b style="font-size:1.1rem; color:{'var(--app-green)' if score >= 90 else ('var(--app-orange)' if score >= 60 else 'var(--app-red)')}">{score} 分</b></div>
    <div><span style="color:var(--app-muted)">考核等级</span><br>
      <b>{_escape(grade)}</b></div>
    <div><span style="color:var(--app-muted)">规范状态</span><br>
      <b>{_escape(safety_status)}</b></div>
  </div>
  <div style="margin-top:12px;padding:10px 12px;border-top:1px solid var(--app-border);font-size:0.8rem;line-height:1.55;">
    <span style="color:var(--app-muted)">最近扣分原因</span><br>
    <b>{latest_reason}</b>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_logbook(logs: list[dict], max_entries: int = 10) -> None:
    """渲染实验记录本，模拟纸质实验记录风格。"""
    if not logs:
        st.markdown(
            """<div style="
  background:var(--app-surface-soft); border:1px dashed var(--app-border);
  border-radius:10px; padding:18px; text-align:center; color:var(--app-muted);
  font-size:0.9rem; margin:8px 0;
">📓 实验记录本 — 暂无操作记录</div>""",
            unsafe_allow_html=True,
        )
        return

    entries = []
    for entry in logs[:max_entries]:
        t = entry.get("time", "")
        action = entry.get("action", "")
        msg = entry.get("message", "")
        level = entry.get("level", "info")
        severity = entry.get("severity", "normal")

        icon_map = {"info": "📌", "error": "⚠️", "warning": "⚠"}
        icon = icon_map.get(level, "📌")

        if level == "error":
            row_style = "border-left: 3px solid var(--app-red); background: rgba(198,40,40,0.04);"
        else:
            row_style = "border-left: 3px solid var(--app-cyan);"

        entries.append(
            f"""<div style="{row_style} padding:8px 12px; margin:6px 0; border-radius:0 8px 8px 0; font-size:0.83rem;">
  <span style="color:var(--app-muted);float:right;">{_escape(t)}</span>
  <span>{icon} <b>{_escape(msg)}</b></span>
  <br><span style="color:var(--app-muted);font-size:0.78rem;">
    操作：{_escape(action)} | 类型：{_escape(level)}
  </span>
</div>"""
        )

    st.markdown(
        f"""<div style="
  background:var(--app-surface); border:1px solid var(--app-border);
  border-radius:12px; padding:14px; margin:8px 0;
  box-shadow:0 2px 10px rgba(11,58,99,0.05);
  max-height:340px; overflow-y:auto;
">
  <div style="
    font-weight:bold; font-size:0.95rem; color:var(--app-primary);
    padding-bottom:8px; margin-bottom:8px;
    border-bottom:1px solid var(--app-border);
  ">📓 实验记录本</div>
  {''.join(entries)}
</div>""",
        unsafe_allow_html=True,
    )


def render_experiment_timeline(
    steps: list[dict],
    active_step_index: int = -1,
) -> None:
    """渲染实验步骤时间轴。

    steps: [{"label": "选择 SOC", "status": "done|active|pending|blocked", "help": "说明"}, ...]
    """
    items = []
    for idx, step in enumerate(steps):
        status = step.get("status", "pending")
        if status == "done":
            dot = '<span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:var(--app-green);color:#fff;font-size:12px;flex-shrink:0;">✓</span>'
            line_color = "var(--app-green)"
            text_color = "var(--app-text)"
            text_decoration = ""
        elif status == "active":
            dot = '<span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:var(--app-primary-light);color:#fff;font-size:12px;flex-shrink:0;box-shadow:0 0 12px rgba(21,101,192,0.4);animation:ctrl-pulse 1.5s ease-in-out infinite;">▶</span>'
            line_color = "var(--app-primary-light)"
            text_color = "var(--app-primary-light)"
            text_decoration = ""
        elif status == "blocked":
            dot = '<span style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;border:2px solid var(--app-muted);color:var(--app-muted);font-size:10px;flex-shrink:0;">⊘</span>'
            line_color = "var(--app-muted)"
            text_color = "var(--app-muted)"
            text_decoration = ""
        else:
            dot = '<span style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;border:2px solid var(--app-border);color:var(--app-muted);font-size:10px;flex-shrink:0;">○</span>'
            line_color = "var(--app-border)"
            text_color = "var(--app-muted)"
            text_decoration = ""

        connector = ""
        if idx < len(steps) - 1:
            connector = f'<div style="width:2px;height:8px;background:{line_color};margin-left:10px;"></div>'

        items.append(
            f"""<div style="display:flex;gap:10px;align-items:flex-start;">
  {dot}
  <div>
    <div style="color:{text_color};font-size:0.82rem;font-weight:{'bold' if status == 'active' else 'normal'};{text_decoration}">{_escape(step['label'])}</div>
    {f'<div style="color:var(--app-muted);font-size:0.72rem;">{_escape(step.get("help", ""))}</div>' if step.get('help') else ''}
  </div>
</div>
{connector}"""
        )

    st.markdown(
        f"""<div style="
  background:var(--app-surface); border:1px solid var(--app-border);
  border-radius:12px; padding:14px 16px;
  box-shadow:0 2px 10px rgba(11,58,99,0.05);
  max-height:480px; overflow-y:auto;
">
  <div style="font-weight:bold;font-size:0.9rem;color:var(--app-primary);margin-bottom:10px;">🧪 实验步骤</div>
  {"<br>".join(items)}
</div>""",
        unsafe_allow_html=True,
    )


def render_monitor_screen(
    t2: float,
    pressure: float,
    heating_rate: float = 0.0,
    voltage: float | None = None,
    gc_done: bool = False,
    theme_mode: str = "light",
) -> None:
    """渲染数据采集监控屏，模拟 DAQ 显示界面。"""
    st.markdown(
        f"""<div style="
  background: linear-gradient(180deg, #0a1620, #142430);
  border: 3px solid #2a4050; border-radius: 14px;
  padding: 16px 18px; margin:10px 0;
  box-shadow: inset 0 2px 8px rgba(0,0,0,0.4), 0 4px 16px rgba(11,58,99,0.15);
  font-family: 'Consolas', 'Courier New', monospace;
  color: #8ecbff;
">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
    <span style="font-size:0.8rem; color:#608090;">DAQ 数据采集仪</span>
    <span style="font-size:0.7rem; color:#405860;">CH1~CH6</span>
  </div>
  <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px 16px; font-size:0.82rem;">
    <div>
      <span style="color:#6090b0;">T1 [壳表]</span><br>
      <span style="color:#a0d0f0; font-size:1.1rem;">25.0 ℃</span>
    </div>
    <div>
      <span style="color:#f0a060;">T2 [主控]</span><br>
      <span style="color:{'#ff6b6b' if t2 > 80 else '#f0a060'}; font-size:1.2rem;">{t2:.1f} ℃</span>
    </div>
    <div>
      <span style="color:#6090b0;">T3 [壳体]</span><br>
      <span style="color:#a0d0f0; font-size:1.1rem;">25.0 ℃</span>
    </div>
    <div>
      <span style="color:#60b0d0;">压力 P</span><br>
      <span style="color:#a0d0f0; font-size:1.1rem;">{pressure:.1f} kPa</span>
    </div>
    <div>
      <span style="color:#60b0d0;">dT/dt</span><br>
      <span style="color:#a0d0f0; font-size:1.1rem;">{heating_rate:.1f} ℃/min</span>
    </div>
    <div>
      <span style="color:#60b0d0;">GC</span><br>
      <span style="color:{'#7bd88f' if gc_done else '#608090'}; font-size:1.1rem;">{'完成' if gc_done else '待机'}</span>
    </div>
  </div>
  <div style="margin-top:10px; padding-top:8px; border-top:1px solid #2a4050;">
    <span style="font-size:0.7rem; color:#405860;">
      SAMPLE RATE 1Hz | CHANNELS 6 | STATUS {_escape('REC' if gc_done else 'MON')}
    </span>
  </div>
</div>""",
        unsafe_allow_html=True,
    )


def render_current_step_guide(state_key: str) -> None:
    """渲染当前步骤推荐操作卡片。"""
    desc = state_description(state_key)
    label = state_label(state_key)
    st.markdown(
        f"""<div style="
  background: linear-gradient(135deg, rgba(0,131,143,0.08), rgba(21,101,192,0.06));
  border: 1.5px solid var(--app-cyan); border-radius: 10px;
  padding: 12px 16px; margin: 8px 0;
">
  <div style="font-size:0.78rem;color:var(--app-muted);margin-bottom:4px;">📋 当前步骤</div>
  <div style="font-weight:bold;color:var(--app-primary);font-size:0.95rem;">{_escape(label)}</div>
  <div style="color:var(--app-text);font-size:0.82rem;margin-top:4px;line-height:1.5;">{_escape(desc)}</div>
</div>""",
        unsafe_allow_html=True,
    )
