"""文献装置模式 SVG 渲染工具 —— 增强版二维可视化。

提供防爆舱-加热模块热失控产气教学演示的完整二维装置图，包含：
- 防爆舱体（观察窗、铰链门、舱壁强化结构）
- 方壳 LFP 电池（电极耳 + 极耳标识）
- 加热模块（虚拟加热状态和蛇形示意）
- 隔热板（舱体下方隔离）
- 热电偶 T1/T2/T3（含温度读数）
- 电压采集线（V+/V-/GND 双线）
- 压力传感器（模拟表盘指针）
- 真空泵 + 真空管路和阀门
- 氮气瓶 + N₂ 管路和阀门
- 集气袋（采样口、采样管路）
- GC 气相色谱仪（色谱屏 + 状态指示灯）
- 数据采集电脑（DAQ 屏幕 + 曲线显示）
- 采样阶段指示灯（一采/二采/三采/四采）
- 加热/喷阀/热失控/采气/GC 状态反馈
"""

from __future__ import annotations

import html
import math

from app.utils.lab_connections import (
    LabConnection,
    render_connection_legend,
    render_connection_paths,
    render_port_debug_nodes,
    validate_connection_endpoints,
)


_HAS_COLORS = False  # 仅在 run_test 时可能被覆盖

THEME_COLORS = {
    "chamber_fill": "var(--app-surface-soft)",
    "chamber_stroke": "var(--equipment-stroke)",
    "cell_normal": "var(--app-yellow)",
    "cell_heating": "var(--app-orange)",
    "cell_runaway": "var(--app-red)",
    "heat_plate": "var(--app-orange)",
    "heat_wire": "var(--app-yellow)",
    "insulation": "var(--app-surface-soft)",
    "pipe_idle": "var(--app-muted)",
    "pipe_n2": "var(--app-cyan)",
    "pipe_vac": "var(--app-muted)",
    "pipe_sample": "var(--app-orange)",
    "tc_line": "var(--app-cyan)",
    "tc_t2_hot": "var(--app-orange)",
    "voltage_vplus": "var(--app-green)",
    "voltage_vminus": "var(--app-red)",
    "gc_peak": "var(--app-cyan)",
    "led_green": "var(--app-green)",
    "led_orange": "var(--app-orange)",
    "led_muted": "var(--app-muted)",
    "panel_bg": "var(--app-surface)",
    "panel_border": "var(--app-border)",
}

LITERATURE_LAYOUT = {
    "viewbox": (1180, 760),
    "anchors": {
        "vacuum": {"out": (148, 476)},
        "nitrogen": {"out": (150, 270)},
        "chamber": {
            "vacuum_in": (306, 414),
            "nitrogen_in": (306, 304),
            "sample_out": (612, 382),
            "voltage_out": (500, 294),
            "pressure_out": (564, 336),
            "arc_monitor": (612, 242),
        },
        "bag": {"in": (780, 382), "out": (864, 396)},
        "gc": {"in": (904, 418), "out": (1048, 430), "data_out": (1064, 426)},
        "ms": {"in": (1048, 470), "data_out": (1000, 518)},
        "daq": {"temperature_in": (824, 224), "pressure_in": (824, 286), "data_out": (888, 282)},
        "computer": {"data_in": (928, 518)},
        "arc": {"signal_in": (684, 234)},
    },
}

LITERATURE_PORTS = LITERATURE_LAYOUT["anchors"]


def _lit_anchor(device: str, port: str) -> tuple[int, int]:
    """Return an absolute literature-canvas anchor."""
    return LITERATURE_LAYOUT["anchors"][device][port]


def _lit_path(start: tuple[int, int], c1: tuple[int, int], c2: tuple[int, int], end: tuple[int, int]) -> str:
    """Build a cubic SVG path from literature-canvas anchors."""
    return f"M{start[0]} {start[1]} C{c1[0]} {c1[1]} {c2[0]} {c2[1]} {end[0]} {end[1]}"


def _render_lit_ports(specs: list[tuple[str, str, str]]) -> str:
    """Render port nodes that visually cover literature connection endpoints."""
    rows = []
    for device, port, kind in specs:
        x, y = _lit_anchor(device, port)
        fill = "var(--app-cyan)" if kind == "gas" else "var(--app-primary-light)"
        if kind == "vacuum":
            fill = "var(--app-muted)"
        rows.append(
            f'<circle cx="{x}" cy="{y}" r="7" fill="{fill}" '
            'stroke="var(--equipment-stroke)" stroke-width="1.8"/>'
        )
    return "\n".join(rows)


def _e(value: object) -> str:
    """HTML 转义。"""
    return html.escape("" if value is None else str(value))


_STATE_LABELS = {
    "soc_selection": "SOC 选择",
    "cell_loaded": "电池已放入",
    "sensors_placed": "传感器已布置",
    "chamber_closed": "舱门已关闭",
    "vacuuming": "抽真空中",
    "nitrogen_filled": "氮气已充入",
    "heating": "加热中",
    "t2_100": "T₂ 达到 100℃",
    "venting": "安全阀喷阀",
    "temperature_peak": "温度峰值",
    "pressure_stable": "压力稳定",
    "sampling_complete": "采气完成",
    "gc_analysis": "GC 分析中",
    "lel_risk_evaluation": "可燃风险评价",
    "report_generated": "报告已生成",
}


def _state_label(state_key: str) -> str:
    """Return a user-facing Chinese state label for SVG text."""
    return _STATE_LABELS.get(state_key, "按流程进行")


def _active(value: bool) -> str:
    """返回 CSS class active 或空。"""
    return "active" if value else ""


def _render_compact_connection_legend(x: int, y: int) -> str:
    """Render a compact literature-canvas legend that does not cover devices."""
    return f"""
<g id="connection-legend" class="connection-legend" transform="translate({x} {y})">
  <rect x="0" y="0" width="220" height="92" rx="8" class="legend-bg"/>
  <text x="14" y="22" class="device-label legend-title">连线图例</text>
  <path d="M16 42 L72 42" class="connection-line physical"/>
  <text x="86" y="46" class="pipeline-label">实线：已连接</text>
  <path d="M16 60 L72 60" class="connection-line physical active"/>
  <text x="86" y="64" class="pipeline-label">虚线：当前作用连接</text>
  <path d="M16 78 L72 78" class="connection-line alert"/>
  <text x="86" y="82" class="pipeline-label">红色：异常 / 违规连接</text>
</g>
"""


