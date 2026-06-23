"""Device hotspot mappings for the two-dimensional lab workbench."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabHotspot:
    """A Streamlit-controlled device hotspot mapped to a state-machine action."""

    key: str
    label: str
    device: str
    action: str
    help: str
    state_key: str = ""
    active_when: str = "truthy"


ARC_HOTSPOTS: tuple[LabHotspot, ...] = (
    LabHotspot("battery", "电池舱", "ARC 实验舱", "load_battery", "将已选 SOC 的虚拟样品放入 ARC 舱体", "battery_loaded"),
    LabHotspot("door", "舱门", "舱门锁扣", "close_arc_door", "关闭 ARC 舱门并同步画布舱门状态", "arc_door_closed"),
    LabHotspot("leak", "气密检测", "压力检测", "start_leak_test", "执行虚拟气密性检测", "leak_test_passed"),
    LabHotspot("vacuum_valve", "真空阀", "真空阀", "open_vacuum_valve", "打开真空阀，激活真空连接线", "vacuum_valve_open"),
    LabHotspot("vacuum_pump", "真空泵", "真空泵", "start_vacuum_pump", "启动真空泵，压力读数下降", "vacuum_pump_on"),
    LabHotspot("nitrogen_valve", "氮气阀", "氮气阀", "open_nitrogen_valve", "打开氮气阀，激活氮气置换路径", "nitrogen_valve_open"),
    LabHotspot("cycle", "置换确认", "20 L 收集罐", "complete_replacement_cycle", "记录一轮抽真空和氮气置换", "replacement_count"),
    LabHotspot("heater", "加热板", "加热板", "start_arc", "启动 ARC 虚拟升温演示", "current_state", "arc_ready"),
    LabHotspot("runaway", "热失控节点", "ARC 热区", "trigger_thermal_runaway", "进入热失控高亮演示", "current_state", "arc_heating"),
    LabHotspot("cooling", "冷却完成", "冷却状态", "finish_cooling", "完成冷却并允许进入采样", "current_state", "thermal_runaway"),
    LabHotspot("bag", "集气袋", "采样袋", "connect_gas_bag", "连接集气袋", "gas_bag_connected"),
    LabHotspot("sampling", "采样阀", "采样阀", "open_sampling_valve", "打开采样阀，激活采样路径", "sampling_valve_open"),
    LabHotspot("sample_done", "完成采样", "采样接口", "close_sampling_valve", "关闭采样阀并完成采样", "gas_bag_filled"),
    LabHotspot("gc", "GC 模块", "气相色谱仪", "start_gc", "启动 GC 教学分析", "gc_started"),
    LabHotspot("gc_done", "完成 GC", "色谱图", "finish_gc", "完成 GC 分析并显示结果状态", "gc_finished"),
    LabHotspot("gas_volume", "产气量", "产气量记录", "calculate_gas_volume", "记录产气量教学状态", "gas_volume_calculated"),
    LabHotspot("lel", "LFL 模块", "LFL 教学评价", "calculate_lel", "执行 LFL 教学风险评价", "lel_calculated"),
    LabHotspot("report", "报告终端", "报告摘要", "generate_report", "生成报告摘要记录", "current_state", "report_generated"),
)


def hotspot_status(hotspot: LabHotspot, state: dict) -> str:
    """Return idle, active, or done for a hotspot."""

    value = state.get(hotspot.state_key) if hotspot.state_key else None
    if hotspot.active_when == "truthy":
        return "done" if bool(value) else "idle"
    return "done" if value == hotspot.active_when else "idle"


def hotspot_button_label(hotspot: LabHotspot, state: dict) -> str:
    """Return a compact label that reads like a clickable device surface."""

    status = hotspot_status(hotspot, state)
    suffix = "已完成" if status == "done" else "点击"
    return f"{hotspot.label} · {suffix}"
