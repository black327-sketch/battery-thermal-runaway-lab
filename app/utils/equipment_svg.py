"""二维实验设备 SVG 渲染工具。"""

from __future__ import annotations

import html
import math

from app.utils.lab_connections import (
    LabConnection,
    flatten_layout_ports,
    render_connection_legend,
    render_connection_paths,
    render_port_debug_nodes,
    validate_connection_endpoints,
)


def _e(value: object) -> str:
    return html.escape("" if value is None else str(value))


ARC_LAYOUT = {
    "viewbox": (1680, 980),
    "devices": {
        "computer": {
            "x": 80,
            "y": 570,
            "w": 180,
            "h": 108,
            "anchors": {"data_in": (192, 570)},
        },
        "ms": {
            "x": 120,
            "y": 338,
            "w": 142,
            "h": 134,
            "anchors": {"analysis_in": (262, 405), "data_out": (190, 472)},
        },
        "gc": {
            "x": 344,
            "y": 322,
            "w": 184,
            "h": 156,
            "anchors": {"sample_in": (528, 430), "analysis_out": (344, 405), "data_out": (528, 458)},
        },
        "sampling_bag": {
            "x": 560,
            "y": 355,
            "w": 162,
            "h": 150,
            "anchors": {"gas_in": (695, 435), "gas_out": (568, 435)},
        },
        "arc": {
            "x": 770,
            "y": 210,
            "w": 330,
            "h": 310,
            "anchors": {
                "gas_out": (1080, 382),
                "nitrogen_in": (1062, 322),
                "vacuum_port": (1070, 470),
                "sensor_out": (856, 508),
                "pressure_out": (972, 368),
            },
        },
        "tank": {
            "x": 1192,
            "y": 314,
            "w": 250,
            "h": 320,
            "anchors": {"gas_in": (1218, 420), "sample_out": (1218, 575), "pressure_out": (1270, 592)},
        },
        "nitrogen": {
            "x": 1370,
            "y": 98,
            "w": 190,
            "h": 252,
            "anchors": {"out": (1478, 170)},
        },
        "vacuum": {
            "x": 1282,
            "y": 650,
            "w": 220,
            "h": 180,
            "anchors": {"in": (1302, 735)},
        },
        "daq": {
            "x": 684,
            "y": 730,
            "w": 286,
            "h": 132,
            "anchors": {
                "temperature_in": (778, 740),
                "voltage_in": (842, 740),
                "pressure_in": (908, 740),
                "data_out": (700, 806),
            },
        },
        "lfl": {
            "x": 1018,
            "y": 738,
            "w": 244,
            "h": 126,
            "anchors": {"data_in": (1030, 802)},
        },
        "report": {
            "x": 1326,
            "y": 796,
            "w": 150,
            "h": 92,
            "anchors": {"data_in": (1326, 840)},
        },
    },
}


def _anchor(layout: dict, device: str, port: str) -> tuple[int, int]:
    """Return an absolute SVG anchor from a layout configuration."""
    return layout["devices"][device]["anchors"][port]


def _path(start: tuple[int, int], c1: tuple[int, int], c2: tuple[int, int], end: tuple[int, int]) -> str:
    """Build a cubic SVG path from anchored endpoints."""
    return f"M{start[0]} {start[1]} C{c1[0]} {c1[1]} {c2[0]} {c2[1]} {end[0]} {end[1]}"


def _render_port_nodes(layout: dict, specs: list[tuple[str, str, str]]) -> str:
    """Render visible interface nodes so connection endpoints are covered by ports."""
    rows = []
    for device, port, kind in specs:
        x, y = _anchor(layout, device, port)
        fill = "var(--app-cyan)" if kind == "gas" else "var(--app-primary-light)"
        if kind == "vacuum":
            fill = "var(--app-muted)"
        rows.append(
            f'<circle cx="{x}" cy="{y}" r="8" fill="{fill}" '
            'stroke="var(--equipment-stroke)" stroke-width="2"/>'
        )
    return "\n".join(rows)


def render_pressure_gauge_svg(value: float, min_value: float, max_value: float, unit: str) -> str:
    """渲染压力表。"""
    safe = max(min_value, min(max_value, float(value)))
    ratio = 0 if max_value == min_value else (safe - min_value) / (max_value - min_value)
    angle = -120 + ratio * 240
    rad = math.radians(angle)
    x2 = 36 + 25 * math.cos(rad)
    y2 = 36 + 25 * math.sin(rad)
    return f"""
<svg class="equipment-svg" viewBox="0 0 72 80" role="img" aria-label="压力表">
  <g id="pressure-gauge">
    <circle cx="36" cy="36" r="31" class="device-fill" stroke-width="2"/>
    <path d="M14 55 A28 28 0 1 1 58 55" fill="none" stroke="var(--app-muted)" stroke-width="3"/>
    <line x1="36" y1="36" x2="{x2:.1f}" y2="{y2:.1f}" stroke="var(--app-red)" stroke-width="3" stroke-linecap="round"/>
    <circle cx="36" cy="36" r="4" fill="var(--app-primary-light)"/>
    <text x="36" y="72" text-anchor="middle" font-size="10">{safe:.1f} {_e(unit)}</text>
  </g>
</svg>
"""


