from app.utils.asset_utils import asset_exists, resolve_asset_path


MECHANISM_ASSETS = [
    "assets/mechanism/01_thermal_runaway_overview.png",
    "assets/mechanism/02_sei_decomposition.png",
    "assets/mechanism/03_separator_melting_short_circuit.png",
    "assets/mechanism/04_cathode_oxygen_electrolyte_oxidation.png",
    "assets/mechanism/05_hydrogen_generation_pathway.png",
    "assets/mechanism/06_co_co2_generation_pathway.png",
    "assets/mechanism/07_venting_gas_cloud.png",
    "assets/mechanism/08_lel_risk_evaluation.png",
]


def test_mechanism_assets_exist():
    missing = [asset for asset in MECHANISM_ASSETS if not asset_exists(asset)]
    assert missing == []


def test_resolve_asset_path_keeps_paths_under_project_root():
    path = resolve_asset_path("assets/mechanism/01_thermal_runaway_overview.png")
    assert path.name == "01_thermal_runaway_overview.png"
    assert "assets" in path.parts
