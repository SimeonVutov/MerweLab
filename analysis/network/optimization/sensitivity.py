# sensitivity.py: how much do the cost assumptions change the result? (scenario A, balanced weights)
# 1. cost of the bridge per metre, as a multiple of a normal path
# 2. weight of the cost indicator (the other weights are scaled so that the sum stays 1)
# run from the repository root:  python analysis/network/optimization/sensitivity.py A

import pandas as pd

from config import OUT, SCENARIO, BRIDGE, CHECK_ALL, COST_PER_M, WEIGHT_SETS
from evaluation import make_scale, total_cost
from main import prepare
from pier_graph import set_costs
from search import greedy, all_combinations, best_of_all

BRIDGE_FACTORS = [0, 1, 2, 4, 8, 16, 32]   # 0 = the bridge is free
COST_WEIGHTS = [0, 0.04, 0.08, 0.15, 0.25, 0.40]
BASE = "balanced"


def best_network(pier, weights):
    # scale with the current costs, then the best network (every combination if possible, else greedy)
    low, high = make_scale(pier)
    results = greedy(pier, weights, low, high)
    best = min(results, key=lambda x: x["score"])
    if CHECK_ALL:
        best = best_of_all(all_combinations(pier), weights, low, high)
    return best


def row(label, value, best, pier):
    return {label: value, "ramp": best["ramp"], "bridge_built": any(s in pier["bridge_ids"] for s in best["built"]),
            "built": " ".join(best["built"]), "access": round(best["access"], 1), "wind": round(best["wind"], 2),
            "car": round(best["car"], 1), "green_loss": round(best["green_loss"], 1), "cost": round(best["cost"], 1)}


def main():
    pier, _ = prepare()
    weights = WEIGHT_SETS[BASE]

    rows = []
    if pier["bridge_ids"]:
        for f in BRIDGE_FACTORS:
            set_costs(pier, {**COST_PER_M, "bridge": f})
            rows.append(row("bridge_cost_factor", f, best_network(pier, weights), pier))
        table = pd.DataFrame(rows)
        print("\nbridge cost per metre (x a normal path), balanced weights")
        print(table.to_string(index=False))
        table.to_csv(f"{OUT}/sensitivity_bridge_cost_{SCENARIO}.csv", index=False)

    set_costs(pier, COST_PER_M)
    rows = []
    for cw in COST_WEIGHTS:
        others = {k: v for k, v in weights.items() if k != "cost"}
        scale = (1 - cw) / sum(others.values())
        w = {**{k: v * scale for k, v in others.items()}, "cost": cw}
        rows.append(row("cost_weight", cw, best_network(pier, w), pier))
    table = pd.DataFrame(rows)
    print("\nweight of the cost indicator, balanced weights, bridge cost x", COST_PER_M["bridge"])
    print(table.to_string(index=False))
    table.to_csv(f"{OUT}/sensitivity_cost_weight_{SCENARIO}.csv", index=False)


if __name__ == "__main__":
    main()
