"""
app/utils/chart_utils.py —— Plotly 图表工具

提供气体组成、可燃占比、风险仪表盘、场景对比和 LFL 贡献等图表函数。
"""

from __future__ import annotations

from typing import Mapping

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.utils.app_config import GAS_DISPLAY_NAMES, RISK_LEVEL_CONFIG
from app.utils.ui_theme import get_current_theme, get_plotly_theme_tokens


PLOTLY_TEMPLATE = "plotly_white"
COLOR_FLAMMABLE = "#1565c0"
COLOR_NON_FLAMMABLE = "#90a4ae"
COLOR_ACCENT = "#00838f"


def _display_gas_name(gas: str) -> str:
    """返回气体分子式的显示名。"""
    return GAS_DISPLAY_NAMES.get(gas, gas)


def _composition_df(
    gas_composition: Mapping[str, float] | None,
    flammable_gases: set[str] | None = None,
) -> pd.DataFrame:
    """将组成字典转换为标准绘图 DataFrame。"""
    rows = []
    if not gas_composition:
        return pd.DataFrame(columns=["气体", "显示气体", "体积百分比", "类别"])

    flammable_gases = flammable_gases or set()
    for gas, value in gas_composition.items():
        try:
            val = float(value)
        except (TypeError, ValueError):
            continue
        if pd.isna(val) or val < 0:
            continue
        rows.append(
            {
                "气体": gas,
                "显示气体": _display_gas_name(gas),
                "体积百分比": val,
                "类别": "可燃组分" if gas in flammable_gases else "不可燃/其他",
            }
        )
    return pd.DataFrame(rows)


def get_plotly_layout_theme(theme_mode: str = "light") -> dict:
    """返回统一 Plotly layout 主题。"""
    t = get_plotly_theme_tokens(theme_mode)
    return {
        "template": "plotly_white",
        "font": {"family": "Arial, Microsoft YaHei, sans-serif", "color": t["font_color"]},
        "paper_bgcolor": t["paper_bgcolor"],
        "plot_bgcolor": t["plot_bgcolor"],
        "xaxis": {"gridcolor": t["grid_color"], "linecolor": t["axis_color"], "tickfont": {"color": t["font_color"]}},
        "yaxis": {"gridcolor": t["grid_color"], "linecolor": t["axis_color"], "tickfont": {"color": t["font_color"]}},
        "legend": {"font": {"color": t["font_color"]}},
        "colorway": [t["primary"], t["cyan"], t["green"], t["yellow"], t["orange"], t["red"]],
    }


def _empty_figure(message: str, theme_mode: str = "light") -> go.Figure:
    """生成空数据提示图。"""
    fig = go.Figure()
    layout = get_plotly_layout_theme(theme_mode)
    layout["xaxis"] = {"visible": False}
    layout["yaxis"] = {"visible": False}
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 15, "color": get_plotly_theme_tokens(theme_mode)["muted"]},
    )
    fig.update_layout(
        **layout,
        height=320,
        margin={"l": 30, "r": 30, "t": 56, "b": 30},
    )
    return fig


def apply_common_layout(
    fig: go.Figure,
    title: str = "",
    height: int = 360,
    theme_mode: str | None = None,
) -> go.Figure:
    """统一 Plotly 图表样式。"""
    mode = theme_mode or get_current_theme()
    fig.update_layout(
        **get_plotly_layout_theme(mode),
        title={"text": title, "x": 0.02, "xanchor": "left"},
        height=height,
        margin={"l": 40, "r": 28, "t": 62, "b": 42},
        legend_title_text="",
    )
    return fig


