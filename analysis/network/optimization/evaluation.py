# evaluation.py: score one network, and scale the indicators to 0..1

import random
import networkx as nx
import numpy as np
import pandas as pd
from shapely.geometry import Point

from config import DESTINATIONS, N_SAMPLES, SEED


def evaluate(pier, built, ramp):
    # built = optional seg_ids that are built, ramp = entrance node of the garage
    # returns the indicators, or None if the network does not work (a building or the ramp can not be reached)
    key = (frozenset(built), ramp)
    if key in pier["cache"]:
        return pier["cache"][key]
    pier["cache"][key] = _evaluate(pier, built, ramp)
    return pier["cache"][key]


def _evaluate(pier, built, ramp):
    G, outside, share = pier["G"], pier["outside"], pier["share"]
    keep = pier["fixed"] | set(built)
    H = G.edge_subgraph([(u, v) for u, v, s in G.edges(data="seg_id") if s in keep])
    if ramp not in H:
        return None
    # distance from every gate to every node on the pier (the bridge gate only if the bridge is built)
    from_gate = {g: nx.single_source_dijkstra_path_length(H, g, weight="length") for g in pier["gates"] if g in H}
    res = {"access": 0, "detour": 0, "wind": 0}
    for b, ents in pier["ent_of"].items():
        best = None
        for e in ents:
            if e == ramp:
                continue  # people do not walk in through the garage ramp
            for g in from_gate:
                if e not in from_gate[g]:
                    continue
                inside = from_gate[g][e]
                acc = sum(w * (inside + outside[(g, t)]) for t, w in DESTINATIONS.items())
                if best is None or acc < best[0]:
                    best = (acc, e, g, inside)
        if best is None:
            return None  # this building has no walking entrance that can be reached (not counting the ramp)
        acc, e, g, inside = best
        straight = Point(e).distance(Point(g))
        path = nx.shortest_path(H, e, g, weight="length")
        edges = [H.edges[u, v] for u, v in zip(path[:-1], path[1:])]
        wind = sum(x["wind"] * x["length"] for x in edges) / max(inside, 1)
        res["access"] += share[b] * acc
        res["detour"] += share[b] * inside / max(straight, 1)
        res["wind"] += share[b] * wind
    # cars drive from the nearest exit to the ramp (not over the bridge)
    res["car"] = min(from_gate[g].get(ramp, np.inf) for g in pier["car_gates"] if g in from_gate)
    if np.isinf(res["car"]):
        return None
    # green space that is used by the built paths (m), and what they cost (relative)
    res["green_loss"] = sum(pier["green_length"][s] for s in built)
    res["cost"] = sum(pier["cost_of"][s] for s in built)
    return res


def make_scale(pier):
    # min and max of every indicator, from random networks (50-100% of the optional paths built)
    random.seed(SEED)
    samples = []
    for _ in range(N_SAMPLES):
        p = random.uniform(0.5, 1)
        built = [s for s in pier["optional"] if random.random() < p]
        r = evaluate(pier, built, random.choice(pier["ramps"]))
        if r:
            samples.append(r)
    samples = pd.DataFrame(samples)
    low, high = samples.min(), samples.max()
    high[high == low] = low[high == low] + 1  # avoid dividing by 0 if an indicator never changes
    print(f"{len(samples)} random networks were valid, used for scaling")
    return low, high


def total_cost(res, weights, low, high):
    # weighted sum of the scaled indicators, lower is better
    return sum(w * (res[k] - low[k]) / (high[k] - low[k]) for k, w in weights.items())
