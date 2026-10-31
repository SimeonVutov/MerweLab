# Task 4.8 step 4: optimize the road network on the pier
# choose which candidate paths to build, and where the ramp of the underground garage goes
# run from the repository root:  python analysis/network/optimization/main.py A

import os

from config import SCENARIO, BRIDGE, CHECK_ALL, WEIGHT_SETS, DESTINATIONS, OUT
from data_loading import load_design, load_wind, load_city
from geometry import snap_lines, cut_lines, add_wind
from pier_graph import build_pier
from evaluation import evaluate, make_scale, total_cost
from search import greedy, all_combinations, best_of_all
from plotting import save_results


def prepare():
    # data, clean lines, graph
    os.makedirs(OUT, exist_ok=True)
    lines, entrances, buildings, share, green = load_design()
    wind_map, transform = load_wind()
    osm, starts = load_city()
    lines = snap_lines(lines)
    pieces = add_wind(cut_lines(lines), wind_map, transform)
    pier = build_pier(lines, pieces, entrances, share, osm, starts, green)
    return pier, buildings


def main():
    pier, buildings = prepare()

    # scale the indicators, and try every combination once (only A)
    low, high = make_scale(pier)
    found = all_combinations(pier) if CHECK_ALL else None

    tag = "_bridge" if (BRIDGE and pier["bridge_ids"]) else ""
    for name, weights in WEIGHT_SETS.items():
        results = greedy(pier, weights, low, high)
        best = min(results, key=lambda x: x["score"])
        print(f"\n[{name}] greedy best: score {best['score']:.3f}, ramp at {best['ramp']}, built {best['built']}")
        if CHECK_ALL:
            full = best_of_all(found, weights, low, high)
            results.append(full)
            print(f"[{name}] all combinations best: score {full['score']:.3f}, ramp at {full['ramp']}, built {full['built']}")
        save_results(pier, buildings, results, best, name + tag)

        # test: the same network, but with the bridge built
        if pier["bridge_ids"] and not set(pier["bridge_ids"]) <= set(best["built"]):
            r = evaluate(pier, best["built"] + pier["bridge_ids"], best["ramp"])
            print("  without bridge:", {k: round(v, 2) for k, v in best.items() if k in weights}, "score", round(total_cost(best, weights, low, high), 3))
            print("  with bridge:   ", {k: round(v, 2) for k, v in r.items()}, "score", round(total_cost(r, weights, low, high), 3))

    # walking distance outside the pier, from each gate to each destination
    for g in pier["gates"]:
        print(g, {t: round(pier["outside"][(g, t)]) for t in DESTINATIONS})
    print("done, results saved in", OUT)


if __name__ == "__main__":
    main()