def render_valve_svg(opened: bool, label: str, disabled: bool = False) -> str:
    """渲染阀门。"""
    rotation = "45" if opened else "0"
    opacity = "0.45" if disabled else "1"
    color = "var(--app-green)" if opened else "var(--app-muted)"
    return f"""
<svg class="equipment-svg" viewBox="0 0 94 60" role="img" aria-label="{_e(label)}">
  <g id="valve-{_e(label)}" opacity="{opacity}">
    <line x1="8" y1="30" x2="86" y2="30" class="pipeline {'active' if opened else ''}"/>
    <circle cx="47" cy="30" r="14" fill="var(--app-surface)" stroke="{color}" stroke-width="3"/>
    <rect x="35" y="26" width="24" height="8" rx="3" fill="{color}" transform="rotate({rotation} 47 30)"/>
    <text x="47" y="56" text-anchor="middle" font-size="10">{_e(label)}</text>
  </g>
</svg>
"""


def render_pipeline_svg(active: bool, gas_type: str = "idle") -> str:
    """渲染管路。"""
    label = {"nitrogen": "N2", "vacuum": "VAC", "sample": "采样"}.get(gas_type, "")
    return f"""
<svg class="equipment-svg" viewBox="0 0 180 38" role="img" aria-label="管路">
  <g id="pipeline-{_e(gas_type)}">
    <line x1="8" y1="19" x2="172" y2="19" class="pipeline {'active' if active else ''}"/>
    <text x="90" y="14" text-anchor="middle" font-size="11">{_e(label)}</text>
  </g>
</svg>
"""


def render_arc_device_svg(state: dict) -> str:
    closed = bool(state.get("arc_door_closed"))
    loaded = bool(state.get("battery_loaded"))
    hot = state.get("current_state") in {"arc_heating", "thermal_runaway"}
    return f"""
<svg class="equipment-svg" viewBox="0 0 210 180" role="img" aria-label="ARC 加速量热仪">
  <g id="arc-device">
    <rect x="24" y="18" width="162" height="142" rx="10" class="device-fill" stroke-width="2"/>
    <rect x="34" y="30" width="138" height="118" rx="6" fill="none" stroke="var(--app-border)" stroke-width="1.5"/>
    <rect x="44" y="44" width="82" height="78" rx="8" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <rect x="54" y="54" width="62" height="58" rx="6" fill="var(--app-surface-soft)" stroke="var(--app-border)"/>
    <rect x="68" y="78" width="34" height="18" rx="4" fill="{'var(--app-orange)' if loaded else 'var(--app-muted)'}"/>
    <line x1="84" y1="54" x2="84" y2="78" stroke="var(--app-cyan)" stroke-width="3"/>
    <path d="M58 112 C66 96 102 96 112 112" fill="none" stroke="{'var(--app-red)' if hot else 'var(--app-muted)'}" stroke-width="3"/>
    <rect x="136" y="42" width="32" height="46" rx="4" fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)"/>
    <polyline points="141,75 147,66 153,70 162,56" fill="none" stroke="var(--app-cyan)" stroke-width="2"/>
    <circle cx="152" cy="108" r="9" fill="{'var(--app-red)' if hot else 'var(--app-green)'}"/>
    <circle cx="140" cy="108" r="4" fill="var(--app-yellow)"/>
    <circle cx="164" cy="108" r="4" fill="var(--app-muted)"/>
    <rect x="42" y="36" width="88" height="94" rx="9" fill="none" stroke="{'var(--app-green)' if closed else 'var(--app-orange)'}" stroke-width="4" stroke-dasharray="{'0' if closed else '7 5'}"/>
    <text x="105" y="16" text-anchor="middle" font-size="13">ARC 加速量热仪</text>
    <text x="152" y="68" text-anchor="middle" font-size="10">控制屏</text>
    <text x="84" y="146" text-anchor="middle" font-size="11">{'舱门已关闭' if closed else '舱门待关闭'}</text>
  </g>
</svg>
"""


