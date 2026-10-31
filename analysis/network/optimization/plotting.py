# plotting.py: final network, csv, gpkg and map

import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from config import OUT, SCENARIO, PEOPLE_PER_DWELLING, CARS_PER_DWELLING, TRIPS_PER_CAR


def final_network(pier, built, ramp, buildings):
    # which edges are built, which are car road, how many people walk on them
    G, outside, share = pier["G"], pier["outside"], pier["share"]
    keep = pier["fixed"] | set(built)
    H = G.edge_subgraph([(u, v) for u, v, s in G.edges(data="seg_id") if s in keep]).copy()
    gate = min(pier["car_gates"], key=lambda g: nx.shortest_path_length(H, g, ramp, weight="length"))
    car_path = nx.shortest_path(H, gate, ramp, weight="length")
    car_edges = {frozenset(e) for e in zip(car_path[:-1], car_path[1:])}
    walkers = {frozenset(e): 0 for e in H.edges}
    for b, ents in pier["ent_of"].items():
        # people walk to the bus/tram stop: best entrance + gate for that trip
        options = [(nx.shortest_path_length(H, e, g, weight="length") + outside[(g, "tram_bus_stop")], e, g)
                   for e in ents for g in pier["gates"] if e != ramp and e in H and g in H and nx.has_path(H, e, g)]
        _, e, g = min(options)
        path = nx.shortest_path(H, e, g, weight="length")
        for u, v in zip(path[:-1], path[1:]):
            walkers[frozenset((u, v))] += share[b] * buildings["dwellings"].sum() * PEOPLE_PER_DWELLING
    car_trips = buildings["dwellings"].sum() * CARS_PER_DWELLING * TRIPS_PER_CAR
    rows = []
    for u, v, d in G.edges(data=True):
        k = frozenset((u, v))
        is_built = d["seg_id"] in keep
        use = "not built" if not is_built else ("car + walk" if k in car_edges else "walk + bike")
        rows.append({"seg_id": d["seg_id"], "kind": d["kind"], "use": use, "wind": round(d["wind"], 1),
                     "residents_walking": round(walkers.get(k, 0)) if is_built else 0,
                     "car_trips_per_day": round(car_trips) if k in car_edges else 0, "geometry": d["geom"]})
    return gpd.GeoDataFrame(rows, crs=28992), car_trips


def save_results(pier, buildings, results, best, run_name):
    # results = all result rows of this run, best = the row that is used for the map
    table = pd.DataFrame(results)
    table["built"] = table["built"].apply(lambda x: " ".join(x))
    table.round(3).to_csv(f"{OUT}/results_{SCENARIO}_{run_name}.csv", index=False)

    final, car_trips = final_network(pier, best["built"], best["ramp"], buildings)
    final.to_file(f"{OUT}/network_{SCENARIO}_{run_name}.gpkg", layer="network")
    print(f"car trips through the ramp: about {car_trips:.0f} per day")

    ax = buildings.plot(color="tan", figsize=(8, 9))
    final.plot(ax=ax, column="use", legend=True, linewidth=2)
    pier["entrances"].plot(ax=ax, color="black", markersize=15)
    ax.plot(*best["ramp"], marker="*", color="red", markersize=20)  # garage ramp
    ax.set_title(f"Scenario {SCENARIO}, {run_name}: optimized network (star = garage ramp)")
    ax.set_axis_off()
    plt.savefig(f"{OUT}/network_{SCENARIO}_{run_name}.png", dpi=150, bbox_inches="tight")
    plt.close()
