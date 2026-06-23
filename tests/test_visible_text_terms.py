from pathlib import Path

from app.utils.report_generator import generate_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _visible_text_files() -> list[Path]:
    roots = [
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "docs",
    ]
    files: list[Path] = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "CHANGELOG.md",
    ]
    for root in roots:
        files.extend(
            path
            for path in root.rglob("*")
            if path.suffix.lower() in {".py", ".csv", ".json", ".md"}
        )
    return [path for path in files if path.exists() and "__pycache__" not in path.parts]


def test_user_visible_text_excludes_forbidden_terms() -> None:
    forbidden = [
        "可" + "怜",
        "莱" + "尔",
        "可燃下限（" + "LE" + "L）",
        "LE" + "L_mix",
        "LFL" + "R",
        "LEL" + "R",
        "爆炸" + "下限",
    ]
    offenders: list[str] = []

    for path in _visible_text_files():
        text = path.read_text(encoding="utf-8")
        for term in forbidden:
            if term in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {term}")

    assert offenders == []


def test_report_uses_lfl_mix_and_risk_ratio_formula_terms() -> None:
    report = generate_report(
        experiment_params={"scene_info": {"scene_label": "S001_实验室通风橱·2.0立方米-可燃"}},
        literature_data={"sample_info": {}, "gas_composition": {}, "flammable_composition": {}},
        calculation_results={
            "lfl_mix": 5.0,
            "space_concentration": 1.0,
            "risk_ratio": 0.2,
            "risk_info": {"level": "低风险", "description": "测试"},
        },
    )

    assert "LFL_mix" in report
    assert "R = C / LFL_mix" in report
    assert "可" + "怜" not in report
    assert "莱" + "尔" not in report
    assert "可燃下限（" + "LE" + "L）" not in report
