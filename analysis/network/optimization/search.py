# search.py: find the best network (greedy, and every combination as a check)

import itertools

from evaluation import evaluate, total_cost


def greedy(pier, weights, low, high):
    # start with everything built, remove the path that lowers the cost most, until nothing helps
    # one result per possible ramp
    results = []
    for ramp in pier["ramps"]:
        built = list(pier["optional"])
        current = evaluate(pier, built, ramp)
        if current is None:
            continue
        while True:
            best = None
            for s in built:
                trial = [x for x in built if x != s]
                r = evaluate(pier, trial, ramp)
                if r and (best is None or total_cost(r, weights, low, high) < best[0]):
                    best = (total_cost(r, weights, low, high), trial, r)
            if best is None or best[0] >= total_cost(current, weights, low, high):
                break
            built, current = best[1], best[2]
        results.append({"method": "greedy", "ramp": ramp, "built": built,
                        "score": total_cost(current, weights, low, high), **current})
    return results


def all_combinations(pier):
    # every combination of optional paths and every ramp, scored once (the weights are applied later)
    found = []
    optional = pier["optional"]
    for n in range(len(optional) + 1):
        for built in itertools.combinations(optional, n):
            for ramp in pier["ramps"]:
                r = evaluate(pier, list(built), ramp)
                if r:
                    found.append((list(built), ramp, r))
    return found


def best_of_all(found, weights, low, high):
    best = None
    for built, ramp, r in found:
        c = total_cost(r, weights, low, high)
        if best is None or c < best["score"]:
            best = {"method": "all combinations", "ramp": ramp, "built": built, "score": c, **r}
    return best
