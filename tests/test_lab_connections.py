from app.utils.lab_connections import (
    LabConnection,
    build_orthogonal_path,
    render_connection_legend,
    render_connection_paths,
    render_port_debug_nodes,
    validate_connection_endpoints,
)


def test_connection_paths_encode_state_classes() -> None:
    markup = render_connection_paths(
        [
            LabConnection("a", "installed", "M0 0 L10 10"),
            LabConnection("b", "active", "M0 0 L20 20", active=True),
            LabConnection("c", "alert", "M0 0 L30 30", kind="virtual", alert=True),
        ]
    )

    assert 'class="connection-line physical"' in markup
    assert 'class="connection-line physical active"' in markup
    assert 'class="connection-line virtual alert"' in markup
    assert 'data-label="active"' in markup


def test_semantic_connection_generates_and_validates_port_endpoints() -> None:
    ports = {
        "pump": {"out": (10, 20)},
        "chamber": {"vacuum_in": (80, 20)},
    }
    connection = LabConnection.from_ports(
        key="vacuum",
        label="真空泵 → 防爆舱",
        ports=ports,
        from_device="pump",
        from_port="out",
        to_device="chamber",
        to_port="vacuum_in",
        via=[(40, 20)],
    )

    assert connection.path == "M10.0 20.0 L40.0 20.0 L80.0 20.0"
    assert validate_connection_endpoints([connection], ports) == []
    markup = render_connection_paths([connection])
    assert 'data-from="pump:out"' in markup
    assert 'data-to="chamber:vacuum_in"' in markup


def test_connection_endpoint_validator_reports_mismatch() -> None:
    ports = {
        "pump": {"out": (10, 20)},
        "chamber": {"vacuum_in": (80, 20)},
    }
    connection = LabConnection(
        key="bad",
        label="bad",
        path=build_orthogonal_path((10, 20), (81, 20)),
        from_device="pump",
        from_port="out",
        to_device="chamber",
        to_port="vacuum_in",
    )

    errors = validate_connection_endpoints([connection], ports)

    assert errors
    assert "bad: end" in errors[0]


def test_port_debug_nodes_are_hidden_by_default() -> None:
    markup = render_port_debug_nodes({"device": {"port": (1, 2)}})

    assert 'id="canvas-port-debug"' in markup
    assert 'class="port-debug-layer hidden"' in markup
    assert 'data-port="device.port"' in markup


def test_connection_legend_explains_solid_dashed_and_alert_lines() -> None:
    markup = render_connection_legend(10, 20)

    assert 'id="connection-legend"' in markup
    assert "实线：已连接" in markup
    assert "虚线：当前作用连接" in markup
    assert "红色：异常 / 阻断" in markup