def _render_chamber_body(
    x: float, y: float, w: float, h: float,
    door_closed: bool, atmosphere: str,
    cell_loaded: bool, heating: bool, runaway: bool,
) -> str:
    """渲染防爆舱体外壳（含加强筋、观察窗、舱门状态）。"""
    door_stroke = "var(--app-green)" if door_closed else "var(--app-orange)"
    door_dash = "0" if door_closed else "8 5"
    door_label = "舱门已关闭 ✓" if door_closed else "⚠ 舱门未关闭"

    # 舱体加强筋
    ribs = "".join([
        f'<line x1="{x + 38 + i * 44}" y1="{y + 18}" x2="{x + 38 + i * 44}" y2="{y + h - 18}" '
        f'stroke="var(--app-border)" stroke-width="0.8" opacity="0.5"/>'
        for i in range(6)
    ])

    return f"""<!-- 防爆舱体 -->
  <g id="explosion-chamber">
    <!-- 舱体外壳 -->
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="3"/>
    <!-- 舱体顶部遮罩 -->
    <rect x="{x + 6}" y="{y + 3}" width="{w - 12}" height="14" rx="8" fill="var(--app-surface)" opacity="0.7"/>
    <!-- 加强筋 -->
    {ribs}
    <!-- 舱体内壁 -->
    <rect x="{x + 16}" y="{y + 16}" width="{w - 32}" height="{h - 32}" rx="8" fill="var(--app-surface)" stroke="var(--app-border)" stroke-width="1.5"/>
    <!-- 舱门区域 -->
    <rect x="{x + 22}" y="{y + 24}" width="130" height="82" rx="8"
      fill="var(--app-surface-soft)" stroke="{door_stroke}" stroke-width="4"
      stroke-dasharray="{door_dash}"/>
    <!-- 观察窗 -->
    <rect x="{x + 44}" y="{y + 36}" width="84" height="50" rx="6"
      fill="rgba(86,180,211,0.15)" stroke="var(--app-cyan)" stroke-width="2"/>
    <!-- 观察窗十字线 -->
    <line x1="{x + 86}" y1="{y + 36}" x2="{x + 86}" y2="{y + 86}" stroke="var(--app-cyan)" stroke-width="0.5" opacity="0.4"/>
    <line x1="{x + 44}" y1="{y + 61}" x2="{x + 128}" y2="{y + 61}" stroke="var(--app-cyan)" stroke-width="0.5" opacity="0.4"/>
    <!-- 舱门铰链（左侧） -->
    <rect x="{x + 16}" y="{y + 44}" width="6" height="14" rx="2" fill="var(--app-muted)"/>
    <rect x="{x + 16}" y="{y + 72}" width="6" height="14" rx="2" fill="var(--app-muted)"/>
    <!-- 舱门状态 -->
    <text x="{x + 87}" y="{y + 112}" text-anchor="middle" font-size="13">{_e(door_label)}</text>
    <!-- 舱体铭牌 -->
    <text x="{x + 188}" y="{y + 18}" text-anchor="middle" font-size="15" font-weight="bold">防爆舱体</text>
    <!-- 气氛指示 -->
    <text x="{x + 250}" y="{y + 38}" text-anchor="middle" font-size="12">气氛 {_e(atmosphere)}</text>
  </g>"""


def _render_prismatic_cell(
    x: float, y: float, soc: object, cell_loaded: bool,
    heating: bool, runaway: bool,
) -> str:
    """渲染方壳磷酸铁锂电池样品。"""
    if not cell_loaded:
        heat_opacity = "0.08"
        cell_fill = "var(--app-muted)"
        opacity = "0.2"
    else:
        heat_opacity = "0.82" if runaway else ("0.55" if heating else "0.12")
        cell_fill = "var(--app-red)" if runaway else ("var(--app-orange)" if heating else "var(--app-yellow)")
        opacity = "1"

    soc_text = f"SOC {_e(soc)}%" if soc is not None else "未选择 SOC"

    return f"""<!-- 方壳磷酸铁锂电池 -->
  <g id="prismatic-lfp-cell" opacity="{opacity}">
    <!-- 热辐射光晕 -->
    <ellipse cx="{x}" cy="{y}" rx="88" ry="56" fill="var(--app-orange)"
      opacity="{heat_opacity}" filter="url(#literature-heat-glow)"/>
    <!-- 电池主体（方壳） -->
    <rect x="{x - 42}" y="{y - 42}" width="84" height="72" rx="8"
      fill="{cell_fill}" stroke="var(--equipment-stroke)" stroke-width="2.5"/>
    <!-- 电池上表面高光 -->
    <rect x="{x - 38}" y="{y - 38}" width="76" height="12" rx="4"
      fill="rgba(255,255,255,0.25)"/>
    <!-- 极耳（负极/左） -->
    <rect x="{x - 31}" y="{y - 52}" width="18" height="12" rx="2"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <text x="{x - 22}" y="{y - 44}" text-anchor="middle" font-size="7">(−)</text>
    <!-- 极耳（正极/右） -->
    <rect x="{x + 12}" y="{y - 52}" width="18" height="12" rx="2"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <text x="{x + 21}" y="{y - 44}" text-anchor="middle" font-size="7">(+)</text>
    <!-- 安全阀（顶部中央凸起） -->
    <rect x="{x - 10}" y="{y - 58}" width="20" height="8" rx="3"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="1"/>
    <text x="{x}" y="{y - 50}" text-anchor="middle" font-size="6" fill="var(--app-muted)">安全阀</text>
    <!-- 电池铭牌 -->
    <text x="{x}" y="{y - 2}" text-anchor="middle" font-size="14" font-weight="bold">LFP</text>
    <text x="{x}" y="{y + 18}" text-anchor="middle" font-size="12">{_e(soc_text)}</text>
    <text x="{x}" y="{y + 48}" text-anchor="middle" font-size="15" font-weight="bold">方壳 LFP 电池</text>
  </g>"""