def plot_gas_composition_bar(
    gas_composition: Mapping[str, float] | None,
    flammable_gases: set[str] | None = None,
    title: str = "气体组成柱状图",
    theme_mode: str | None = None,
) -> go.Figure:
    """绘制气体组成柱状图。"""
    df = _composition_df(gas_composition, flammable_gases)
    if df.empty:
        return _empty_figure("暂无可绘制的气体组成数据", theme_mode or get_current_theme())
    fig = px.bar(
        df,
        x="显示气体",
        y="体积百分比",
        color="类别",
        color_discrete_map={
            "可燃组分": COLOR_FLAMMABLE,
            "不可燃/其他": COLOR_NON_FLAMMABLE,
        },
        text=df["体积百分比"].map(lambda v: f"{v:.1f}%"),
        hover_data={"气体": True, "类别": True, "体积百分比": ":.2f", "显示气体": False},
        labels={"显示气体": "气体", "体积百分比": "体积百分比 (% vol)"},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(title="体积百分比 (% vol)", rangemode="tozero")
    fig.update_xaxes(title="")
    return apply_common_layout(fig, title=title, height=360, theme_mode=theme_mode)


def plot_gas_composition_donut(
    gas_composition: Mapping[str, float] | None,
    flammable_gases: set[str] | None = None,
    title: str = "气体组成环形图",
    theme_mode: str | None = None,
) -> go.Figure:
    """绘制气体组成环形图。"""
    df = _composition_df(gas_composition, flammable_gases)
    if df.empty:
        return _empty_figure("暂无可绘制的气体组成数据", theme_mode or get_current_theme())
    colors = [COLOR_FLAMMABLE if c == "可燃组分" else COLOR_NON_FLAMMABLE for c in df["类别"]]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=df["显示气体"],
                values=df["体积百分比"],
                hole=0.55,
                marker={"colors": colors, "line": {"color": "#ffffff", "width": 2}},
                hovertemplate="%{label}<br>体积百分比: %{value:.2f}% vol<extra></extra>",
            )
        ]
    )
    fig.update_traces(textposition="inside", textinfo="label+percent")
    return apply_common_layout(fig, title=title, height=360, theme_mode=theme_mode)


def plot_flammable_ratio(
    flammable_fraction: float,
    title: str = "可燃 / 不可燃组分占比",
    theme_mode: str | None = None,
) -> go.Figure:
    """绘制可燃和不可燃组分占比图。"""
    safe_value = max(0.0, float(flammable_fraction or 0.0))
    non_value = max(0.0, 100.0 - safe_value)
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["可燃组分", "不可燃/其他"],
                values=[safe_value, non_value],
                hole=0.58,
                marker={
                    "colors": [COLOR_FLAMMABLE, COLOR_NON_FLAMMABLE],
                    "line": {"color": "#ffffff", "width": 2},
                },
                hovertemplate="%{label}: %{value:.2f}% vol<extra></extra>",
            )
        ]
    )
    fig.update_traces(textinfo="label+percent")
    return apply_common_layout(fig, title=title, height=320, theme_mode=theme_mode)


def plot_risk_gauge(
    risk_ratio: float | None,
    title: str = "风险比值 R 教学仪表盘",
    theme_mode: str | None = None,
) -> go.Figure:
    """绘制风险 R 值仪表盘。"""
    mode = theme_mode or get_current_theme()
    tokens = get_plotly_theme_tokens(mode)
    try:
        value = float(risk_ratio)
    except (TypeError, ValueError):
        value = 0.0
    if pd.isna(value):
        value = 0.0
    value = max(0.0, value)
    axis_max = max(1.5, value * 1.25 if value > 1.2 else 1.5)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"valueformat": ".3f", "font": {"size": 32, "color": tokens["primary"]}},
            title={"text": "R = C / LFL_mix", "font": {"size": 14}},
            gauge={
                "axis": {"range": [0, axis_max], "tickwidth": 1, "tickcolor": "#607485"},
                "bar": {"color": tokens["primary"]},
                "bgcolor": tokens["surface"],
                "borderwidth": 1,
                "bordercolor": "#d9e4ef",
                "steps": [
                    {"range": [0, 0.25], "color": RISK_LEVEL_CONFIG["低风险"]["bg"]},
                    {"range": [0.25, 0.5], "color": RISK_LEVEL_CONFIG["关注"]["bg"]},
                    {"range": [0.5, 1.0], "color": RISK_LEVEL_CONFIG["较高风险"]["bg"]},
                    {"range": [1.0, axis_max], "color": RISK_LEVEL_CONFIG["高风险"]["bg"]},
                ],
                "threshold": {
                    "line": {"color": "#c62828", "width": 4},
                    "thickness": 0.78,
                    "value": 1.0,
                },
            },
        )
    )
    return apply_common_layout(fig, title=title, height=340, theme_mode=mode)


