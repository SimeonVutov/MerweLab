# Task 4.8 step 1: accessibility of the current situation
# walking distance from the pier (and from each buurt) to everyday facilities, using OSM data

import os
import time
import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
import pandas as pd

# settings
CONTEXT = "data/boundaries/context_area.gpkg"
SITE = "data/boundaries/GCS_FP_Development_Site.gpkg"
BUURTEN = "data/cbs/cbs_output/buurten.geojson"
OUT = "data/network/baseline"          # results (csv, png)
OSM = "data/network/osm"               # osm downloads, recreated by the script (not in git)
FAC = "data/network/facilities"        # one file per facility type, recreated by the script (not in git)
for folder in [OUT, OSM, FAC]:
    os.makedirs(folder, exist_ok=True)

WALK_SPEED = 80  # metres per minute, about 4.8 km/h
STEP = 10        # metres between sample points on the pier

# osm server settings
ox.settings.requests_timeout = 600  # wait up to 10 minutes for the server
# ox.settings.overpass_url = "https://overpass.kumi.systems/api"  # mirror, if the main server keeps failing
# ox.settings.overpass_rate_limit = False                        # needed when using the mirror

# osm tags of each facility, and the matching cbs column (None = no cbs value)
FACILITIES = {
    "supermarket":   ({"shop": "supermarket"}, "groteSupermarktGemiddeldeAfstandInKm"),
    "gp":            ({"amenity": "doctors", "healthcare": "doctor"}, "huisartsenpraktijkGemiddeldeAfstandInKm"),
    "pharmacy":      ({"amenity": "pharmacy"}, "apotheekGemiddeldeAfstandInKm"),
    "day_care":      ({"amenity": ["kindergarten", "childcare"]}, "kinderdagverblijfGemiddeldeAfstandInKm"),
    "school":        ({"amenity": "school"}, "basisonderwijsGemiddeldeAfstandInKm"),
    "park":          ({"leisure": "park"}, None),
    "tram_bus_stop": ({"highway": "bus_stop", "railway": "tram_stop"}, None),
    "metro":         ({"station": "subway"}, None),
    "train_station": ({"railway": "station"}, "treinstationGemiddeldeAfstandInKm"),
}

# load boundaries, all in RD (EPSG:28992)
context = gpd.read_file(CONTEXT).to_crs(28992)
site = gpd.read_file(SITE).to_crs(28992)
buurten = gpd.read_file(BUURTEN).to_crs(28992)

# osm needs lat/lon, 500 m extra so routes at the edge are not cut off
area = context.buffer(500).to_crs(4326).union_all()

# download osm data, only the first time (saved files are used after that)
if not os.path.exists(f"{OSM}/osm_walk.graphml"):
    print("downloading walking network...")
    G = ox.graph_from_polygon(area, network_type="walk")
    G = ox.project_graph(G, to_crs=28992)
    ox.save_graphml(G, f"{OSM}/osm_walk.graphml")

# the osm server is often busy, so wait and try again (up to 5 times)
def download(tags):
    for wait in [0, 1, 2, 4, 8]:  # minutes
        if wait > 0:
            print(f"  server busy, trying again in {wait} min...")
            time.sleep(wait * 60)
        try:
            return ox.features_from_polygon(area, tags)
        except Exception as e:
            print("  failed:", str(e)[:80])
    raise RuntimeError("osm server is still busy, run the script again later")


# facilities: every type gets its own file, so a failed download does not lose the types already done
os.makedirs(FAC, exist_ok=True)
for name, (tags, cbs_col) in FACILITIES.items():
    file = f"{FAC}/{name}.gpkg"
    if os.path.exists(file):
        continue
    print(f"downloading {name}...")
    f = download(tags).to_crs(28992)
    if name == "train_station" and "station" in f.columns:
        f = f[f["station"] != "subway"]  # metro stations are also railway=station, remove them
    points = f.geometry.representative_point()
    gpd.GeoDataFrame({"type": name, "geometry": points.values}, crs=28992).to_file(file)

if not os.path.exists(f"{OSM}/osm_homes.gpkg"):
    print("downloading residential buildings...")
    b = download({"building": ["apartments", "residential", "house", "terrace"]})
    b = b[b.geometry.type.isin(["Polygon", "MultiPolygon"])].to_crs(28992)
    gpd.GeoDataFrame(geometry=b.geometry.centroid, crs=28992).to_file(f"{OSM}/osm_homes.gpkg")

G = ox.load_graphml(f"{OSM}/osm_walk.graphml")
G = ox.convert.to_undirected(G)  # walking works in both directions
facilities = pd.concat([gpd.read_file(f"{FAC}/{name}.gpkg") for name in FACILITIES])
homes = gpd.read_file(f"{OSM}/osm_homes.gpkg")
print(f"network: {len(G.nodes)} nodes | {len(facilities)} facilities | {len(homes)} homes")