def _render_thermocouples(
    x_cell: float, y_top: float, y_bottom: float,
    sensors: bool, t2: float, t2_100: bool,
) -> str:
    """渲染三根 K 型热电偶 T1/T2/T3。"""
    opacity = "1" if sensors else "0.25"
    t2_color = "var(--app-orange)" if t2_100 else "var(--app-cyan)"
    t2_size = 7 if t2_100 else 5

    return f"""<!-- 热电偶 T1 / T2 / T3 -->
  <g id="thermocouple-t1" opacity="{opacity}">
    <!-- T1 - 电池左侧底部 -->
    <line x1="{x_cell - 46}" y1="{y_top}" x2="{x_cell - 32}" y2="{y_bottom}"
      stroke="var(--app-cyan)" stroke-width="2"/>
    <circle cx="{x_cell - 32}" cy="{y_bottom}" r="5"
      fill="var(--app-cyan)" stroke="var(--equipment-stroke)" stroke-width="1"/>
    <text x="{x_cell - 62}" y="{y_top - 6}" font-size="14" font-weight="bold">T1</text>
  </g>

  <g id="thermocouple-t2" opacity="{opacity}">
    <!-- T2 - 电池中心底部（关键控制热电偶） -->
    <line x1="{x_cell}" y1="{y_top - 6}" x2="{x_cell}" y2="{y_bottom}"
      stroke="{t2_color}" stroke-width="3"/>
    <circle cx="{x_cell}" cy="{y_bottom}" r="{t2_size}"
      fill="{t2_color}" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <text x="{x_cell + 12}" y="{y_top - 14}" font-size="14" font-weight="bold">T2</text>
    <text x="{x_cell + 12}" y="{y_top}" font-size="12" fill="{t2_color}">{t2:.1f}℃</text>
  </g>

  <g id="thermocouple-t3" opacity="{opacity}">
    <!-- T3 - 电池右侧底部 -->
    <line x1="{x_cell + 44}" y1="{y_top}" x2="{x_cell + 28}" y2="{y_bottom}"
      stroke="var(--app-cyan)" stroke-width="2"/>
    <circle cx="{x_cell + 28}" cy="{y_bottom}" r="5"
      fill="var(--app-cyan)" stroke="var(--equipment-stroke)" stroke-width="1"/>
    <text x="{x_cell + 52}" y="{y_top - 6}" font-size="14" font-weight="bold">T3</text>
  </g>"""


def _render_voltage_leads(
    x_cell: float, y_top: float, x_daq: float, y_daq: float,
    voltage: bool,
) -> str:
    """渲染电压采集线（V+ / V- 双线 → DAQ）。"""
    if not voltage:
        return f"""<!-- 电压采集线（未连接） -->
  <g id="voltage-leads" opacity="0.2">
    <path d="M{x_cell + 14} {y_top - 8} C{x_cell + 10} {y_top - 72} {x_daq} {y_daq - 28} {x_daq + 16} {y_daq}" fill="none" stroke="var(--app-green)" stroke-width="2" stroke-dasharray="6 4"/>
    <path d="M{x_cell - 26} {y_top - 8} C{x_cell - 20} {y_top - 60} {x_daq + 4} {y_daq - 20} {x_daq + 20} {y_daq + 2}" fill="none" stroke="var(--app-red)" stroke-width="2" stroke-dasharray="6 4"/>
  </g>"""

    return f"""<!-- 电压采集线 V+ / V- -->
  <g id="voltage-leads" opacity="1">
    <!-- V+（正极，绿色） -->
    <path d="M{x_cell + 14} {y_top - 8} C{x_cell + 10} {y_top - 62} {x_daq} {y_daq - 16} {x_daq + 16} {y_daq}"
      fill="none" stroke="var(--app-green)" stroke-width="2.5"/>
    <!-- V-（负极，红色） -->
    <path d="M{x_cell - 26} {y_top - 8} C{x_cell - 20} {y_top - 50} {x_daq + 4} {y_daq - 10} {x_daq + 20} {y_daq + 2}"
      fill="none" stroke="var(--app-red)" stroke-width="2.5"/>
    <!-- V+ 标签 -->
    <text x="{x_daq - 12}" y="{y_daq - 22}" font-size="9" fill="var(--app-green)">V+</text>
    <!-- V- 标签 -->
    <text x="{x_daq + 26}" y="{y_daq - 6}" font-size="9" fill="var(--app-red)">V−</text>
    <text x="{x_daq - 38}" y="{y_daq - 38}" text-anchor="middle" font-size="12">电压采集线 ✓</text>
  </g>"""


def _render_pressure_sensor(
    x_gauge: float, y_gauge: float,
    pressure: float, pressure_checked: bool,
) -> str:
    """渲染舱体压力传感器模拟表盘。"""
    gauge_angle = max(-115, min(115, -115 + pressure / 160 * 230))
    rad = math.radians(gauge_angle)
    needle_len = 18
    nx = x_gauge + needle_len * math.cos(rad)
    ny = y_gauge + needle_len * math.sin(rad)
    opacity = "1" if pressure_checked else "0.3"

    return f"""<!-- 压力传感器 -->
  <g id="pressure-sensor" opacity="{opacity}">
    <!-- 传感器本体 -->
    <rect x="{x_gauge - 22}" y="{y_gauge - 42}" width="44" height="26" rx="5"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <!-- 连接管 -->
    <line x1="{x_gauge}" y1="{y_gauge - 16}" x2="{x_gauge}" y2="{y_gauge - 6}"
      stroke="var(--equipment-stroke)" stroke-width="2.5"/>
    <!-- 表盘 -->
    <circle cx="{x_gauge}" cy="{y_gauge + 20}" r="24"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <!-- 刻度弧线 -->
    <path d="M{x_gauge - 18} {y_gauge + 32} A22 22 0 1 1 {x_gauge + 18} {y_gauge + 32}"
      fill="none" stroke="var(--app-muted)" stroke-width="3"/>
    <!-- 指针 -->
    <line x1="{x_gauge}" y1="{y_gauge + 20}" x2="{nx:.1f}" y2="{ny:.1f}"
      stroke="var(--app-red)" stroke-width="3" stroke-linecap="round"/>
    <!-- 指针中心 -->
    <circle cx="{x_gauge}" cy="{y_gauge + 20}" r="4" fill="var(--app-primary-light)"/>
    <!-- 读数 -->
    <text x="{x_gauge}" y="{y_gauge + 26}" text-anchor="middle" font-size="10">{pressure:.1f}</text>
    <text x="{x_gauge}" y="{y_gauge + 56}" text-anchor="middle" font-size="10">kPa</text>
    <!-- 标签 -->
    <text x="{x_gauge + 36}" y="{y_gauge - 18}" text-anchor="start" font-size="11">压力</text>
  </g>"""


def _render_vacuum_pump(x: float, y: float, vacuum_active: bool) -> str:
    """渲染旋片式真空泵（带电机）。"""
    led = "var(--app-green)" if vacuum_active else "var(--app-muted)"
    return f"""<!-- 真空泵 -->
  <g id="vacuum-pump">
    <!-- 泵主体 -->
    <rect x="{x}" y="{y}" width="78" height="52" rx="10"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="2.5"/>
    <!-- 电机部分 -->
    <rect x="{x + 50}" y="{y + 6}" width="22" height="40" rx="6"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <!-- 电机散热片 -->
    <line x1="{x + 52}" y1="{y + 12}" x2="{x + 70}" y2="{y + 12}" stroke="var(--app-border)" stroke-width="1"/>
    <line x1="{x + 52}" y1="{y + 20}" x2="{x + 70}" y2="{y + 20}" stroke="var(--app-border)" stroke-width="1"/>
    <line x1="{x + 52}" y1="{y + 28}" x2="{x + 70}" y2="{y + 28}" stroke="var(--app-border)" stroke-width="1"/>
    <!-- 泵体 -->
    <rect x="{x + 10}" y="{y + 12}" width="38" height="28" rx="5"
      fill="var(--app-surface)" stroke="var(--app-border)" stroke-width="1"/>
    <!-- 进气口 / 排气口 -->
    <circle cx="{x + 18}" cy="{y + 10}" r="6"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <circle cx="{x + 40}" cy="{y + 10}" r="6"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <!-- 状态灯 -->
    <circle cx="{x + 68}" cy="{y + 44}" r="6" fill="{led}" stroke="var(--equipment-stroke)" stroke-width="1"/>
    <!-- 标签 -->
    <text x="{x + 39}" y="{y + 66}" text-anchor="middle" font-size="15" font-weight="bold">真空泵</text>
    <text x="{x + 39}" y="{y + 82}" text-anchor="middle" font-size="11"
      fill="{led}">{'运行中' if vacuum_active else '待机'}</text>
  </g>"""