def plot_scenario_comparison(
    scenario_results: pd.DataFrame | None,
    title: str = "不同虚拟场景 R 值对比",
    theme_mode: str | None = None,
) -> go.Figure:
    """绘制同一样本在不同虚拟场景下的 R 值对比。"""
    if scenario_results is None or scenario_results.empty:
        return _empty_figure("暂无场景对比数据", theme_mode or get_current_theme())
    df = scenario_results.copy()
    fig = px.bar(
        df,
        x="场景",
        y="风险比值 R",
        color="教学风险等级",
        color_discrete_map={k: v["color"] for k, v in RISK_LEVEL_CONFIG.items()},
        hover_data={
            "空间浓度 (% vol)": ":.4f",
            "LFL_mix (% vol)": ":.2f",
            "教学风险等级": True,
        },
        labels={"风险比值 R": "风险比值 R"},
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color="#c62828", annotation_text="R = 1")
    fig.update_xaxes(title="")
    fig.update_yaxes(title="风险比值 R", rangemode="tozero")
    return apply_common_layout(fig, title=title, height=380, theme_mode=theme_mode)


def plot_lfl_contribution(
    normalized: Mapping[str, float] | None,
    lfl_constants: Mapping[str, float] | None,
    title: str = "y_i / LFL_i 贡献柱状图",
    theme_mode: str | None = None,
) -> go.Figure:
    """绘制 Le Chatelier 求和项贡献图。"""
    rows = []
    if normalized and lfl_constants:
        for gas, y_i in normalized.items():
            lfl_i = lfl_constants.get(gas)
            if lfl_i is None:
                continue
            try:
                contribution = float(y_i) / float(lfl_i)
            except (TypeError, ValueError, ZeroDivisionError):
                continue
            rows.append(
                {
                    "气体": _display_gas_name(gas),
                    "归一化 y_i": float(y_i),
                    "LFL_i": float(lfl_i),
                    "y_i / LFL_i": contribution,
                }
            )
    df = pd.DataFrame(rows)
    if df.empty:
        return _empty_figure("暂无可绘制的 LFL 贡献数据", theme_mode or get_current_theme())
    fig = px.bar(
        df,
        x="气体",
        y="y_i / LFL_i",
        color="气体",
        color_discrete_sequence=px.colors.qualitative.Safe,
        text=df["y_i / LFL_i"].map(lambda v: f"{v:.4f}"),
        hover_data={"归一化 y_i": ":.4f", "LFL_i": ":.2f", "y_i / LFL_i": ":.5f"},
        labels={"y_i / LFL_i": "贡献值 y_i / LFL_i"},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(title="")
    fig.update_yaxes(title="贡献值", rangemode="tozero")
    return apply_common_layout(fig, title=title, height=360, theme_mode=theme_mode)


def _source_note(fig: go.Figure, text: str) -> None:
    fig.add_annotation(
        text=f"数据来源：{text}",
        x=1,
        y=-0.22,
        xref="paper",
        yref="paper",
        showarrow=False,
        align="right",
        font={"size": 12},
    )


def plot_temperature_curve(curve_df: pd.DataFrame, theme_mode: str = "light") -> go.Figure:
    if curve_df is None or curve_df.empty:
        return _empty_figure("暂无 ARC 温度曲线数据", theme_mode)
    fig = px.line(curve_df, x="time_min", y="temperature_c", markers=True, labels={"time_min": "时间 (min)", "temperature_c": "温度 (°C)"})
    _source_note(fig, "教学插值 / 模拟曲线，非文献原始数据")
    return apply_common_layout(fig, "ARC 温度演示曲线", 320, theme_mode)


def plot_heating_rate_curve(curve_df: pd.DataFrame, theme_mode: str = "light") -> go.Figure:
    if curve_df is None or curve_df.empty:
        return _empty_figure("暂无温升速率数据", theme_mode)
    fig = px.line(curve_df, x="time_min", y="heating_rate_c_min", markers=True, labels={"time_min": "时间 (min)", "heating_rate_c_min": "dT/dt (°C/min)"})
    _source_note(fig, "教学插值 / 模拟曲线，非文献原始数据")
    return apply_common_layout(fig, "温升速率演示曲线", 300, theme_mode)


def plot_pressure_curve(curve_df: pd.DataFrame, theme_mode: str = "light") -> go.Figure:
    if curve_df is None or curve_df.empty:
        return _empty_figure("暂无压力曲线数据", theme_mode)
    fig = px.line(curve_df, x="time_min", y="pressure_kpa", markers=True, labels={"time_min": "时间 (min)", "pressure_kpa": "压力 (kPa)"})
    _source_note(fig, "压力变化为教学可视化模拟数据，非文献原始曲线")
    return apply_common_layout(fig, "20 L 密封罐压力演示曲线", 320, theme_mode)


def plot_gc_chromatogram(peaks_df: pd.DataFrame, theme_mode: str = "light") -> go.Figure:
    if peaks_df is None or peaks_df.empty:
        return _empty_figure("暂无 GC 色谱峰数据", theme_mode)
    fig = go.Figure()
    for _, row in peaks_df.iterrows():
        rt = float(row.get("retention_time_min", 0))
        height = float(row.get("peak_height", 0))
        gas = str(row.get("gas", "未知"))
        fig.add_trace(go.Scatter(x=[rt - 0.08, rt, rt + 0.08], y=[0, height, 0], mode="lines", name=gas, hovertemplate=f"{gas}<br>保留时间: {rt:.2f} min<extra></extra>"))
    fig.update_xaxes(title="保留时间 (min)")
    fig.update_yaxes(title="响应强度 (a.u.)")
    _source_note(fig, "教学模拟 GC 峰，用于界面演示")
    return apply_common_layout(fig, "GC 气相色谱教学模拟图", 320, theme_mode)


def plot_gas_volume_comparison(df: pd.DataFrame, theme_mode: str = "light") -> go.Figure:
    if df is None or df.empty:
        return _empty_figure("暂无产气量对比数据", theme_mode)
    fig = px.bar(df, x="gas", y="volume_l", color="source_type", labels={"gas": "气体", "volume_l": "体积 (L)", "source_type": "来源类型"})
    _source_note(fig, "教学演示，不作为真实文献结果")
    return apply_common_layout(fig, "产气量教学演示对比", 320, theme_mode)


def plot_lel_risk_timeline(df: pd.DataFrame, theme_mode: str = "light") -> go.Figure:
    if df is None or df.empty:
        return _empty_figure("暂无可燃风险时间线数据", theme_mode)
    fig = px.line(df, x="step", y="risk_ratio", markers=True, labels={"step": "阶段", "risk_ratio": "R = C / LFL_mix"})
    fig.add_hline(y=1.0, line_dash="dash", line_color=get_plotly_theme_tokens(theme_mode)["red"], annotation_text="R = 1")
    _source_note(fig, "教学模型结果，不用于真实工程防爆设计")
    return apply_common_layout(fig, "可燃风险评价时间线", 320, theme_mode)


def plot_zeng_key_point_comparison(
    key_points_df: pd.DataFrame,
    metric: str | None = None,
    title: str = "不同 SOC 热失控关键节点对比",
    y_label: str | None = None,
    theme_mode: str = "light",
) -> go.Figure:
    """绘制曾垂辉等 2026 表 2 SOC 对比图。"""
    if key_points_df is None or key_points_df.empty:
        return _empty_figure("暂无可绘制的文献关键节点数据", theme_mode)
    df = key_points_df.copy()
    if "soc_pct" not in df.columns:
        return _empty_figure("缺少 SOC 字段，无法绘制文献关键节点对比", theme_mode)

    metric_labels = {
        "vent_time_s": "喷阀时间 (s)",
        "thermal_runaway_time_s": "热失控时间 (s)",
        "max_temperature_c": "最高温度 (℃)",
        "max_heating_rate_c_per_s": "最大温升速率 (℃/s)",
    }
    if metric:
        if metric not in df.columns:
            return _empty_figure(f"缺少字段 {metric}，无法绘制该指标", theme_mode)
        df[metric] = pd.to_numeric(df[metric], errors="coerce")
        df = df.dropna(subset=[metric])
        if df.empty:
            return _empty_figure("暂无可绘制的文献关键节点数据", theme_mode)
        df["SOC"] = df["soc_pct"].astype(str) + "%"
        fig = px.bar(
            df,
            x="SOC",
            y=metric,
            color="SOC",
            text=df[metric].map(lambda v: f"{v:g}"),
            labels={metric: y_label or metric_labels.get(metric, metric)},
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_yaxes(title=y_label or metric_labels.get(metric, metric), rangemode="tozero")
        fig.update_xaxes(title="SOC")
        _source_note(fig, "曾垂辉等，2026，表 2；仅用于二维教学仿真数据回放")
        return apply_common_layout(fig, title, 330, theme_mode)

    available_metrics = [col for col in metric_labels if col in df.columns]
    if not available_metrics:
        return _empty_figure("暂无可绘制的文献关键节点数据", theme_mode)

    long_rows = []
    for _, row in df.iterrows():
        soc = f"{row.get('soc_pct')}%"
        for col in available_metrics:
            value = pd.to_numeric(row.get(col), errors="coerce")
            if pd.isna(value):
                continue
            long_rows.append({"SOC": soc, "指标": metric_labels[col], "数值": float(value)})
    long_df = pd.DataFrame(long_rows)
    if long_df.empty:
        return _empty_figure("暂无可绘制的文献关键节点数据", theme_mode)
    fig = px.line(
        long_df,
        x="SOC",
        y="数值",
        color="指标",
        markers=True,
        labels={"数值": "数值", "SOC": "SOC"},
    )
    fig.update_yaxes(title="数值", rangemode="tozero")
    fig.update_xaxes(title="SOC")
    _source_note(fig, "曾垂辉等，2026，表 2；仅用于二维教学仿真数据回放")
    return apply_common_layout(fig, title, 360, theme_mode)


def plot_zeng_sampling_timeline(key_points_df: pd.DataFrame, soc: int | str | None = None, theme_mode: str = "light") -> go.Figure:
    """绘制文献装置采气阶段时间轴。"""
    if key_points_df is None or key_points_df.empty:
        return _empty_figure("暂无采气阶段时间轴数据", theme_mode)
    if "soc_pct" not in key_points_df.columns:
        return _empty_figure("缺少 SOC 字段，无法绘制采气阶段时间轴", theme_mode)
    if soc is None:
        soc = key_points_df["soc_pct"].dropna().iloc[0] if not key_points_df["soc_pct"].dropna().empty else ""
    df = key_points_df[key_points_df["soc_pct"].astype(str) == str(soc)].copy()
    if df.empty:
        return _empty_figure("当前 SOC 暂无关键节点数据", theme_mode)
    row = df.iloc[0]
    events = [
        {"阶段": "T2=100℃", "time_s": None, "说明": "文献表 3 采气阶段；具体时间未由用户提供"},
        {"阶段": "喷阀", "time_s": row.get("vent_time_s"), "说明": f"喷阀温度 {row.get('vent_temperature_c')}℃"},
        {"阶段": "热失控", "time_s": row.get("thermal_runaway_time_s"), "说明": "0%SOC 未热失控" if str(row.get("thermal_runaway_observed")).lower() == "false" else "热失控时间"},
        {"阶段": "反应结束", "time_s": None, "说明": "压力稳定阶段；具体时间未由用户提供"},
    ]
    timeline = pd.DataFrame(events)
    timeline["time_s"] = pd.to_numeric(timeline["time_s"], errors="coerce")
    plot_df = timeline.dropna(subset=["time_s"])
    if plot_df.empty:
        return _empty_figure("当前 SOC 暂无可定位的时间节点", theme_mode)
    plot_df = plot_df.copy()
    plot_df["lane"] = "采气阶段"
    fig = px.scatter(
        plot_df,
        x="time_s",
        y="lane",
        color="阶段",
        size=[18] * len(plot_df),
        hover_data={"说明": True, "time_s": ":.0f"},
        labels={"time_s": "时间 (s)", "lane": ""},
    )
    fig.update_yaxes(visible=False)
    fig.update_xaxes(title="时间 (s)")
    _source_note(fig, "喷阀和热失控节点来自表 2；T2=100℃和反应结束仅作阶段提示")
    return apply_common_layout(fig, f"{soc}%SOC 采气阶段时间轴", 260, theme_mode)


def plot_zeng_stage_gas_trends(gc_df: pd.DataFrame, theme_mode: str = "light") -> go.Figure:
    """绘制表 3 阶段产气变化；无数值时明确显示待补充。"""
    if gc_df is None or gc_df.empty:
        return _empty_figure("暂无表 3 气体组分数据", theme_mode)
    df = gc_df.copy()
    if "volume_fraction_pct" not in df.columns:
        return _empty_figure("缺少气体组分数值字段，无法绘制阶段变化", theme_mode)
    df["volume_fraction_pct"] = pd.to_numeric(df["volume_fraction_pct"], errors="coerce")
    df = df.dropna(subset=["volume_fraction_pct"])
    if df.empty:
        return _empty_figure("表 3 气体组分数值未录入，当前仅有 pending_user_input 占位", theme_mode)
    fig = px.line(
        df,
        x="sampling_stage",
        y="volume_fraction_pct",
        color="gas_component",
        line_dash="soc_pct",
        markers=True,
        labels={"sampling_stage": "采样阶段", "volume_fraction_pct": "体积百分比 (% vol)", "gas_component": "气体"},
    )
    _source_note(fig, "仅当用户录入表 3 明确数值后绘制；不得从图像猜测")
    return apply_common_layout(fig, "阶段性 H2 / CO2 / CO / 碳氢化合物变化", 360, theme_mode)
