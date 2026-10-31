# config.py: all settings of the road network optimization (task 4.8)
# run:  python analysis/network/optimization/main.py A   (from any folder, give the path to main.py)

import sys
from pathlib import Path

SCENARIO = sys.argv[1].upper() if len(sys.argv) > 1 else "A"
BRIDGE = True                 # False = leave the bridge out of the candidates
CHECK_ALL = SCENARIO == "A"   # also try every combination (only A is small enough)
SNAP = 1.0                    # lines closer than 1 m are joined

# paths: the repository root is found from the location of this file, so it does not matter
# from which folder the script is started (this file is MerweLab/analysis/network/optimization/config.py)
ROOT = Path(__file__).resolve().parents[3]
DESIGN = ROOT / "data/network/design/network_design.gpkg"
LAYOUT = ROOT / f"data/network/design/scenario_{SCENARIO}_layout.gpkg"
WIND = ROOT / f"outputs/data/wind/study_area/grid_1m/wind_scenario_{SCENARIO.lower()}_1p5m.tif"
OSM_GRAPH = ROOT / "data/network/osm/osm_walk.graphml"
FACILITY_DIR = ROOT / "data/network/facilities"
OUT = ROOT / "data/network/output"   # all results (csv, gpkg, png) are written here

# how important each indicator is (they add up to 1), one run per set
# green_loss = built length that lies on green space (m)
# cost = building cost of the built paths (relative units, see COST_PER_M)
WEIGHT_SETS = {
    "balanced":     {"access": 0.30, "detour": 0.15, "car": 0.20, "wind": 0.15, "green_loss": 0.12, "cost": 0.08},
    "access_first": {"access": 0.45, "detour": 0.20, "car": 0.10, "wind": 0.10, "green_loss": 0.09, "cost": 0.06},  # walking matters more
    "green_first":  {"access": 0.15, "detour": 0.10, "car": 0.20, "wind": 0.15, "green_loss": 0.30, "cost": 0.10},  # keeping green space matters more
    "no_wind":      {"access": 0.35, "detour": 0.18, "car": 0.23, "wind": 0.00, "green_loss": 0.15, "cost": 0.09},  # to see if the wind data changes the result
}

# building cost per metre of path, by kind of line. relative numbers, no real prices (1 = a normal path)
# the bridge crosses water, so it is much more expensive: its factor is tested in sensitivity.py
BRIDGE_COST = 8
COST_PER_M = {"quay": 1, "exit": 1, "between": 1, "access": 1, "green": 1, "bridge": BRIDGE_COST}

# how important each destination is for daily life (they add up to 1)
DESTINATIONS = {"tram_bus_stop": 0.35, "supermarket": 0.15, "school": 0.10, "gp": 0.10,
                "park": 0.10, "metro": 0.10, "pharmacy": 0.05, "day_care": 0.05}

# dwellings: 3 m per floor, ground floor is not housing, 70 m2 per dwelling
FLOOR_HEIGHT = 3
DWELLING_SIZE = 70
PEOPLE_PER_DWELLING = 1.9  # data from cbs in our study area
CARS_PER_DWELLING = 0.5    # from cbs, also refer to Rotterdam gemeente merwehaven plan 2025
TRIPS_PER_CAR = 2          # we assume one trip out, one back per day

# scaling: random networks used to find the min and max of every indicator
N_SAMPLES = 2000
SEED = 1