def render_sealed_tank_svg(state: dict) -> str:
    pressure = float(state.get("pressure", 101.3))
    count = int(state.get("replacement_count", 0))
    return f"""
<svg class="equipment-svg" viewBox="0 0 210 190" role="img" aria-label="20 L 密封气体收集罐">
  <g id="sealed-tank">
    <ellipse cx="105" cy="48" rx="56" ry="18" class="device-fill" stroke-width="2"/>
    <rect x="49" y="48" width="112" height="88" class="device-fill" stroke-width="2"/>
    <ellipse cx="105" cy="136" rx="56" ry="18" class="device-fill" stroke-width="2"/>
    <line x1="50" y1="82" x2="24" y2="82" class="pipeline {'active' if state.get('vacuum_valve_open') else ''}"/>
    <line x1="160" y1="78" x2="188" y2="78" class="pipeline {'active' if state.get('nitrogen_valve_open') else ''}"/>
    <line x1="105" y1="154" x2="105" y2="182" class="pipeline {'active' if state.get('sampling_valve_open') else ''}"/>
    <circle cx="44" cy="82" r="8" fill="{'var(--app-green)' if state.get('vacuum_valve_open') else 'var(--app-muted)'}" stroke="var(--equipment-stroke)"/>
    <circle cx="166" cy="78" r="8" fill="{'var(--app-green)' if state.get('nitrogen_valve_open') else 'var(--app-muted)'}" stroke="var(--equipment-stroke)"/>
    <circle cx="105" cy="154" r="8" fill="{'var(--app-green)' if state.get('sampling_valve_open') else 'var(--app-muted)'}" stroke="var(--equipment-stroke)"/>
    <circle cx="105" cy="84" r="22" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <line x1="105" y1="84" x2="{105 + min(18, max(-18, (pressure - 60) / 4)):.1f}" y2="70" stroke="var(--app-red)" stroke-width="3"/>
    <rect x="69" y="116" width="72" height="16" rx="4" fill="var(--app-surface-soft)" stroke="var(--app-border)"/>
    <text x="105" y="128" text-anchor="middle" font-size="9">T / P SENSOR</text>
    <text x="26" y="73" text-anchor="middle" font-size="9">真空阀</text>
    <text x="184" y="69" text-anchor="middle" font-size="9">N₂阀</text>
    <text x="134" y="162" text-anchor="middle" font-size="9">采样阀</text>
    <text x="105" y="113" text-anchor="middle" font-size="10">{pressure:.1f} kPa</text>
    <text x="105" y="28" text-anchor="middle" font-size="13">20 L 密封气体收集罐</text>
    <text x="105" y="166" text-anchor="middle" font-size="11">置换 {count}/3</text>
  </g>
</svg>
"""


def render_nitrogen_cylinder_svg(state: dict) -> str:
    active = bool(state.get("nitrogen_valve_open"))
    return f"""
<svg class="equipment-svg" viewBox="0 0 150 190" role="img" aria-label="氮气瓶">
  <g id="nitrogen-cylinder">
    <rect x="48" y="30" width="54" height="130" rx="22" class="device-fill" stroke-width="2"/>
    <path d="M58 46 C74 38 88 44 95 56" fill="none" stroke="var(--app-border)" stroke-width="2"/>
    <rect x="62" y="16" width="26" height="20" rx="4" fill="var(--app-surface)" stroke="var(--equipment-stroke)"/>
    <circle cx="75" cy="16" r="10" fill="{'var(--app-green)' if active else 'var(--app-muted)'}"/>
    <circle cx="106" cy="44" r="13" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <line x1="106" y1="44" x2="115" y2="39" stroke="var(--app-red)" stroke-width="2"/>
    <line x1="102" y1="62" x2="136" y2="62" class="pipeline {'active' if active else ''}"/>
    <text x="75" y="92" text-anchor="middle" font-size="22">N₂</text>
    <text x="75" y="180" text-anchor="middle" font-size="12">氮气瓶</text>
  </g>
</svg>
"""


def render_vacuum_pump_svg(state: dict) -> str:
    active = bool(state.get("vacuum_pump_on"))
    return f"""
<svg class="equipment-svg" viewBox="0 0 180 130" role="img" aria-label="真空泵">
  <g id="vacuum-pump">
    <rect x="38" y="45" width="104" height="54" rx="10" class="device-fill" stroke-width="2"/>
    <rect x="52" y="58" width="42" height="22" rx="4" fill="var(--app-surface)" stroke="var(--equipment-stroke)"/>
    <path d="M58 72 C66 58 80 58 88 72" fill="none" stroke="var(--app-cyan)" stroke-width="2"/>
    <circle cx="62" cy="100" r="10" fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)"/>
    <circle cx="118" cy="100" r="10" fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)"/>
    <line x1="10" y1="68" x2="38" y2="68" class="pipeline {'active' if active else ''}"/>
    <circle cx="126" cy="58" r="8" fill="{'var(--app-green)' if active else 'var(--app-muted)'}"/>
    <text x="90" y="76" text-anchor="middle" font-size="12">VAC</text>
    <text x="90" y="122" text-anchor="middle" font-size="12">真空泵</text>
  </g>
</svg>
"""


