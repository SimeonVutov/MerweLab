# data_loading.py: read the design, the wind map and the city network

import geopandas as gpd
import numpy as np
import osmnx as ox
import rasterio

from config import (DESIGN, LAYOUT, WIND, OSM_GRAPH, FACILITY_DIR, SCENARIO, BRIDGE,
                    DESTINATIONS, FLOOR_HEIGHT, DWELLING_SIZE)


def load_design():
    # candidate lines, entrances and buildings (with dwellings and the share of each building)
    lines = gpd.read_file(DESIGN, layer=f"candidates_{SCENARIO}")
    if not BRIDGE:
        lines = lines[lines["kind"] != "bridge"].reset_index(drop=True)
    entrances = gpd.read_file(DESIGN, layer=f"entrances_{SCENARIO}")
    buildings = gpd.read_file(LAYOUT, layer="buildings")
    buildings["dwellings"] = (buildings.area * (buildings["height_m"] // FLOOR_HEIGHT - 1) / DWELLING_SIZE).round()
    share = (buildings.set_index("building_id")["dwellings"] / buildings["dwellings"].sum()).to_dict()
    print("dwellings:", buildings.set_index("building_id")["dwellings"].to_dict())
    green = gpd.read_file(LAYOUT, layer="green").union_all()  # green space of the layout, one geometry
    return lines, entrances, buildings, share, green


def load_wind():
    with rasterio.open(WIND) as src:
        wind_map = src.read(1).astype(float)
        wind_map[wind_map == src.nodata] = np.nan
        return wind_map, src.transform


def load_city():
    # walking network of the city, and for every facility type the network nodes where the facilities are
    osm = ox.load_graphml(OSM_GRAPH)
    osm = ox.convert.to_undirected(osm)
    starts = {}
    for t in DESTINATIONS:
        f = gpd.read_file(f"{FACILITY_DIR}/{t}.gpkg")
        starts[t] = set(ox.distance.nearest_nodes(osm, f.geometry.x, f.geometry.y))
    return osm, starts
