"""Shared SVG connection helpers for the two-dimensional lab canvas."""

from __future__ import annotations

import html
from dataclasses import dataclass
import re


Point = tuple[float, float]
PortMap = dict[str, dict[str, Point]]


@dataclass(frozen=True)
class LabConnection:
    """A semantic connection line in a teaching-only lab SVG."""

    key: str
    label: str
    path: str = ""
    kind: str = "physical"
    active: bool = False
    alert: bool = False
    label_x: float | None = None
    label_y: float | None = None
    from_device: str = ""
    from_port: str = ""
    to_device: str = ""
    to_port: str = ""

    @classmethod
    def from_ports(
        cls,
        *,
        key: str,
        label: str,
        ports: PortMap,
        from_device: str,
        from_port: str,
        to_device: str,
        to_port: str,
        via: list[Point] | None = None,
        kind: str = "physical",
        active: bool = False,
        alert: bool = False,
        label_x: float | None = None,
        label_y: float | None = None,
    ) -> "LabConnection":
        """Build a connection from named device ports and generate its SVG path."""

        start = get_port_point(ports, from_device, from_port)
        end = get_port_point(ports, to_device, to_port)
        return cls(
            key=key,
            label=label,
            path=build_orthogonal_path(start, end, via),
            kind=kind,
            active=active,
            alert=alert,
            label_x=label_x,
            label_y=label_y,
            from_device=from_device,
            from_port=from_port,
            to_device=to_device,
            to_port=to_port,
        )


def _e(value: object) -> str:
    return html.escape("" if value is None else str(value))


def render_connection_paths(connections: list[LabConnection]) -> str:
    """Render connection paths with stable classes for CSS and tests."""

    rows: list[str] = []
    for item in connections:
        classes = ["connection-line", item.kind]
        if item.active:
            classes.append("active")
        if item.alert:
            classes.append("alert")
        attrs = []
        if item.from_device and item.from_port:
            attrs.append(f'data-from="{_e(item.from_device)}:{_e(item.from_port)}"')
        if item.to_device and item.to_port:
            attrs.append(f'data-to="{_e(item.to_device)}:{_e(item.to_port)}"')
        rows.append(
            f'<path id="connection-{_e(item.key)}" d="{_e(item.path)}" '
            f'class="{" ".join(classes)}" data-label="{_e(item.label)}" '
            f'aria-label="{_e(item.label)}" {" ".join(attrs)}><title>{_e(item.label)}</title></path>'
        )
        rows.append(
            f'<text class="pipeline-label connection-label" '
            f'x="{item.label_x if item.label_x is not None else _label_x(item.path)}" '
            f'y="{item.label_y if item.label_y is not None else _label_y(item.path)}">{_e(item.label)}</text>'
        )
    return "\n".join(rows)


def render_connection_legend(x: int, y: int) -> str:
    """Render a compact legend explaining solid, dashed, and alert lines."""

    return f"""
<g id="connection-legend" class="connection-legend" transform="translate({x} {y})">
  <rect x="0" y="0" width="238" height="86" rx="8" class="legend-bg"/>
  <text x="14" y="22" class="device-label legend-title">连线图例</text>
  <path d="M16 40 L78 40" class="connection-line physical"/>
  <text x="92" y="44" class="pipeline-label">实线：已连接</text>
  <path d="M16 58 L78 58" class="connection-line physical active"/>
  <text x="92" y="62" class="pipeline-label">虚线：当前作用连接</text>
  <path d="M16 76 L78 76" class="connection-line alert"/>
  <text x="92" y="80" class="pipeline-label">红色：异常 / 阻断</text>
</g>
"""


def flatten_layout_ports(layout: dict, *, device_key: str = "devices", port_key: str = "anchors") -> PortMap:
    """Extract a device->port coordinate map from existing layout dictionaries."""

    devices = layout.get(device_key, {})
    ports: PortMap = {}
    for device_name, device_spec in devices.items():
        anchors = device_spec.get(port_key, {})
        ports[device_name] = {name: (float(point[0]), float(point[1])) for name, point in anchors.items()}
    return ports


def get_port_point(ports: PortMap, device: str, port: str) -> Point:
    """Return a named port point or raise a clear configuration error."""

    try:
        return ports[device][port]
    except KeyError as exc:
        raise KeyError(f"Unknown canvas port: {device}.{port}") from exc


def build_orthogonal_path(start: Point, end: Point, via: list[Point] | None = None) -> str:
    """Generate a readable polyline-style SVG path with exact anchored endpoints."""

    points = [start, *(via or []), end]
    return " ".join(("M" if idx == 0 else "L") + f"{point[0]:.1f} {point[1]:.1f}" for idx, point in enumerate(points))


def validate_connection_endpoints(
    connections: list[LabConnection],
    ports: PortMap,
    *,
    tolerance: float = 0.1,
) -> list[str]:
    """Validate that semantic connection paths begin and end at their declared ports."""

    errors: list[str] = []
    for item in connections:
        if not (item.from_device and item.from_port and item.to_device and item.to_port):
            continue
        numbers = _path_numbers(item.path)
        if len(numbers) < 4:
            errors.append(f"{item.key}: path has fewer than two points")
            continue
        path_start = (numbers[0], numbers[1])
        path_end = (numbers[-2], numbers[-1])
        expected_start = get_port_point(ports, item.from_device, item.from_port)
        expected_end = get_port_point(ports, item.to_device, item.to_port)
        if _distance(path_start, expected_start) > tolerance:
            errors.append(
                f"{item.key}: start {path_start} != {item.from_device}.{item.from_port} {expected_start}"
            )
        if _distance(path_end, expected_end) > tolerance:
            errors.append(f"{item.key}: end {path_end} != {item.to_device}.{item.to_port} {expected_end}")
    return errors


def render_port_debug_nodes(ports: PortMap, *, visible: bool = False) -> str:
    """Render optional port markers for canvas debugging and screenshot checks."""

    cls = "port-debug-layer" + ("" if visible else " hidden")
    rows = [f'<g id="canvas-port-debug" class="{cls}" aria-label="设备端口调试层">']
    for device, device_ports in ports.items():
        for port, (x, y) in device_ports.items():
            label = f"{device}.{port}"
            rows.append(
                f'<g class="port-debug-node" data-port="{_e(label)}">'
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5"/>'
                f'<text x="{x + 7:.1f}" y="{y - 7:.1f}">{_e(label)}</text>'
                "</g>"
            )
    rows.append("</g>")
    return "\n".join(rows)


def _label_x(path: str) -> str:
    nums = _path_numbers(path)
    if len(nums) >= 4:
        return f"{(nums[0] + nums[-2]) / 2:.1f}"
    return "0"


def _label_y(path: str) -> str:
    nums = _path_numbers(path)
    if len(nums) >= 4:
        return f"{(nums[1] + nums[-1]) / 2 - 10:.1f}"
    return "0"


def _path_numbers(path: str) -> list[float]:
    return [float(match) for match in re.findall(r"-?\d+(?:\.\d+)?", path)]


def _distance(a: Point, b: Point) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