def render_gas_bag_svg(state: dict) -> str:
    connected = bool(state.get("gas_bag_connected"))
    filled = bool(state.get("gas_bag_filled") or state.get("sampling_valve_open"))
    width = 84 if filled else (62 if connected else 46)
    x = 90 - width / 2
    status = "已采样" if state.get("gas_bag_filled") else ("采样中" if state.get("sampling_valve_open") else ("已连接" if connected else "未连接"))
    return f"""
<svg class="equipment-svg" viewBox="0 0 180 130" role="img" aria-label="集气袋">
  <g id="gas-bag">
    <line x1="10" y1="64" x2="{x:.1f}" y2="64" class="pipeline {'active' if state.get('sampling_valve_open') else ''}"/>
    <path d="M{x:.1f} 38 C{x + width:.1f} 26 {x + width:.1f} 102 {x:.1f} 90 C{x + 12:.1f} 72 {x + 12:.1f} 56 {x:.1f} 38 Z" fill="var(--app-surface-soft)" stroke="{'var(--app-cyan)' if connected else 'var(--app-muted)'}" stroke-width="3" stroke-dasharray="{'0' if connected else '5 4'}"/>
    <path d="M{x + 10:.1f} 48 C{x + width - 12:.1f} 42 {x + width - 12:.1f} 84 {x + 10:.1f} 82" fill="none" stroke="var(--app-border)" stroke-width="1.5"/>
    <rect x="{x - 8:.1f}" y="56" width="16" height="16" rx="3" fill="var(--app-surface)" stroke="var(--equipment-stroke)"/>
    <text x="90" y="69" text-anchor="middle" font-size="12">采样袋</text>
    <text x="90" y="118" text-anchor="middle" font-size="11">{status}</text>
  </g>
</svg>
"""


def render_gas_chromatograph_svg(state: dict) -> str:
    done = bool(state.get("gc_finished"))
    peaks = """
      <polyline points="56,96 66,96 71,58 76,96 84,96 90,70 96,96 106,96 111,78 116,96" fill="none" stroke="var(--app-cyan)" stroke-width="3"/>
    """ if done else ""
    return f"""
<svg class="equipment-svg" viewBox="0 0 230 170" role="img" aria-label="GC 气相色谱仪">
  <g id="gas-chromatograph">
    <rect x="28" y="24" width="174" height="120" rx="10" class="device-fill" stroke-width="2"/>
    <rect x="44" y="42" width="82" height="70" rx="5" fill="var(--app-surface)" stroke="var(--equipment-stroke)"/>
    <rect x="52" y="48" width="66" height="56" rx="3" fill="var(--app-surface-soft)" stroke="var(--app-border)"/>
    <rect x="136" y="42" width="48" height="18" rx="4" fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)"/>
    <rect x="136" y="72" width="48" height="18" rx="4" fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)"/>
    <circle cx="54" cy="126" r="7" fill="{'var(--app-green)' if done else 'var(--app-muted)'}"/>
    <text x="160" y="56" text-anchor="middle" font-size="10">FID</text>
    <text x="160" y="86" text-anchor="middle" font-size="10">TCD</text>
    <text x="84" y="38" text-anchor="middle" font-size="10">色谱图</text>
    {peaks}
    <text x="115" y="162" text-anchor="middle" font-size="12">GC 气相色谱仪</text>
  </g>
</svg>
"""


