# pier_graph.py: turn the clean pieces into a graph, find the gates, measure the walk outside the pier

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
from shapely.geometry import Point

from config import DESTINATIONS, COST_PER_M


def build_pier(lines, pieces, entrances, share, osm, starts, green):
    # one dictionary with everything that evaluate() needs
    # pier graph, piece ends closer than 0.2 m become the same node
    node_list = []

    def node(xy):
        for n in node_list:
            if abs(n[0] - xy[0]) < 0.2 and abs(n[1] - xy[1]) < 0.2:
                return n
        node_list.append((round(xy[0], 1), round(xy[1], 1)))
        return node_list[-1]

    G = nx.Graph()
    for _, p in pieces.iterrows():
        a, b = node(p.geometry.coords[0]), node(p.geometry.coords[-1])
        G.add_edge(a, b, length=p.geometry.length, wind=p["wind"], seg_id=p["seg_id"], kind=p["kind"], geom=p.geometry)
    print("connected parts:", nx.number_connected_components(G))

    fixed = set(lines.loc[lines["kind"].isin(["quay", "exit"]), "seg_id"])
    optional = sorted(set(lines["seg_id"]) - fixed)  # the bridge is optional too
    bridge_ids = list(lines.loc[lines["kind"] == "bridge", "seg_id"])
    print(f"{len(G.edges)} edges | fixed: {sorted(fixed)} | optional ({len(optional)}): {optional}")

    # entrances: the graph node at the entrance point
    entrances = entrances.copy()
    nodes = gpd.GeoDataFrame({"node": list(G.nodes)}, geometry=[Point(n) for n in G.nodes], crs=28992)
    entrances["node"] = gpd.sjoin_nearest(entrances, nodes, how="left")["node"].values
    ent_of = entrances.groupby("building_id")["node"].apply(list).to_dict()

    # gates: where the exits and the bridge touch the existing city network
    quay = lines[lines["kind"] == "quay"].union_all()
    gates = []
    car_gates = []  # cars only use the exits, not the bridge
    for _, l in lines[lines["kind"].isin(["exit", "bridge"])].iterrows():
        ends = [l.geometry.coords[0], l.geometry.coords[-1]]
        outer = max(ends, key=lambda xy: Point(xy).distance(quay))  # the end far from the quay is the city side
        gates.append(node(outer))
        if l["kind"] == "exit":
            car_gates.append(node(outer))
    print("gates (exits and bridge to the city):", gates)
    print("wind on the bridge:", pieces.loc[pieces["kind"] == "bridge", "wind"].round(1).tolist())

    # walking distance from each gate to the nearest facility of each type
    outside = {}
    for t in DESTINATIONS:
        d = nx.multi_source_dijkstra_path_length(osm, starts[t], weight="length")
        for g in gates:
            n, gap = ox.distance.nearest_nodes(osm, g[0], g[1], return_dist=True)
            outside[(g, t)] = d.get(n, np.inf) + gap

    # per line: length on green space, and the kind (the cost is set in set_costs)
    green_length = {s: g.intersection(green).length for s, g in zip(lines["seg_id"], lines.geometry)}
    pier = {"G": G, "fixed": fixed, "optional": optional, "bridge_ids": bridge_ids,
            "entrances": entrances, "ent_of": ent_of, "ramps": list(entrances["node"]),
            "gates": gates, "car_gates": car_gates, "outside": outside, "share": share,
            "length_of": dict(zip(lines["seg_id"], lines.geometry.length)),
            "kind_of": dict(zip(lines["seg_id"], lines["kind"])), "green_length": green_length, "cache": {}}
    set_costs(pier, COST_PER_M)
    return pier


def set_costs(pier, cost_per_m):
    # building cost of every line = length x cost per metre of its kind (also used by sensitivity.py)
    pier["cost_of"] = {s: pier["length_of"][s] * cost_per_m[pier["kind_of"][s]] for s in pier["length_of"]}
    pier["cache"] = {}  # results from before do not count any more