def _render_nitrogen_cylinder(x: float, y: float, nitrogen_active: bool) -> str:
    """渲染氮气瓶（含减压阀）。"""
    led = "var(--app-green)" if nitrogen_active else "var(--app-muted)"
    return f"""<!-- 氮气瓶 -->
  <g id="nitrogen-cylinder">
    <!-- 瓶体 -->
    <rect x="{x}" y="{y + 20}" width="52" height="98" rx="22"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="2.5"/>
    <!-- 瓶体高光 -->
    <rect x="{x + 8}" y="{y + 26}" width="10" height="78" rx="3"
      fill="rgba(255,255,255,0.15)"/>
    <!-- 瓶颈 -->
    <rect x="{x + 12}" y="{y}" width="28" height="24" rx="5"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <!-- 减压阀 -->
    <circle cx="{x + 26}" cy="{y + 6}" r="10"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <line x1="{x + 26}" y1="{y + 6}" x2="{x + 32}" y2="{y}" stroke="var(--app-red)" stroke-width="2"/>
    <!-- 出气口 -->
    <circle cx="{x + 56}" cy="{y + 48}" r="10"
      fill="{led}" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <!-- N₂ 文字 -->
    <text x="{x + 26}" y="{y + 72}" text-anchor="middle" font-size="22"
      font-weight="bold" fill="var(--app-primary-light)">N₂</text>
    <!-- 标签 -->
    <text x="{x + 26}" y="{y + 136}" text-anchor="middle" font-size="15" font-weight="bold">氮气瓶</text>
    <text x="{x + 26}" y="{y + 152}" text-anchor="middle" font-size="11"
      fill="{led}">{'供气中' if nitrogen_active else '关闭'}</text>
  </g>"""


def _render_gas_bag(
    x_left: float, y_center: float, has_sample: bool,
) -> str:
    """渲染集气袋（多段采样袋）。"""
    opacity = "1" if has_sample else "0.45"
    fill_color = "var(--app-surface-soft)" if has_sample else "var(--app-surface)"
    stroke_color = "var(--app-cyan)" if has_sample else "var(--app-muted)"
    status_text = "已采样" if has_sample else "待采样"
    bag_w = 78

    return f"""<!-- 集气袋 -->
  <g id="gas-bag" opacity="{opacity}">
    <!-- 袋体 -->
    <path d="M{x_left} {y_center - 38}
      C{x_left + bag_w + 14} {y_center - 48}
       {x_left + bag_w + 14} {y_center + 42}
       {x_left} {y_center + 30}
      C{x_left + 14} {y_center + 16}
       {x_left + 14} {y_center - 12}
       {x_left} {y_center - 38} Z"
      fill="{fill_color}" stroke="{stroke_color}" stroke-width="3"/>
    <!-- 袋体折叠纹 -->
    <path d="M{x_left + 8} {y_center - 22} C{x_left + bag_w - 8} {y_center - 28} {x_left + bag_w - 8} {y_center - 14} {x_left + 8} {y_center - 8}"
      fill="none" stroke="{stroke_color}" stroke-width="1" opacity="0.5"/>
    <!-- 接口 -->
    <rect x="{x_left - 8}" y="{y_center - 6}" width="16" height="12" rx="3"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <rect x="{x_left + bag_w - 3}" y="{y_center + 8}" width="18" height="12" rx="3"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <!-- 标签 -->
    <text x="{x_left + bag_w / 2}" y="{y_center + 5}" text-anchor="middle" font-size="16" font-weight="bold">集气袋</text>
    <text x="{x_left + bag_w / 2}" y="{y_center + 22}" text-anchor="middle" font-size="11"
      fill="{stroke_color}">{_e(status_text)}</text>
  </g>"""


def _render_gc_device(
    x: float, y: float, gc_started: bool, gc_done: bool,
) -> str:
    """渲染 GC 气相色谱仪（含色谱峰曲线）。"""
    led = "var(--app-green)" if gc_done else ("var(--app-orange)" if gc_started else "var(--app-muted)")
    if gc_done:
        peaks = (
            f'<polyline points="{x + 16},{y + 88} {x + 30},{y + 88} {x + 36},{y + 44} '
            f'{x + 42},{y + 88} {x + 58},{y + 88} {x + 66},{y + 54} {x + 74},{y + 88} '
            f'{x + 90},{y + 88} {x + 98},{y + 64} {x + 106},{y + 88}" '
            'fill="none" stroke="var(--app-cyan)" stroke-width="3"/>'
        )
        peak_labels = (
            f'<text x="{x + 36}" y="{y + 38}" text-anchor="middle" font-size="8" fill="var(--app-cyan)">H₂</text>'
            f'<text x="{x + 66}" y="{y + 48}" text-anchor="middle" font-size="8" fill="var(--app-cyan)">CO</text>'
            f'<text x="{x + 98}" y="{y + 58}" text-anchor="middle" font-size="8" fill="var(--app-cyan)">CH₄</text>'
        )
    elif gc_started:
        peaks = (
            f'<polyline points="{x + 16},{y + 88} {x + 30},{y + 88} {x + 38},{y + 60} {x + 46},{y + 88} {x + 64},{y + 88}" '
            'fill="none" stroke="var(--app-cyan)" stroke-width="2" opacity="0.75"/>'
        )
        peak_labels = ""
    else:
        peaks = ""
        peak_labels = ""

    return f"""<!-- GC 气相色谱仪 -->
  <g id="gc-device">
    <!-- 主机 -->
    <rect x="{x}" y="{y}" width="140" height="108" rx="10"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="2.5"/>
    <!-- 进样接口 -->
    <rect x="{x - 8}" y="{y + 96}" width="18" height="14" rx="4"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <!-- 显示屏 -->
    <rect x="{x + 12}" y="{y + 10}" width="100" height="60" rx="5"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <!-- 基线 -->
    <line x1="{x + 16}" y1="{y + 60}" x2="{x + 108}" y2="{y + 60}"
      stroke="var(--app-border)" stroke-width="0.5"/>
    <!-- 色谱峰 -->
    {peaks}
    {peak_labels}
    <!-- 显示屏网格 -->
    <line x1="{x + 16}" y1="{y + 30}" x2="{x + 108}" y2="{y + 30}"
      stroke="var(--app-border)" stroke-width="0.3" stroke-dasharray="3 6"/>
    <!-- FID / TCD 标签 -->
    <rect x="{x + 116}" y="{y + 10}" width="20" height="22" rx="3"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="1"/>
    <text x="{x + 126}" y="{y + 24}" text-anchor="middle" font-size="7">FID</text>
    <rect x="{x + 116}" y="{y + 36}" width="20" height="22" rx="3"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="1"/>
    <text x="{x + 126}" y="{y + 50}" text-anchor="middle" font-size="7">TCD</text>
    <!-- 状态灯 -->
    <circle cx="{x + 130}" cy="{y + 96}" r="7" fill="{led}"
      stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <!-- 标签 -->
    <text x="{x + 70}" y="{y - 10}" text-anchor="middle" font-size="14" font-weight="bold">GC 气相色谱仪</text>
  </g>"""


