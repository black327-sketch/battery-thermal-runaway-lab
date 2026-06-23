"""report_context.py —— 实验报告上下文收集。

从 session_state 和项目数据中收集报告所需的结构化上下文，
供 report_sections 和 report_docx 使用。
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
EXP_DIR = DATA_DIR / "experiment"


def _safe_get(mapping: Mapping | None, key: str, default: object = "未记录") -> object:
    if not mapping:
        return default
    value = mapping.get(key, default)
    if value is None or value == "":
        return default
    return value


def _fmt(value: object, digits: int = 2, none_text: str = "无法计算") -> str:
    if value is None:
        return none_text
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def collect_report_context(
    experiment_params: Mapping | None,
    literature_data: Mapping | None,
    calculation_results: Mapping | None,
) -> dict[str, Any]:
    """收集报告所需的完整上下文，统一为 dict。"""

    experiment_params = experiment_params or {}
    literature_data = literature_data or {}
    calculation_results = calculation_results or {}

    now = datetime.now()

    # ── 报告标题与基本信息 ──
    report_title = "《锂电池热失控产气与燃爆风险评价实验报告》"
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S")
    report_id = _safe_get(experiment_params, "report_id", f"VEXP-{now.strftime('%Y%m%d-%H%M%S')}")

    # ── 样本信息 ──
    sample_info = _safe_get(literature_data, "sample_info", {})
    if not isinstance(sample_info, Mapping):
        sample_info = {}
    sample_label = _safe_get(sample_info, "sample_label", _safe_get(sample_info, "source", "未选择"))
    sample_source = _safe_get(sample_info, "source", "未记录")
    sample_soc = _safe_get(sample_info, "soc", "未记录")
    sample_notes = _safe_get(sample_info, "notes", "未记录")
    sample_doi = _safe_get(sample_info, "DOI", _safe_get(sample_info, "doi", "待补充"))
    sample_reference = _safe_get(sample_info, "reference", _safe_get(sample_info, "citation", "待补充"))
    sample_data_type = _safe_get(sample_info, "data_type", "未记录")
    sample_data_status = _safe_get(sample_info, "data_status", "未记录")

    # ── 场景信息 ──
    scene_info = _safe_get(experiment_params, "scene_info", {})
    if not isinstance(scene_info, Mapping):
        scene_info = {}
    scene_label = _safe_get(scene_info, "scene_label", _safe_get(scene_info, "scenario_id", "未记录"))
    scene_volume = _safe_get(scene_info, "room_volume_m3", "未记录")
    scene_temp = _safe_get(scene_info, "temp_c", "未记录")
    scene_pressure = _safe_get(scene_info, "pressure_kpa", "未记录")
    scene_ventilation = _safe_get(scene_info, "ventilation", "未记录")

    total_gas_l = _safe_get(experiment_params, "total_gas_l", 10.0)
    ventilation_factor = _safe_get(experiment_params, "ventilation_factor", 1.0)

    # ── 气体组成 ──
    gas_composition = _safe_get(literature_data, "gas_composition", {})
    if not isinstance(gas_composition, Mapping):
        gas_composition = {}
    flammable_composition = _safe_get(literature_data, "flammable_composition", {})
    if not isinstance(flammable_composition, Mapping):
        flammable_composition = {}
    flammable_fraction = _safe_get(literature_data, "flammable_fraction", 0.0)

    # ── 计算结果 ──
    normalized = _safe_get(calculation_results, "normalized", {})
    if not isinstance(normalized, Mapping):
        normalized = {}
    lfl_constants = _safe_get(calculation_results, "lfl_constants", {})
    if not isinstance(lfl_constants, Mapping):
        lfl_constants = {}
    lfl_mix = _safe_get(calculation_results, "lfl_mix", None)
    space_concentration = _safe_get(calculation_results, "space_concentration", None)
    risk_ratio = _safe_get(calculation_results, "risk_ratio", None)
    risk_info = _safe_get(calculation_results, "risk_info", {})
    if not isinstance(risk_info, Mapping):
        risk_info = {}
    risk_level = _safe_get(risk_info, "level", _safe_get(calculation_results, "risk_level", "无法评价"))
    risk_description = _safe_get(risk_info, "description", _safe_get(calculation_results, "risk_description", "缺少有效风险评价信息。"))

    # ── 交互状态 ──
    interactive_state = _safe_get(experiment_params, "interactive_state", {})
    if not isinstance(interactive_state, Mapping):
        interactive_state = {}
    gas_volume_status = _safe_get(experiment_params, "gas_volume_status", {})
    if not isinstance(gas_volume_status, Mapping):
        gas_volume_status = {}
    score_summary = _safe_get(experiment_params, "score_summary", {})
    if not isinstance(score_summary, Mapping):
        score_summary = {}
    active_dataset = _safe_get(experiment_params, "active_dataset", {})
    if not isinstance(active_dataset, Mapping):
        active_dataset = {}
    experiment_mode = _safe_get(experiment_params, "experiment_mode",
                                _safe_get(interactive_state, "experiment_mode", "教学ARC模式"))

    # ── 文献数据（曾垂辉等2026） ──
    literature_meta = _load_csv_rows("literature_zeng_2026_metadata.csv")
    literature_battery = _load_csv_rows("literature_zeng_2026_battery_sample.csv")
    literature_key_points = _load_csv_rows("literature_zeng_2026_arc_key_points.csv")
    literature_gc = _load_csv_rows("literature_zeng_2026_gc_composition.csv")

    lit_meta = literature_meta[0] if literature_meta else {}
    lit_battery = literature_battery[0] if literature_battery else {}
    lit_gc_pending = sum(1 for r in literature_gc if r.get("source_type") == "pending_user_input")

    # ── 数据源登记表 ──
    registry_rows = _load_registry()

    # ── 装置图片路径 ──
    def _collect_images(subdir: str) -> list[Path]:
        d = PROJECT_ROOT / "assets" / subdir
        if not d.exists():
            return []
        return sorted([p for p in d.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}])

    sumf_images = _collect_images("sumf")
    facility_images = _collect_images("facility")
    mechanism_images = _collect_images("mechanism")

    return {
        "report_title": str(report_title),
        "report_id": str(report_id),
        "generated_at": generated_at,
        "now": now,
        # 样本
        "sample_label": str(sample_label),
        "sample_source": str(sample_source),
        "sample_soc": str(sample_soc),
        "sample_notes": str(sample_notes),
        "sample_doi": str(sample_doi),
        "sample_reference": str(sample_reference),
        "sample_data_type": str(sample_data_type),
        "sample_data_status": str(sample_data_status),
        # 场景
        "scene_label": str(scene_label),
        "scene_volume": str(scene_volume),
        "scene_temp": str(scene_temp),
        "scene_pressure": str(scene_pressure),
        "scene_ventilation": str(scene_ventilation),
        "total_gas_l": float(total_gas_l) if total_gas_l is not None else 0.0,
        "ventilation_factor": float(ventilation_factor) if ventilation_factor is not None else 1.0,
        # 气体
        "gas_composition": gas_composition,
        "flammable_composition": flammable_composition,
        "flammable_fraction": float(flammable_fraction) if flammable_fraction is not None else 0.0,
        # 计算
        "normalized": normalized,
        "lfl_constants": lfl_constants,
        "lfl_mix": float(lfl_mix) if lfl_mix is not None else None,
        "space_concentration": float(space_concentration) if space_concentration is not None else None,
        "risk_ratio": float(risk_ratio) if risk_ratio is not None else None,
        "risk_level": str(risk_level),
        "risk_description": str(risk_description),
        # 交互
        "interactive_state": interactive_state,
        "gas_volume_status": gas_volume_status,
        "score_summary": score_summary,
        "active_dataset": active_dataset,
        "experiment_mode": str(experiment_mode),
        # 文献
        "lit_meta": lit_meta,
        "lit_battery": lit_battery,
        "lit_key_points": literature_key_points,
        "lit_gc_pending": lit_gc_pending,
        # 数据源
        "registry_rows": registry_rows,
        # 图片
        "sumf_images": sumf_images,
        "facility_images": facility_images,
        "mechanism_images": mechanism_images,
    }


def _load_csv_rows(file_name: str) -> list[dict[str, str]]:
    path = EXP_DIR / file_name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_registry() -> list[list[object]]:
    path = EXP_DIR / "data_source_registry.csv"
    if not path.exists():
        return [["data_source_registry", "未找到", "pending_user_input", "否", "待补充数据源登记表"]]
    rows: list[list[object]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append([
                row.get("data_file", ""),
                row.get("data_type", ""),
                row.get("source_type", ""),
                "是" if str(row.get("is_literature", "")).lower() == "true" else "否",
                row.get("notes", ""),
            ])
    return rows or [["data_source_registry", "空表", "pending_user_input", "否", "待补充数据源登记记录"]]
