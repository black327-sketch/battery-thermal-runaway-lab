from app.utils.equipment_svg import ARC_LAYOUT, render_full_workbench_svg
from app.utils.lab_canvas import (
    CanvasSettings,
    build_svg_canvas_html,
    remove_source_fragments_for_text,
    validate_svg_markup,
)
from app.utils.lab_connections import flatten_layout_ports, validate_connection_endpoints
from app.utils.literature_device_svg import (
    LITERATURE_LAYOUT,
    render_explosion_chamber_heating_platform_svg,
)
from app.utils.literature_experiment_state import initial_literature_experiment_state


def test_validate_svg_markup_accepts_complete_svg() -> None:
    ok, message = validate_svg_markup("<svg viewBox='0 0 10 10'><text>OK</text></svg>")

    assert ok is True
    assert message == ""


def test_validate_svg_markup_rejects_partial_svg_fragment() -> None:
    ok, message = validate_svg_markup("<polyline points='0,0 10,10' />")

    assert ok is False
    assert "源码片段" in message


def test_remove_source_fragments_for_text_strips_svg_tags() -> None:
    text = remove_source_fragments_for_text(
        "<svg><text x='1'>设备标签</text><polyline points='0,0 1,1'/></svg>"
    )

    assert "<polyline" not in text
    assert "<text x=" not in text
    assert "设备标签" in text


def test_zoomed_canvas_html_allows_scroll_instead_of_clipping() -> None:
    html = build_svg_canvas_html(
        "<svg viewBox='0 0 1600 900'></svg>",
        title="ARC 通用模式数字孪生画布",
        settings=CanvasSettings(
            zoom=1.75,
            fullscreen=True,
            detailed=True,
            show_device_labels=True,
            show_pipeline_labels=True,
            show_risk_overlay=True,
            runaway_focus=False,
        ),
        height=700,
    )

    assert "overflow: auto;" in html
    assert "width: calc(100% * 1.75);" in html
    assert "overscroll-behavior: contain;" in html


def test_device_svg_helpers_return_complete_svg_only() -> None:
    arc_svg = render_full_workbench_svg({"current_state": "sample_preparation"})
    lit_svg = render_explosion_chamber_heating_platform_svg(initial_literature_experiment_state())

    for svg in (arc_svg, lit_svg):
        ok, _ = validate_svg_markup(svg)
        assert ok is True
        assert svg.strip().startswith("<svg")
        assert svg.strip().endswith("</svg>")
        assert "<div" not in svg


def test_arc_workbench_uses_large_fit_friendly_viewbox_and_connections() -> None:
    svg = render_full_workbench_svg(
        {
            "current_state": "gas_sampling",
            "replacement_count": 3,
            "gas_bag_connected": True,
            "sampling_valve_open": True,
            "gc_finished": True,
            "lel_calculated": True,
        }
    )

    assert 'viewBox="0 0 1680 980"' in svg
    assert svg.count('class="connection-line') >= 9
    assert 'id="connection-legend"' in svg
    assert "实线：已连接" in svg
    assert "虚线：当前作用连接" in svg
    assert "红色：异常 / 阻断" in svg
    assert "ARC 实验舱" in svg
    assert "20 L 收集罐" in svg
    assert "气相色谱仪" in svg
    assert "质谱仪" in svg
    assert "电脑" in svg
    assert "压力传感器" in svg
    assert "可燃极限教学评估" in svg
    assert "Connection legend" not in svg
    assert "GC analyzer" not in svg
    assert "气象色谱仪" not in svg


def test_arc_nitrogen_connection_active_only_when_valve_open_or_filling() -> None:
    idle_svg = render_full_workbench_svg({"current_state": "sample_preparation"})
    filling_svg = render_full_workbench_svg(
        {"current_state": "nitrogen_filling", "nitrogen_valve_open": True}
    )
    completed_closed_svg = render_full_workbench_svg(
        {
            "current_state": "atmosphere_replacement",
            "replacement_count": 1,
            "cycle_nitrogen_done": True,
            "nitrogen_valve_open": False,
        }
    )

    assert 'id="connection-n2-to-arc"' in idle_svg
    n2_path = 'd="M1478.0 170.0 L1420.0 202.0 L1196.0 250.0 L1062.0 322.0"'
    n2_ports = 'data-from="nitrogen:out" data-to="arc:nitrogen_in"'
    assert f'id="connection-n2-to-arc" {n2_path} class="connection-line physical"' in idle_svg
    assert n2_ports in idle_svg
    assert f'id="connection-n2-to-arc" {n2_path} class="connection-line physical active"' in filling_svg
    assert f'id="connection-n2-to-arc" {n2_path} class="connection-line physical"' in completed_closed_svg
    assert f'id="connection-n2-to-arc" {n2_path} class="connection-line physical active"' not in completed_closed_svg