def _render_ms_device(x: float, y: float, active: bool) -> str:
    """渲染质谱仪，用于文献装置 GC-MS 分析链显示。"""
    led = "var(--app-green)" if active else "var(--app-muted)"
    opacity = "1" if active else "0.65"
    return f"""<!-- 质谱仪 -->
  <g id="ms-device" opacity="{opacity}">
    <rect x="{x}" y="{y}" width="134" height="92" rx="10"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="2.5"/>
    <rect x="{x + 16}" y="{y + 16}" width="82" height="38" rx="6"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <path d="M{x + 24} {y + 48} L{x + 38} {y + 26} L{x + 54} {y + 48} L{x + 72} {y + 24} L{x + 92} {y + 48}"
      fill="none" stroke="var(--app-cyan)" stroke-width="2.5"/>
    <circle cx="{x + 112}" cy="{y + 70}" r="8" fill="{led}" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <text x="{x + 67}" y="{y - 12}" text-anchor="middle" font-size="15" font-weight="bold">质谱仪</text>
  </g>"""


def _render_analysis_computer(x: float, y: float, active: bool) -> str:
    """渲染文献装置中的分析电脑。"""
    opacity = "1" if active else "0.7"
    return f"""<!-- 分析电脑 -->
  <g id="analysis-computer" opacity="{opacity}">
    <rect x="{x}" y="{y}" width="128" height="76" rx="8"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="2.5"/>
    <rect x="{x + 12}" y="{y + 10}" width="104" height="46" rx="5"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <polyline points="{x + 24},{y + 46} {x + 42},{y + 38} {x + 58},{y + 42} {x + 76},{y + 28} {x + 104},{y + 34}"
      fill="none" stroke="var(--app-green)" stroke-width="2.5"/>
    <rect x="{x + 48}" y="{y + 64}" width="32" height="5" rx="2" fill="var(--app-muted)" opacity="0.5"/>
    <text x="{x + 64}" y="{y - 12}" text-anchor="middle" font-size="15" font-weight="bold">电脑</text>
  </g>"""


def _render_daq_computer(
    x: float, y: float, voltage: bool, gc_done: bool,
) -> str:
    """渲染数据采集电脑（含 DAQ 屏幕）。"""
    wave_color = "var(--app-green)" if voltage else "var(--app-muted)"
    return f"""<!-- DAQ 数据采集电脑 -->
  <g id="daq-computer">
    <!-- 主机 -->
    <rect x="{x}" y="{y}" width="128" height="76" rx="8"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="2.5"/>
    <!-- 屏幕 -->
    <rect x="{x + 10}" y="{y + 8}" width="108" height="50" rx="5"
      fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <!-- 屏幕顶部栏 -->
    <rect x="{x + 10}" y="{y + 8}" width="108" height="8" rx="3"
      fill="var(--app-surface-soft)" stroke="none"/>
    <!-- 实时曲线 -->
    <polyline points="{x + 16},{y + 54} {x + 30},{y + 46} {x + 46},{y + 48} {x + 60},{y + 34}
      {x + 76},{y + 38} {x + 90},{y + 28} {x + 108},{y + 30}"
      fill="none" stroke="{wave_color}" stroke-width="2"/>
    <!-- T2 温升指示 -->
    <polyline points="{x + 16},{y + 50} {x + 36},{y + 50} {x + 56},{y + 44} {x + 76},{y + 36} {x + 108},{y + 18}"
      fill="none" stroke="var(--app-orange)" stroke-width="2" opacity="{'1' if gc_done else '0'}"/>
    <!-- 底座 -->
    <rect x="{x + 44}" y="{y + 74}" width="40" height="4" rx="2"
      fill="var(--app-muted)" opacity="0.5"/>
    <!-- 标签 -->
    <text x="{x + 64}" y="{y - 20}" text-anchor="middle" font-size="14" font-weight="bold">DAQ</text>
    <text x="{x + 64}" y="{y - 6}" text-anchor="middle" font-size="13" font-weight="bold">数据采集仪</text>
  </g>"""


def _render_valve(x: float, y: float, label: str, active: bool, direction: str = "h") -> str:
    """渲染管路阀门（水平或垂直）。"""
    color = "var(--app-green)" if active else "var(--app-muted)"
    if direction == "v":
        lx1, ly1, lx2, ly2 = x, y - 16, x, y + 16
        rx, ry = x, y
        rotation = 0 if active else 90
    else:
        lx1, ly1, lx2, ly2 = x - 16, y, x + 16, y
        rx, ry = x, y
        rotation = 45 if active else 0

    return f"""<line x1="{lx1}" y1="{ly1}" x2="{lx2}" y2="{ly2}"
      class="pipeline {'active' if active else ''}"/>
    <circle cx="{rx}" cy="{ry}" r="9" fill="{color}"
      stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <rect x="{rx - 8}" y="{ry - 3}" width="16" height="6" rx="2"
      fill="{color}" transform="rotate({rotation} {rx} {ry})"/>
    <text x="{rx}" y="{ry + 18}" text-anchor="middle" font-size="9">{_e(label)}</text>"""