# distance from every network node to the nearest facility of one type
def distance_to_nearest(points):
    start_nodes = set(ox.distance.nearest_nodes(G, points.geometry.x, points.geometry.y))
    return nx.multi_source_dijkstra_path_length(G, start_nodes, weight="length")


# distance for any set of points: straight to the nearest node, then along the network
def distance_of(points, dist_by_node):
    nodes, gaps = ox.distance.nearest_nodes(G, points.geometry.x, points.geometry.y, return_dist=True)
    return [dist_by_node.get(n, float("nan")) + gap for n, gap in zip(nodes, gaps)]


dist = {}
for name in FACILITIES:
    found = facilities[facilities["type"] == name]
    if len(found) > 0:
        dist[name] = distance_to_nearest(found)
    else:
        print(f"no {name} found in osm, skipped")

# pier: a point every STEP metres
xmin, ymin, xmax, ymax = site.total_bounds
xs, ys = [], []
for x in range(int(xmin), int(xmax), STEP):
    for y in range(int(ymin), int(ymax), STEP):
        xs.append(x)
        ys.append(y)
pier = gpd.GeoDataFrame(geometry=gpd.points_from_xy(xs, ys), crs=28992)
pier = pier[pier.within(site.union_all())].copy()  # only keep points on the pier

# there are no paths on the pier in osm yet, people first walk to the road at the north end of the pier.
# so pier points may only connect to nodes close to the pier, otherwise they "walk over the water" to the next quay
nodes = ox.graph_to_gdfs(G, edges=False)
gates = nodes[nodes.distance(site.union_all()) < 50].reset_index()  # node id becomes a column "osmid"
pier = gpd.sjoin_nearest(pier, gates[["osmid", "geometry"]], distance_col="gap")
pier = pier.rename(columns={"osmid": "node"})
print(f"pier connects to the city through {len(gates)} nodes")

for name in dist:
    pier[name] = [dist[name].get(n, float("nan")) + gap for n, gap in zip(pier["node"], pier["gap"])]

result = pd.DataFrame({"mean_m": pier[list(dist)].mean(), "max_m": pier[list(dist)].max()}).round(0)
result.index.name = "facility"
result["mean_walk_min"] = (result["mean_m"] / WALK_SPEED).round(1)
result.to_csv(f"{OUT}/pier_accessibility.csv")
print(result)

# check the model: our distance vs cbs distance, per buurt
homes = gpd.sjoin(homes, buurten[["buurtcode", "geometry"]], predicate="within")
rows = []
for name, (tags, cbs_col) in FACILITIES.items():
    if cbs_col is None or name not in dist:
        continue
    homes[name] = distance_of(homes, dist[name])
    ours = homes.groupby("buurtcode")[name].mean() / 1000  # m -> km
    cbs = buurten.set_index("buurtcode")[cbs_col]
    rows.append(pd.DataFrame({"facility": name, "ours_km": ours.round(2), "cbs_km": cbs}).dropna())
check = pd.concat(rows)
check.to_csv(f"{OUT}/check_vs_cbs.csv")

plt.figure(figsize=(5, 5))
for name, d in check.groupby("facility"):
    plt.scatter(d["cbs_km"], d["ours_km"], label=name, s=20)
plt.plot([0, 3], [0, 3], "k--", linewidth=0.8)  # if our model = cbs, points are on this line
plt.xlabel("CBS distance (km, by road)")
plt.ylabel("Our distance (km, walking)")
plt.title("Our model vs CBS, per buurt")
plt.legend(fontsize=7)
plt.savefig(f"{OUT}/check_vs_cbs.png", dpi=150, bbox_inches="tight")
plt.close()

# maps: walking time to the nearest supermarket and metro
nodes, edges = ox.graph_to_gdfs(G)
for name in ["supermarket", "metro"]:
    if name not in dist:
        continue
    start_nodes = edges.index.get_level_values("u")
    edges["minutes"] = [dist[name].get(n, float("nan")) / WALK_SPEED for n in start_nodes]
    ax = edges.plot(column="minutes", cmap="RdYlGn_r", vmin=0, vmax=20, linewidth=0.7, figsize=(9, 8),
                    legend=True, legend_kwds={"label": "walking minutes", "shrink": 0.6})
    facilities[facilities["type"] == name].plot(ax=ax, color="black", marker="*", markersize=25)
    site.boundary.plot(ax=ax, color="blue", linewidth=2)
    context.boundary.plot(ax=ax, color="grey", linestyle="--")
    ax.set_title(f"Walking time to the nearest {name} (pier in blue)")
    ax.set_axis_off()
    plt.savefig(f"{OUT}/walk_time_{name}.png", dpi=150, bbox_inches="tight")
    plt.close()

# save the network for qgis, used as base map in step 2
ox.save_graph_geopackage(G, f"{OSM}/osm_walk_network.gpkg")
print("done, results saved in", OUT)