def render_full_workbench_svg(state: dict) -> str:
    """Render the full ARC teaching workbench with fit-friendly proportions."""

    layout = ARC_LAYOUT
    aw, ah = layout["viewbox"]
    device = layout["devices"]
    ports = flatten_layout_ports(layout)
    assessment = state.get("_assessment_summary", {}) or {}
    alert = assessment.get("last_alert") or {}
    alert_text = str(alert.get("message", ""))
    has_alert = bool(alert_text)
    current_state = state.get("current_state", "sample_preparation")
    replacement_count = int(state.get("replacement_count", 0) or 0)
    temperature = float(state.get("temperature", 25.0) or 25.0)
    pressure = float(state.get("pressure", 101.3) or 101.3)
    selected_soc = state.get("selected_soc") or "--"

    arc_active = current_state in {"arc_heating", "thermal_runaway", "cooling"}
    n2_active = bool(state.get("nitrogen_valve_open")) or current_state == "nitrogen_filling"
    vacuum_active = bool(state.get("vacuum_pump_on"))
    sample_active = bool(state.get("sampling_valve_open") or state.get("gas_bag_filled"))
    gc_active = bool(state.get("gc_started") or state.get("gc_finished") or current_state == "gc_analysis")
    ms_active = bool(state.get("ms_started") or state.get("ms_finished") or state.get("gc_finished"))
    computer_active = bool(state.get("computer_result_ready") or state.get("gc_finished"))
    lel_active = bool(state.get("lel_calculated") or current_state == "lel_risk_evaluation")
    report_active = current_state == "report_generated"

    connections = [
        LabConnection.from_ports(
            key="vacuum-to-arc",
            label="抽真空",
            ports=ports,
            from_device="arc",
            from_port="vacuum_port",
            to_device="vacuum",
            to_port="in",
            via=[(1168, 540), (1240, 650)],
            active=vacuum_active,
            label_x=1230,
            label_y=610,
        ),
        LabConnection.from_ports(
            key="n2-to-arc",
            label="氮气置换路径",
            ports=ports,
            from_device="nitrogen",
            from_port="out",
            to_device="arc",
            to_port="nitrogen_in",
            via=[(1420, 202), (1196, 250)],
            active=n2_active,
            label_x=1284,
            label_y=224,
        ),
        LabConnection.from_ports(
            key="arc-to-tank",
            label="ARC 采样口",
            ports=ports,
            from_device="arc",
            from_port="gas_out",
            to_device="tank",
            to_port="gas_in",
            via=[(1132, 382), (1166, 410)],
            active=arc_active,
            alert=has_alert,
            label_x=1132,
            label_y=356,
        ),
        LabConnection.from_ports(
            key="tank-to-bag",
            label="采样阀 → 采样袋",
            ports=ports,
            from_device="tank",
            from_port="sample_out",
            to_device="sampling_bag",
            to_port="gas_in",
            via=[(1080, 568), (860, 500)],
            active=sample_active,
            label_x=1000,
            label_y=526,
        ),
        LabConnection.from_ports(
            key="bag-to-gc",
            label="采样袋 → GC",
            ports=ports,
            from_device="sampling_bag",
            from_port="gas_out",
            to_device="gc",
            to_port="sample_in",
            via=[(554, 435), (542, 430)],
            active=gc_active,
            label_x=548,
            label_y=414,
        ),
        LabConnection.from_ports(
            key="gc-to-ms",
            label="气相色谱仪 → 质谱仪",
            ports=ports,
            from_device="gc",
            from_port="analysis_out",
            to_device="ms",
            to_port="analysis_in",
            via=[(318, 405), (294, 405)],
            active=ms_active,
            label_x=314,
            label_y=378,
        ),
        LabConnection.from_ports(
            key="ms-to-computer",
            label="质谱仪 → 电脑",
            ports=ports,
            from_device="ms",
            from_port="data_out",
            to_device="computer",
            to_port="data_in",
            via=[(174, 498), (190, 535)],
            kind="virtual",
            active=computer_active,
            label_x=150,
            label_y=526,
        ),
        LabConnection.from_ports(
            key="arc-sensors-to-daq",
            label="T/P/V 信号 → DAQ",
            ports=ports,
            from_device="arc",
            from_port="sensor_out",
            to_device="daq",
            to_port="temperature_in",
            via=[(812, 590), (792, 674)],
            kind="virtual",
            active=arc_active,
            label_x=716,
            label_y=640,
        ),
        LabConnection.from_ports(
            key="pressure-sensor-to-daq",
            label="压力信号",
            ports=ports,
            from_device="arc",
            from_port="pressure_out",
            to_device="daq",
            to_port="pressure_in",
            via=[(1002, 500), (968, 660)],
            kind="virtual",
            active=arc_active or sample_active,
            label_x=1018,
            label_y=586,
        ),
        LabConnection.from_ports(
            key="daq-to-computer",
            label="DAQ → 电脑",
            ports=ports,
            from_device="daq",
            from_port="data_out",
            to_device="computer",
            to_port="data_in",
            via=[(520, 842), (278, 718)],
            kind="virtual",
            active=arc_active or computer_active,
            label_x=444,
            label_y=826,
        ),
        LabConnection.from_ports(
            key="gc-to-lfl",
            label="组成数据 → LFL_mix",
            ports=ports,
            from_device="gc",
            from_port="data_out",
            to_device="lfl",
            to_port="data_in",
            via=[(650, 610), (858, 802)],
            kind="virtual",
            active=gc_active,
            label_x=720,
            label_y=704,
        ),
    ]
    endpoint_errors = validate_connection_endpoints(connections, ports)
    if endpoint_errors:
        raise ValueError("ARC canvas connection endpoint mismatch: " + "; ".join(endpoint_errors))

    hot_fill = "var(--app-red)" if current_state == "thermal_runaway" else ("var(--app-orange)" if arc_active else "var(--app-muted)")
    tank_fill_level = min(88, 16 + replacement_count * 22)
    bag_width = 126 if state.get("gas_bag_filled") else (112 if state.get("gas_bag_connected") else 104)
    gc_led = "var(--app-green)" if state.get("gc_finished") else ("var(--app-orange)" if gc_active else "var(--app-muted)")
    lel_led = "var(--app-green)" if lel_active else "var(--app-muted)"

    return f"""
<svg class="equipment-svg arc-workbench-svg" viewBox="0 0 {aw} {ah}" role="img" aria-label="ARC 通用模式二维数字孪生实验台">
  <defs>
    <pattern id="arc-grid" width="56" height="56" patternUnits="userSpaceOnUse">
      <path d="M56 0 L0 0 L0 56" fill="none" stroke="var(--app-border)" stroke-width="0.7" opacity="0.35"/>
    </pattern>
  </defs>
  <rect x="0" y="0" width="{aw}" height="{ah}" fill="url(#arc-grid)" opacity="0.72"/>
  <rect x="44" y="62" width="{aw - 88}" height="{ah - 118}" rx="18" fill="transparent" stroke="var(--app-border)" stroke-width="2"/>
  <rect x="66" y="90" width="520" height="610" rx="14" fill="var(--app-surface)" stroke="var(--app-border)" opacity="0.50"/>
  <rect x="648" y="90" width="520" height="610" rx="14" fill="var(--app-surface)" stroke="var(--app-border)" opacity="0.50"/>
  <rect x="1210" y="90" width="400" height="610" rx="14" fill="var(--app-surface)" stroke="var(--app-border)" opacity="0.50"/>
  <text x="326" y="126" font-size="18" font-weight="bold" text-anchor="middle" fill="var(--app-muted)">气体分析与数据处理区</text>
  <text x="908" y="126" font-size="18" font-weight="bold" text-anchor="middle" fill="var(--app-muted)">ARC 热失控实验区</text>
  <text x="1410" y="126" font-size="18" font-weight="bold" text-anchor="middle" fill="var(--app-muted)">气氛与辅助装置区</text>
  <text x="{aw / 2:.0f}" y="42" text-anchor="middle" font-size="26" font-weight="bold" fill="var(--app-primary)">ARC 通用模式：产气收集与可燃性教学评价</text>

  <g id="workbench-connections">
    {render_connection_paths(connections)}
  </g>

  <g id="arc-station" transform="translate({device['arc']['x']} {device['arc']['y']})">
    <rect x="0" y="0" width="330" height="310" rx="18" class="device-fill" stroke-width="3"/>
    <rect x="34" y="42" width="196" height="206" rx="12" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="3"/>
    <rect x="62" y="82" width="124" height="118" rx="10" fill="var(--app-surface-soft)" stroke="var(--app-border)" stroke-width="2"/>
    <rect x="94" y="130" width="58" height="34" rx="5" fill="{hot_fill}"/>
    <path d="M74 204 C98 174 146 174 176 204" fill="none" stroke="{hot_fill}" stroke-width="5" opacity="0.85"/>
    <line x1="126" y1="94" x2="126" y2="130" stroke="var(--app-cyan)" stroke-width="3"/>
    <line x1="98" y1="98" x2="110" y2="130" stroke="var(--app-cyan)" stroke-width="2.5"/>
    <line x1="168" y1="98" x2="150" y2="130" stroke="var(--app-cyan)" stroke-width="2.5"/>
    <rect x="242" y="62" width="58" height="86" rx="7" fill="var(--app-surface-soft)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <polyline points="250,120 258,98 270,110 290,82" fill="none" stroke="var(--app-cyan)" stroke-width="3"/>
    <circle cx="270" cy="186" r="12" fill="{hot_fill}" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <g id="arc-pressure-sensor">
      <line x1="198" y1="126" x2="186" y2="150" stroke="var(--app-primary-light)" stroke-width="3" stroke-linecap="round"/>
      <rect x="184" y="94" width="74" height="32" rx="7" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
      <circle cx="200" cy="110" r="8" fill="var(--app-primary-light)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
      <text x="222" y="115" text-anchor="middle" font-size="12" font-weight="bold">压力传感器</text>
    </g>
    <rect x="31" y="40" width="202" height="214" rx="14" fill="none" stroke="{'var(--app-green)' if state.get('arc_door_closed') else 'var(--app-orange)'}" stroke-width="5" stroke-dasharray="{'0' if state.get('arc_door_closed') else '11 8'}"/>
    <text x="165" y="-18" text-anchor="middle" font-size="20" font-weight="bold" class="device-label">ARC 实验舱</text>
    <text x="165" y="284" text-anchor="middle" font-size="16" class="device-label">实验电池 SOC {selected_soc} | {'舱门已锁' if state.get('arc_door_closed') else '舱门待关'}</text>
    <text x="124" y="74" text-anchor="middle" font-size="14" class="device-label">加热板</text>
    <text x="124" y="232" text-anchor="middle" font-size="13" class="device-label">T1 / T2 / T3</text>
    <text x="270" y="168" text-anchor="middle" font-size="13" class="device-label">控制屏</text>
  </g>

  <g id="tank-station" transform="translate({device['tank']['x']} {device['tank']['y']})">
    <ellipse cx="120" cy="36" rx="92" ry="30" class="device-fill" stroke-width="3"/>
    <rect x="28" y="36" width="184" height="206" class="device-fill" stroke-width="3"/>
    <ellipse cx="120" cy="242" rx="92" ry="30" class="device-fill" stroke-width="3"/>
    <rect x="54" y="{236 - tank_fill_level}" width="132" height="{tank_fill_level}" rx="8" fill="var(--app-cyan)" opacity="0.16"/>
    <circle cx="120" cy="126" r="38" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="3"/>
    <path d="M92 140 A36 36 0 1 1 148 140" fill="none" stroke="var(--app-muted)" stroke-width="4"/>
    <line x1="120" y1="126" x2="{120 + min(31, max(-31, (pressure - 70) / 2.4)):.1f}" y2="102" stroke="var(--app-red)" stroke-width="4" stroke-linecap="round"/>
    <rect x="68" y="186" width="104" height="28" rx="6" fill="var(--app-surface)" stroke="var(--app-border)" stroke-width="2"/>
    <text x="120" y="-18" text-anchor="middle" font-size="20" font-weight="bold" class="device-label">20 L 收集罐</text>
    <text x="120" y="132" text-anchor="middle" font-size="14">{pressure:.1f} kPa</text>
    <text x="120" y="205" text-anchor="middle" font-size="14">置换 {replacement_count}/3</text>
    <text x="120" y="266" text-anchor="middle" font-size="13" class="device-label">压力传感器</text>
  </g>

  <g id="nitrogen-station" transform="translate({device['nitrogen']['x']} {device['nitrogen']['y']})">
    <rect x="34" y="50" width="68" height="156" rx="29" class="device-fill" stroke-width="3"/>
    <rect x="50" y="28" width="36" height="28" rx="6" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="3"/>
    <circle cx="132" cy="72" r="17" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="3"/>
    <line x1="132" y1="72" x2="144" y2="64" stroke="var(--app-red)" stroke-width="3"/>
    <circle cx="68" cy="48" r="11" fill="{'var(--app-green)' if n2_active else 'var(--app-muted)'}"/>
    <path d="M102 72 L132 72" class="connection-line physical {'active' if n2_active else ''}"/>
    <text x="68" y="137" text-anchor="middle" font-size="30" font-weight="bold" fill="var(--app-primary)">N₂</text>
    <text x="68" y="232" text-anchor="middle" font-size="19" font-weight="bold" class="device-label">氮气瓶</text>
    <text x="132" y="108" text-anchor="middle" font-size="15" class="device-label">氮气阀</text>
    <text x="-16" y="-20" text-anchor="start" font-size="15" fill="var(--app-muted)" class="pipeline-label">氮气瓶 → 氮气阀 → ARC 舱体 / 收集系统</text>
  </g>

  <g id="vacuum-station" transform="translate({device['vacuum']['x']} {device['vacuum']['y']})">
    <rect x="0" y="44" width="198" height="94" rx="16" class="device-fill" stroke-width="3"/>
    <rect x="30" y="66" width="76" height="42" rx="8" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <path d="M42 94 C56 66 84 66 96 94" fill="none" stroke="var(--app-cyan)" stroke-width="3"/>
    <circle cx="48" cy="142" r="18" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <circle cx="154" cy="142" r="18" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <circle cx="168" cy="72" r="12" fill="{'var(--app-green)' if vacuum_active else 'var(--app-muted)'}"/>
    <text x="99" y="30" text-anchor="middle" font-size="19" font-weight="bold" class="device-label">真空泵</text>
    <text x="99" y="94" text-anchor="middle" font-size="17">VAC</text>
    <text x="168" y="42" text-anchor="middle" font-size="13" class="device-label">真空阀</text>
  </g>

  <g id="bag-station" transform="translate({device['sampling_bag']['x']} {device['sampling_bag']['y']})">
    <path d="M0 44 C{bag_width + 36} 12 {bag_width + 38} 154 0 132 C22 100 22 74 0 44 Z" fill="var(--app-surface-soft)" stroke="{'var(--app-cyan)' if sample_active else 'var(--app-muted)'}" stroke-width="5" stroke-dasharray="{'0' if state.get('gas_bag_connected') or sample_active else '9 7'}"/>
    <rect x="0" y="68" width="28" height="24" rx="5" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <rect x="{max(54, bag_width - 10):.1f}" y="68" width="24" height="24" rx="5" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <text x="{bag_width / 2:.1f}" y="88" text-anchor="middle" font-size="19" font-weight="bold">采样袋</text>
    <text x="{bag_width / 2:.1f}" y="114" text-anchor="middle" font-size="14" fill="var(--app-muted)">{'已采样' if state.get('gas_bag_filled') else ('已连接' if state.get('gas_bag_connected') else '待连接')}</text>
  </g>

  <g id="gc-station" transform="translate({device['gc']['x']} {device['gc']['y']})">
    <rect x="0" y="0" width="184" height="156" rx="15" class="device-fill" stroke-width="3"/>
    <rect x="172" y="96" width="20" height="24" rx="5" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <rect x="20" y="24" width="104" height="78" rx="7" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <polyline points="28,88 44,88 52,44 60,88 76,88 86,58 96,88 112,88" fill="none" stroke="var(--app-cyan)" stroke-width="4" opacity="{'1' if gc_active else '0.18'}"/>
    <rect x="134" y="30" width="24" height="28" rx="4" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <rect x="134" y="70" width="24" height="28" rx="4" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="1.5"/>
    <circle cx="144" cy="124" r="12" fill="{gc_led}" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <text x="84" y="-16" text-anchor="middle" font-size="19" font-weight="bold" class="device-label">气相色谱仪</text>
  </g>

  <g id="ms-station" transform="translate({device['ms']['x']} {device['ms']['y']})">
    <rect x="0" y="0" width="142" height="134" rx="14" class="device-fill" stroke-width="3"/>
    <rect x="18" y="18" width="84" height="44" rx="7" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <path d="M28 52 L42 32 L56 52 L72 28 L92 52" fill="none" stroke="var(--app-cyan)" stroke-width="3" opacity="{'1' if ms_active else '0.22'}"/>
    <circle cx="28" cy="96" r="10" fill="{'var(--app-green)' if ms_active else 'var(--app-muted)'}" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <text x="71" y="-16" text-anchor="middle" font-size="19" font-weight="bold" class="device-label">质谱仪</text>
    <text x="60" y="102" text-anchor="middle" font-size="13" class="device-label">质谱识别</text>
  </g>

  <g id="computer-station" transform="translate({device['computer']['x']} {device['computer']['y']})">
    <rect x="0" y="0" width="180" height="108" rx="10" class="device-fill" stroke-width="3"/>
    <rect x="18" y="16" width="144" height="66" rx="6" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <polyline points="34,66 54,54 72,58 92,40 112,46 142,30" fill="none" stroke="var(--app-green)" stroke-width="3" opacity="{'1' if computer_active else '0.2'}"/>
    <rect x="70" y="90" width="40" height="7" rx="2" fill="var(--app-muted)" opacity="0.55"/>
    <text x="90" y="-12" text-anchor="middle" font-size="17" font-weight="bold" class="device-label">电脑</text>
    <text x="90" y="44" text-anchor="middle" font-size="12">组分结果</text>
  </g>

  <g id="daq-station" transform="translate({device['daq']['x']} {device['daq']['y']})">
    <rect x="0" y="0" width="286" height="132" rx="14" class="device-fill" stroke-width="3"/>
    <rect x="20" y="20" width="246" height="78" rx="8" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <polyline points="34,82 64,72 94,76 124,54 154,62 188,38 238,46" fill="none" stroke="var(--app-cyan)" stroke-width="4"/>
    <text x="143" y="16" text-anchor="middle" font-size="17" font-weight="bold" class="device-label">DAQ 数据采集仪</text>
    <text x="143" y="118" text-anchor="middle" font-size="14">T {temperature:.1f} C / P {pressure:.1f} kPa / V</text>
  </g>

  <g id="lfl-station" transform="translate({device['lfl']['x']} {device['lfl']['y']})" opacity="0.92">
    <rect x="0" y="0" width="244" height="126" rx="14" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <path d="M42 88 A62 62 0 0 1 182 88" fill="none" stroke="var(--app-border)" stroke-width="10"/>
    <path d="M42 88 A62 62 0 0 1 136 32" fill="none" stroke="var(--app-orange)" stroke-width="10"/>
    <circle cx="196" cy="86" r="12" fill="{lel_led}" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <text x="122" y="30" text-anchor="middle" font-size="16" font-weight="bold">可燃极限教学评估</text>
    <text x="122" y="106" text-anchor="middle" font-size="12" fill="var(--app-muted)">LFL_mix / C / R 教学估算</text>
  </g>

  <g id="report-station" transform="translate({device['report']['x']} {device['report']['y']})" opacity="0.72">
    <rect x="0" y="0" width="142" height="90" rx="10" fill="var(--app-surface)" stroke="var(--equipment-stroke)" stroke-width="2"/>
    <line x1="24" y1="32" x2="112" y2="32" stroke="var(--app-border)" stroke-width="3"/>
    <line x1="24" y1="52" x2="112" y2="52" stroke="var(--app-border)" stroke-width="3"/>
    <circle cx="116" cy="70" r="8" fill="{'var(--app-green)' if report_active else 'var(--app-muted)'}"/>
    <text x="71" y="-12" text-anchor="middle" font-size="15" font-weight="bold" class="device-label">报告摘要</text>
  </g>

  <g id="workbench-ports">
    {_render_port_nodes(layout, [
        ("arc", "gas_out", "gas"),
        ("arc", "nitrogen_in", "gas"),
        ("arc", "vacuum_port", "vacuum"),
        ("arc", "sensor_out", "signal"),
        ("arc", "pressure_out", "signal"),
        ("tank", "gas_in", "gas"),
        ("tank", "sample_out", "gas"),
        ("nitrogen", "out", "gas"),
        ("vacuum", "in", "vacuum"),
        ("sampling_bag", "gas_in", "gas"),
        ("sampling_bag", "gas_out", "gas"),
        ("gc", "sample_in", "gas"),
        ("gc", "analysis_out", "gas"),
        ("gc", "data_out", "signal"),
        ("ms", "analysis_in", "gas"),
        ("ms", "data_out", "signal"),
        ("computer", "data_in", "signal"),
        ("daq", "temperature_in", "signal"),
        ("daq", "pressure_in", "signal"),
        ("daq", "data_out", "signal"),
        ("lfl", "data_in", "signal"),
    ])}
  </g>
  {render_port_debug_nodes(ports)}

  {render_connection_legend(70, 152)}

  {f'''
  <g class="risk-overlay" id="arc-risk-overlay">
    <rect x="480" y="112" width="640" height="106" rx="16" fill="rgba(198,40,40,0.10)" stroke="var(--app-red)" stroke-width="4"/>
    <text x="800" y="152" text-anchor="middle" font-size="28" font-weight="bold" fill="var(--app-red)">注意实验安全</text>
    <text x="800" y="184" text-anchor="middle" font-size="17" fill="var(--app-red)">{_e(alert_text[:70])}</text>
    <path d="M520 244 C660 298 940 298 1080 244" fill="none" stroke="var(--app-red)" stroke-width="6" stroke-dasharray="14 10"/>
  </g>
  ''' if has_alert else ''}
</svg>
"""
