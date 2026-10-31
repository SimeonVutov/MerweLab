# export_web.py: save the best network of one scenario as GeoJSON for the Cesium website
# run (one scenario at a time):  python analysis/network/optimization/export_web.py A balanced
# writes data/network/for_cesium/network_scenario_a.geojson (lines, garage ramp, entrances) and network_scenario_a_summary.json
# coordinates are lon/lat (EPSG:4326), the format Cesium reads

import json
import os
import sys
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from config import ROOT, SCENARIO, BRIDGE, CHECK_ALL, WEIGHT_SETS
from evaluation import make_scale
from main import prepare
from plotting import final_network
from search import greedy, all_combinations, best_of_all

RUN = sys.argv[2] if len(sys.argv) > 2 else "balanced"   # which weight set
WEB = ROOT / "data/network/for_cesium"
NAME = {"A": "scenario_a", "B": "scenario_b"}[SCENARIO]   # same names as config/scenarios.yaml


def main():
    os.makedirs(WEB, exist_ok=True)
    pier, buildings = prepare()
    weights = WEIGHT_SETS[RUN]

    # best network, found in the same way as in main.py
    low, high = make_scale(pier)
    results = greedy(pier, weights, low, high)
    best = min(results, key=lambda x: x["score"])
    if CHECK_ALL:
        best = best_of_all(all_combinations(pier), weights, low, high)
    print(f"[{RUN}] ramp at {best['ramp']}, built {best['built']}")

    # layer 1: the paths (built or not), with what the website can show
    paths, car_trips = final_network(pier, best["built"], best["ramp"], buildings)
    paths["built"] = (paths["use"] != "not built").astype(int)   # 1 = built, 0 = not built
    paths["layer"] = "path"

    # layer 2: the garage ramp, layer 3: the entrances of the buildings
    ramp = gpd.GeoDataFrame({"layer": ["garage_ramp"]}, geometry=[Point(best["ramp"])], crs=28992)
    entrances = pier["entrances"][["building_id", "geometry"]].copy()
    entrances["layer"] = "entrance"

    both = pd.concat([paths, ramp, entrances], ignore_index=True)
    both["scenario"] = NAME
    for col in ["built", "residents_walking", "car_trips_per_day"]:   # whole numbers (the points have no value)
        both[col] = both[col].astype("Int64")
    both = gpd.GeoDataFrame(both, geometry="geometry", crs=28992).to_crs(4326)
    both.to_file(WEB / f"network_{NAME}.geojson", driver="GeoJSON", COORDINATE_PRECISION=7)

    # indicators of the chosen network, for the dashboard
    summary = {"scenario": NAME, "weight_set": RUN, "weights": weights,
               "bridge_in_candidates": bool(pier["bridge_ids"]),
               "bridge_built": any(s in best["built"] for s in pier["bridge_ids"]),
               "built_paths": sorted(best["built"]), "ramp_rd": list(best["ramp"]),
               "car_trips_per_day": round(float(car_trips)),
               "indicators": {k: round(float(best[k]), 2) for k in ["access", "detour", "wind", "car", "green_loss", "cost"]}}
    with open(WEB / f"network_{NAME}_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("written", WEB / f"network_{NAME}.geojson")


if __name__ == "__main__":
    main()
