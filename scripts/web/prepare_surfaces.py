from download_grids import ROOT
from prepare_buildings import prepare_models


SOURCES = {
    "shared": [],
    "water": ["water_surface.obj"],
    "baseline": ["baseline/ground_existing.obj", "baseline/quays_existing.obj"],
    "scenario_a": ["scenario_a/pavement_v1.obj", "scenario_a/green_areas_v1.obj"],
    "scenario_b": ["scenario_b/pavement_v2.obj", "scenario_b/green_areas_v2.obj"],
}


if __name__ == "__main__":
    prepare_models(SOURCES, ROOT / "data/web/surfaces")