def test_arc_workbench_labels_nitrogen_and_gc_directions_without_direct_gc_to_n2() -> None:
    svg = render_full_workbench_svg({"current_state": "sample_preparation"})

    assert "氮气瓶 → 氮气阀 → ARC 舱体 / 收集系统" in svg
    assert "氮气置换路径" in svg
    assert "采样袋 → GC" in svg
    assert "GC → 氮气瓶" not in svg
    assert "气相色谱仪 → 氮气瓶" not in svg


def test_literature_device_has_connection_legend() -> None:
    svg = render_explosion_chamber_heating_platform_svg(initial_literature_experiment_state())

    assert 'viewBox="0 0 1180 760"' in svg
    assert svg.count('class="connection-line') >= 9
    assert 'id="connection-legend"' in svg
    assert "关键流向" in svg
    assert "氮气瓶 → 防爆舱" in svg
    assert "采样口 → 集气袋" in svg
    assert "集气袋 → GC" in svg
    assert "GC → 质谱仪" in svg
    assert "质谱仪 → 电脑" in svg
    assert "VAC line" not in svg
    assert "sample line" not in svg
    assert "气象色谱仪" not in svg


def test_arc_layout_uses_shared_anchors_for_pressure_and_lfl_panel() -> None:
    svg = render_full_workbench_svg({"current_state": "arc_heating", "selected_soc": 75})

    arc = ARC_LAYOUT["devices"]["arc"]
    lfl = ARC_LAYOUT["devices"]["lfl"]
    assert lfl["y"] >= arc["y"] + arc["h"] + 200
    assert 'id="connection-pressure-sensor-to-daq"' in svg
    assert 'data-label="压力信号"' in svg
    assert f'cx="{arc["anchors"]["pressure_out"][0]}" cy="{arc["anchors"]["pressure_out"][1]}"' in svg
    assert f'transform="translate({lfl["x"]} {lfl["y"]})"' in svg


def test_arc_gcms_and_signal_chain_endpoint_anchors_are_rendered() -> None:
    svg = render_full_workbench_svg({"current_state": "gc_analysis", "gc_started": True})

    expected_ports = [
        'data-from="sampling_bag:gas_out" data-to="gc:sample_in"',
        'data-from="gc:analysis_out" data-to="ms:analysis_in"',
        'data-from="ms:data_out" data-to="computer:data_in"',
        'data-from="daq:data_out" data-to="computer:data_in"',
        'data-from="gc:data_out" data-to="lfl:data_in"',
    ]
    for expected in expected_ports:
        assert expected in svg

    assert "T/P/V 信号 → DAQ" in svg
    assert "压力信号" in svg


def test_literature_layout_endpoint_anchors_and_labels_are_rendered() -> None:
    svg = render_explosion_chamber_heating_platform_svg(initial_literature_experiment_state())

    assert 'id="literature-ports"' in svg
    assert 'id="connection-lit-bag-gc" d="M864.0 396.0 L876.0 398.0 L894.0 414.0 L904.0 418.0"' in svg
    assert 'data-from="bag:out" data-to="gc:in"' in svg
    for device, port in [
        ("chamber", "sample_out"),
        ("bag", "in"),
        ("gc", "in"),
        ("gc", "out"),
        ("ms", "in"),
        ("computer", "data_in"),
        ("daq", "pressure_in"),
    ]:
        x, y = LITERATURE_LAYOUT["anchors"][device][port]
        assert f'cx="{x}" cy="{y}"' in svg

    assert "ARC 热失控测试单元" in svg
    assert "压力信号 → DAQ" in svg
