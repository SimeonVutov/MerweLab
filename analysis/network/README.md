# Road network optimization (task 4.8)

Which paths should be built on Kortevaarpier, and where should the ramp of the underground garage go?
The candidate paths are drawn by hand (`data/network/design/network_design.gpkg`). The scripts choose which of them to build, for `scenario_a` and `scenario_b`.

## How it works

- **Fixed:** the quay ring and the two exits to the city. **Optional:** all other candidates, including a bridge (A15 / B21) from the south-west tip to the west quay.
- **Gates:** the city ends of the exits (and of the bridge, walking only). Cars use the exits only, and only from an exit to the ramp. Residents never walk in through the ramp.
- **Indicators** (each scaled 0-1 with 2000 random networks, lower is better):

| Indicator | Meaning |
| --- | --- |
| `access` | walking distance (m) from the buildings to 8 kinds of destinations, weighted by dwellings |
| `detour` | walking distance on the pier / straight distance to the gate |
| `car` | length of the car route from the nearest exit to the ramp (m) |
| `wind` | mean wind speed along the walking routes (relative values, one wind direction, 240 degrees) |
| `green_loss` | length of built paths that lie on green space (m) |
| `cost` | building cost, length x cost per metre of each kind of path (relative; the bridge counts 8 times a normal path) |

- **Search:** greedy removal (start with everything built, remove the path that improves the total most). For scenario A every combination is also tried, and gives the same result.
- **Weight sets** (in `config.py`): `balanced`, `access_first`, `green_first`, `no_wind`.

## Run

Run from the repository root. Install: geopandas, networkx, osmnx, rasterio, matplotlib, pyogrio.

```
python analysis/network/baseline_network_analysis.py              # once: downloads OSM network and facilities
python analysis/network/optimization/main.py A                    # best network, all weight sets (use B for scenario B)
python analysis/network/optimization/sensitivity.py A             # bridge cost and cost weight
python analysis/network/optimization/export_web.py A balanced     # GeoJSON for the Cesium website
```

Settings (scenario, bridge on/off, weights, cost per metre, paths) are all in `analysis/network/optimization/config.py`.

## Files

| Path | Content |
| --- | --- |
| `analysis/network/optimization/` | `config`, `data_loading`, `geometry` (snap and cut lines), `pier_graph`, `evaluation`, `search`, `plotting`, `main`, `sensitivity`, `export_web` |
| `data/network/design/` | hand-drawn candidates and entrances, building layout of each scenario |
| `data/network/baseline/` | accessibility of the current situation |
| `data/network/output/` | results of `main.py` and `sensitivity.py` (csv, gpkg, png) |
| `data/network/for_cesium/` | GeoJSON (lon/lat) and a summary json per scenario, for the website |
| `data/network/osm/`, `data/network/facilities/` | OSM downloads, not in git, recreated by the baseline script |
| `outputs/data/wind/study_area/grid_1m/` | wind rasters used for the `wind` indicator |

## Results (balanced weights)

- **Scenario A:** build A03 A04 A06 A08 A12, ramp at (88189.1, 436464.9). access 1001 m, wind 5.63, car 81 m, green loss 215 m.
- **Scenario B:** build B11-B16 and B20, ramp at (88148.6, 436459.5). Only the greedy search is used (too many combinations to try all).
- **The bridge is not built** in scenario A for any of the weight sets, nor for any bridge cost between 0 and 32 times a normal path (tested for A), and not in scenario B with balanced weights. From the bridge end every destination is further away than from the northern exits (tram stop: 689 m, against 245 m and 93 m), so the bridge does not improve access.

## Limits

- Candidates are drawn by hand, so the result depends on what we drew.
- Weights and building costs are assumptions (no real prices). Cost values cannot be compared between scenarios, because every scenario is scaled on its own.
- Wind is one direction and relative values only.
- Most of the walking distance is outside the pier, so the paths on the pier change `access` by only a few percent.