def render_explosion_chamber_heating_platform_svg(state: dict) -> str:
    """渲染防爆舱-加热模块热失控产气教学演示二维装置图（增强版）。

    状态联动覆盖：
    - 电池准备、热电偶布置、电压线连接、压力检查
    - 防爆舱门关闭、真空、氮气置换
    - 加热模块演示、T2=100℃ 一采
    - 安全阀喷阀二采、温度峰值三采、压力稳定四采
    - GC 分析和可燃风险评价
    """
    # ---------- 状态提取 ----------
    cell_loaded = bool(state.get("cell_loaded"))
    sensors = bool(state.get("thermocouples_placed"))
    voltage = bool(state.get("voltage_leads_connected"))
    pressure_checked = bool(state.get("pressure_sensor_checked"))
    door_closed = bool(state.get("chamber_door_closed"))
    vacuum_done = bool(state.get("vacuum_done"))
    nitrogen_filled = bool(state.get("nitrogen_filled"))
    vacuum = state.get("current_state") == "vacuuming" or (vacuum_done and not nitrogen_filled)
    nitrogen = state.get("current_state") == "nitrogen_filled" or nitrogen_filled
    heating = bool(state.get("heating_started"))
    t2_100 = bool(state.get("t2_reached_100"))
    venting = bool(state.get("venting_detected"))
    runaway = bool(state.get("thermal_runaway_triggered") or state.get("temperature_peak_reached"))
    peak = bool(state.get("temperature_peak_reached"))
    stable = bool(state.get("pressure_stable"))
    gc_started = bool(state.get("gc_started"))
    gc_done = bool(state.get("gc_finished"))
    sampled = state.get("sampling_completed", {}) or {}
    pressure = float(state.get("pressure_kpa", 101.3) or 101.3)
    t2 = float(state.get("temperature_t2_c", 25.0) or 25.0)
    soc = state.get("selected_soc")
    atmosphere = "N₂" if nitrogen else ("真空" if vacuum else "空气")
    current_state = state.get("current_state", "soc_selection")
    assessment = state.get("_assessment_summary", {}) or {}
    alert = assessment.get("latest_severe_warning") or assessment.get("last_alert") or {}
    alert_text = alert.get("message", "")
    has_alert = bool(alert_text) and bool(alert.get("active", True))
    labels = {
        "vacuum": "\u771f\u7a7a\u6cf5 \u2192 \u9632\u7206\u8231",
        "nitrogen": "\u6c2e\u6c14 \u2192 \u9632\u7206\u8231",
        "sample": "\u91c7\u6837\u53e3 \u2192 \u96c6\u6c14\u888b",
        "bag_gc": "\u96c6\u6c14\u888b \u2192 GC",
        "gc_ms": "GC \u2192 \u8d28\u8c31\u4eea",
        "ms_pc": "\u8d28\u8c31\u4eea \u2192 \u7535\u8111",
        "voltage": "V \u4fe1\u53f7 \u2192 DAQ",
        "pressure": "\u538b\u529b\u4fe1\u53f7 \u2192 DAQ",
        "arc_monitor": "ARC \u6e29\u63a7\u76d1\u6d4b",
    }
    connections = [
        LabConnection.from_ports(
            key="lit-vacuum",
            label=labels["vacuum"],
            ports=LITERATURE_PORTS,
            from_device="vacuum",
            from_port="out",
            to_device="chamber",
            to_port="vacuum_in",
            via=[(200, 474), (250, 430)],
            active=vacuum,
            label_x=214,
            label_y=462,
        ),
        LabConnection.from_ports(
            key="lit-n2",
            label=labels["nitrogen"],
            ports=LITERATURE_PORTS,
            from_device="nitrogen",
            from_port="out",
            to_device="chamber",
            to_port="nitrogen_in",
            via=[(202, 270), (246, 296)],
            active=nitrogen and not vacuum,
            label_x=210,
            label_y=248,
        ),
        LabConnection.from_ports(
            key="lit-sample",
            label=labels["sample"],
            ports=LITERATURE_PORTS,
            from_device="chamber",
            from_port="sample_out",
            to_device="bag",
            to_port="in",
            via=[(668, 382), (734, 382)],
            active=any(sampled.values()) or gc_started,
            label_x=696,
            label_y=358,
        ),
        LabConnection.from_ports(
            key="lit-bag-gc",
            label=labels["bag_gc"],
            ports=LITERATURE_PORTS,
            from_device="bag",
            from_port="out",
            to_device="gc",
            to_port="in",
            via=[(876, 398), (894, 414)],
            active=any(sampled.values()) or gc_started,
            label_x=878,
            label_y=436,
        ),
        LabConnection.from_ports(
            key="lit-gc-ms",
            label=labels["gc_ms"],
            ports=LITERATURE_PORTS,
            from_device="gc",
            from_port="out",
            to_device="ms",
            to_port="in",
            via=[(1060, 438), (1060, 452)],
            active=gc_started or gc_done,
            label_x=1110,
            label_y=456,
        ),
        LabConnection.from_ports(
            key="lit-ms-computer",
            label=labels["ms_pc"],
            ports=LITERATURE_PORTS,
            from_device="ms",
            from_port="data_out",
            to_device="computer",
            to_port="data_in",
            via=[(980, 530), (948, 528)],
            kind="virtual",
            active=gc_done,
            label_x=900,
            label_y=548,
        ),
        LabConnection.from_ports(
            key="lit-voltage",
            label=labels["voltage"],
            ports=LITERATURE_PORTS,
            from_device="chamber",
            from_port="voltage_out",
            to_device="daq",
            to_port="temperature_in",
            via=[(600, 220), (720, 208)],
            kind="virtual",
            active=voltage,
            label_x=676,
            label_y=196,
        ),
        LabConnection.from_ports(
            key="lit-pressure",
            label=labels["pressure"],
            ports=LITERATURE_PORTS,
            from_device="chamber",
            from_port="pressure_out",
            to_device="daq",
            to_port="pressure_in",
            via=[(640, 350), (738, 322)],
            kind="virtual",
            active=pressure_checked,
            label_x=704,
            label_y=330,
        ),
        LabConnection.from_ports(
            key="lit-arc-monitor",
            label=labels["arc_monitor"],
            ports=LITERATURE_PORTS,
            from_device="chamber",
            from_port="arc_monitor",
            to_device="arc",
            to_port="signal_in",
            via=[(652, 218), (700, 220)],
            kind="virtual",
            active=heating,
            label_x=626,
            label_y=192,
        ),
    ]
    endpoint_errors = validate_connection_endpoints(connections, LITERATURE_PORTS)
    if endpoint_errors:
        raise ValueError("Literature canvas connection endpoint mismatch: " + "; ".join(endpoint_errors))
    connection_paths = render_connection_paths(connections)

    # ---------- \u91c7\u6837\u6307\u793a\u706f ----------
    light_defs = [
        ("t2_100",      "一采\nT₂=100℃", sampled.get("t2_100"),         t2_100),
        ("venting",     "二采\n安全阀开",  sampled.get("venting"),        venting),
        ("temp_peak",   "三采\n温度峰值",  sampled.get("temperature_peak"), peak),
        ("pressure_ok", "四采\n压力稳定",  sampled.get("pressure_stable"), stable),
    ]
    lights = []
    for idx, (key, label, done, ready) in enumerate(light_defs):
        x = 490 + idx * 70
        color = "var(--app-green)" if done else ("var(--app-orange)" if ready else "var(--app-muted)")
        # 脉冲动画（就绪但未完成）
        pulse = '<animate attributeName="opacity" values="0.6;1;0.6" dur="1.5s" repeatCount="indefinite"/>' if ready and not done else ""
        lights.append(
            f"""<g id="sampling-light-{_e(key)}">
      <circle cx="{x}" cy="612" r="10" fill="{color}" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
      {pulse}
      <text x="{x}" y="640" text-anchor="middle" font-size="12">
        <tspan x="{x}" dy="0">{_e(label.split(chr(10))[0])}</tspan>
        <tspan x="{x}" dy="12">{_e(label.split(chr(10))[1]) if chr(10) in label else ''}</tspan>
      </text>
    </g>"""
        )

    # ---------- 构建 SVG ----------
    vw, vh = LITERATURE_LAYOUT["viewbox"]

    return f"""<svg class="equipment-svg literature-device-svg"
  viewBox="0 0 {vw} {vh}" role="img"
  aria-label="防爆舱-加热模块产气教学演示二维装置图">
  <defs>
    <!-- 热辐射光晕 -->
    <filter id="literature-heat-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="8" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <!-- 背景网格图案 -->
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--app-border)" stroke-width="0.3" opacity="0.4"/>
    </pattern>
  </defs>
  <style>
    .literature-device-svg .connection-label {{
      font-size: 12px;
      font-weight: 700;
      paint-order: stroke;
      stroke: var(--app-surface);
      stroke-width: 6px;
    }}
  </style>
  <g id="literature-layout">

  <!-- ===== 背景 ===== -->
  <rect x="0" y="0" width="{vw}" height="{vh}" fill="url(#grid)" opacity="0.45"/>
  <rect x="24" y="106" width="230" height="470" rx="14" fill="var(--app-surface)" stroke="var(--app-border)" stroke-width="1.5" opacity="0.72"/>
  <rect x="280" y="106" width="390" height="470" rx="14" fill="var(--app-surface)" stroke="var(--app-border)" stroke-width="1.5" opacity="0.72"/>
  <rect x="706" y="106" width="430" height="470" rx="14" fill="var(--app-surface)" stroke="var(--app-border)" stroke-width="1.5" opacity="0.72"/>
  <g id="literature-connection-overview">
    {connection_paths}
  </g>
  <!-- 台面线 -->
  <line x1="32" y1="586" x2="1130" y2="586" stroke="var(--app-border)" stroke-width="2"/>
  <!-- 设备区域标签 -->
  <text x="42" y="134" font-size="16" font-weight="bold" fill="var(--app-muted)">气氛控制区</text>
  <text x="302" y="134" font-size="16" font-weight="bold" fill="var(--app-muted)">防爆舱与测点</text>
  <text x="730" y="134" font-size="16" font-weight="bold" fill="var(--app-muted)">采样分析区</text>
  <text x="42" y="626" font-size="15" font-weight="bold" fill="var(--app-muted)">监控 &amp; 控制区</text>

  <!-- ===== 真空管路系统 ===== -->
  <g id="vacuum-line">
    <!-- 真空泵 -->
    {_render_vacuum_pump(72, 450, vacuum)}
    <!-- 真空管路（真空泵 → 防爆舱左下部） -->
    <line x1="148" y1="476" x2="306" y2="414" class="pipeline {_active(vacuum)}"/>
    <text x="222" y="440" text-anchor="middle" font-size="13" fill="var(--app-muted)">VAC</text>
    {_render_valve(242, 434, "真空阀", vacuum)}
  </g>

  <!-- ===== 氮气管路系统 ===== -->
  <g id="nitrogen-line">
    <!-- 氮气瓶 -->
    {_render_nitrogen_cylinder(70, 184, nitrogen)}
    <!-- 氮气管路（氮气瓶 → 防爆舱左上部） -->
    <line x1="150" y1="270" x2="306" y2="304" class="pipeline {_active(nitrogen and not vacuum)}"/>
    <text x="218" y="258" text-anchor="middle" font-size="14" fill="var(--app-cyan)">N₂</text>
    {_render_valve(246, 290, "N₂阀", nitrogen and not vacuum)}
  </g>

  <!-- ===== 中央：防爆舱体 ===== -->
  {_render_chamber_body(300, 206, 326, 240, door_closed, atmosphere, cell_loaded, heating, runaway)}

  <!-- ===== 舱内：隔热板 ===== -->
  <g id="insulation-board" opacity="{'1' if cell_loaded else '0.3'}">
    <rect x="394" y="398" width="138" height="18" rx="4"
      fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <!-- 隔热纹理 -->
    <line x1="402" y1="403" x2="524" y2="403" stroke="var(--app-border)" stroke-width="0.5" opacity="0.6"/>
    <line x1="402" y1="410" x2="524" y2="410" stroke="var(--app-border)" stroke-width="0.5" opacity="0.6"/>
    <text x="463" y="434" text-anchor="middle" font-size="15" font-weight="bold">隔热板</text>
  </g>

  <!-- ===== 舱内：加热板 ===== -->
  <g id="heating-plate" opacity="{'1' if cell_loaded else '0.3'}">
    <rect x="398" y="374" width="130" height="22" rx="4"
      fill="{'var(--app-orange)' if heating else 'var(--app-muted)'}"
      stroke="var(--equipment-stroke)" stroke-width="2"/>
    <!-- 蛇形加热丝 -->
    <path d="M412 384 C419 377 427 390 435 384 S451 384 459 384 S475 384 483 384 S499 384 507 384"
      fill="none" stroke="var(--app-yellow)" stroke-width="2.5"
      opacity="{'1' if heating else '0.2'}"/>
    <text x="358" y="388" text-anchor="middle" font-size="15" font-weight="bold">加热模块</text>
    <!-- 加热中脉冲动画 -->
    {'<circle cx="518" cy="385" r="5" fill="var(--app-orange)"><animate attributeName="opacity" values="0.5;1;0.5" dur="1s" repeatCount="indefinite"/></circle>' if heating and not runaway else ''}
  </g>

  <!-- ===== 舱内：方壳 LFP 电池 ===== -->
  {_render_prismatic_cell(463, 342, soc, cell_loaded, heating, runaway)}

  <!-- ===== 舱内：热电偶 T1/T2/T3 ===== -->
  {_render_thermocouples(463, 246, 296, sensors, t2, t2_100)}

  <!-- ===== 电压采集线（电池极耳 → DAQ） ===== -->
  {_render_voltage_leads(463, 286, 824, 224, voltage)}

  <!-- ===== 舱体压力传感器 ===== -->
  {_render_pressure_sensor(566, 322, pressure, pressure_checked)}

  <!-- ===== ARC 热失控测试单元 ===== -->
  <g id="literature-arc-unit" transform="translate(676, 172)">
    <rect x="0" y="0" width="112" height="92" rx="12" class="device-fill" stroke-width="2.5"/>
    <rect x="14" y="18" width="56" height="48" rx="6" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <rect x="76" y="18" width="24" height="34" rx="4" fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <path d="M24 58 C34 42 54 42 64 58" fill="none" stroke="{'var(--app-red)' if runaway else ('var(--app-orange)' if heating else 'var(--app-muted)')}" stroke-width="3"/>
    <circle cx="88" cy="68" r="8" fill="{'var(--app-green)' if heating else 'var(--app-muted)'}" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <text x="56" y="-12" text-anchor="middle" font-size="14" font-weight="bold">ARC 热失控测试单元</text>
    <text x="56" y="84" text-anchor="middle" font-size="11">温控 / 监测</text>
  </g>

  <!-- ===== 采样管路（舱体出气口 → 集气袋） ===== -->
  <g id="sampling-line">
    <line x1="612" y1="382" x2="780" y2="382" class="pipeline {_active(any(sampled.values()) or gc_started)}"/>
    <circle cx="696" cy="382" r="10"
      fill="{'var(--app-green)' if any(sampled.values()) else 'var(--app-muted)'}"
      stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <text x="692" y="360" text-anchor="middle" font-size="15" font-weight="bold">采样口</text>
  </g>

  <!-- ===== 集气袋 ===== -->
  <g id="gas-bag" transform="translate(756, 332)">
    {_render_gas_bag(24, 50, any(sampled.values()))}
  </g>

  <!-- ===== GC 气相色谱仪 ===== -->
  {_render_gc_device(904, 312, gc_started, gc_done)}

  <!-- ===== 质谱仪与分析电脑 ===== -->
  {_render_ms_device(1002, 470, gc_started or gc_done)}
  {_render_analysis_computer(800, 478, gc_done)}

  <!-- ===== DAQ 数据采集电脑 ===== -->
  {_render_daq_computer(824, 204, voltage or pressure_checked, gc_done)}

  <!-- ===== 喷阀产气指示 ===== -->
  <g id="vent-gas-indicator" opacity="{'1' if venting else '0'}">
    <path d="M512 332 C562 310 598 290 634 254"
      fill="none" stroke="var(--app-orange)" stroke-width="3"/>
    <path d="M510 340 C558 342 598 330 634 306"
      fill="none" stroke="var(--app-orange)" stroke-width="2" opacity="0.7"/>
    <text x="640" y="252" font-size="13" fill="var(--app-orange)">喷阀产气</text>
  </g>

  <!-- ===== 底部：采样阶段指示灯面板 ===== -->
  <g id="sampling-stage-panel">
    <rect x="448" y="598" width="300" height="96" rx="9"
      fill="var(--app-surface)" stroke="var(--app-border)" stroke-width="1.5"/>
    <text x="598" y="590" text-anchor="middle" font-size="15" font-weight="bold">采样阶段指示灯</text>
    {''.join(lights)}
  </g>

  <!-- ===== 底部：状态条 ===== -->
  <g id="status-strip">
    <rect x="254" y="598" width="172" height="96" rx="9"
      fill="var(--app-surface)" stroke="var(--app-border)" stroke-width="1.5"/>
    <!-- 阶段名称 -->
    <text x="340" y="628" text-anchor="middle" font-size="15" font-weight="bold">当前阶段</text>
    <text x="340" y="654" text-anchor="middle" font-size="14"
      fill="var(--app-primary-light)">{_e(_state_label(current_state))}</text>
  </g>

  <!-- ===== 右下：读图说明 ===== -->
  <g id="literature-teaching-notes">
    <rect x="776" y="598" width="342" height="96" rx="9"
      fill="var(--app-surface)" stroke="var(--app-border)" stroke-width="1.5"/>
    <text x="794" y="628" font-size="15" font-weight="bold" fill="var(--app-primary)">关键流向</text>
    <text x="794" y="652" font-size="13" fill="var(--app-muted)">氮气瓶 / 真空泵 → 防爆舱</text>
    <text x="794" y="672" font-size="13" fill="var(--app-muted)">采样口、集气袋、气相色谱仪、质谱仪；T/P/V 信号接入 DAQ 数据采集仪</text>
  </g>

  <g id="literature-ports">
    {_render_lit_ports([
        ("vacuum", "out", "vacuum"),
        ("nitrogen", "out", "gas"),
        ("chamber", "vacuum_in", "vacuum"),
        ("chamber", "nitrogen_in", "gas"),
        ("chamber", "sample_out", "gas"),
        ("chamber", "voltage_out", "signal"),
        ("chamber", "pressure_out", "signal"),
        ("chamber", "arc_monitor", "signal"),
        ("bag", "in", "gas"),
        ("bag", "out", "gas"),
        ("gc", "in", "gas"),
        ("gc", "out", "gas"),
        ("ms", "in", "gas"),
        ("ms", "data_out", "signal"),
        ("computer", "data_in", "signal"),
        ("daq", "temperature_in", "signal"),
        ("daq", "pressure_in", "signal"),
        ("arc", "signal_in", "signal"),
    ])}
  </g>
  {render_port_debug_nodes(LITERATURE_PORTS)}

  {f'''
  <g class="risk-overlay" id="literature-risk-overlay">
    <rect x="286" y="68" width="588" height="48" rx="12" fill="rgba(198,40,40,0.13)" stroke="var(--app-red)" stroke-width="2.5"/>
    <text x="580" y="88" text-anchor="middle" font-size="18" font-weight="bold" fill="var(--app-red)">注意实验安全</text>
    <text x="580" y="108" text-anchor="middle" font-size="13" fill="var(--app-red)">{_e(str(alert_text)[:50])}</text>
  </g>
  ''' if has_alert else ''}

  <!-- ===== 顶部标题 ===== -->
  <rect x="286" y="18" width="588" height="36" rx="10"
    fill="var(--app-surface)" stroke="var(--app-border)" stroke-width="1" opacity="0.92"/>
  <text x="580" y="42" text-anchor="middle" font-size="19" font-weight="bold"
    fill="var(--app-primary)">文献装置模式：防爆舱-加热模块产气教学演示</text>
  {_render_compact_connection_legend(900, 18)}

  </g>
</svg>"""
