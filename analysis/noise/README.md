# Road-traffic noise simulations

NoiseModelling 6.0.0 evaluates the existing baseline and proposed V1/V2 layouts
at 1.5 m above ground. Coordinates use EPSG:28992 (RD New). These calculations
cover road traffic only; they do not include shipping, industry or aircraft.

## Status and files

| Scenario | Saved workflow | Current outputs |
| --- | --- | --- |
| `baseline` | `baseline/workflow.json` | Inputs prepared; the study-area run and results will follow in a separate PR |
| `scenario_a` (V1) | `scenario_a/workflow.json` | Final contours and four study-area PNGs |
| `scenario_b` (V2) | `scenario_b/workflow.json` | Final contours, precise receiver levels and four study-area PNGs |

The earlier baseline pilot covered a smaller area. It is not the final baseline
comparison, and its experimental workflow and outputs are not included here.

For each scenario, `data/processed/noise/{scenario}/` contains:

| File | Role |
| --- | --- |
| `buildings.geojson` | Building footprints and acoustic height attributes; import as `BUILDINGS` |
| `ground.geojson.gz` | Prepared ground-absorption polygons; import as `GROUND` |
| `terrain.geojson.gz` | Raster cell centres and elevations as 3D points; import as `DEM` |
| `ground.gpkg` | Preserved ground preparation source; also used for water context in plots |
| `terrain.tif` | Preserved terrain preparation source |

Compressed GeoJSON files are read directly by the saved import blocks. Oversized
ground records are partitioned without simplifying their geometry, with material
attributes retained and `SOURCE_PK` linking pieces to the source record.

Shared files are `data/processed/noise/assessment_area.geojson`,
`config/noise/study_area.json` and `data/processed/noise/ground_classification.json`.
The last file records ground-absorption assumptions.

## Required common road input

All three workflows and the visualization script use the following committed
prepared road file:

```text
data/processed/noise/roads/roads.geojson
```

This is the prepared common road input derived from DCMR RVMK 2025, reference
situation 2024. It contains the road geometry and mapped traffic, speed and
pavement attributes used for all scenarios. No separate raw RVMK download is
needed for a simulation rerun. If comparing transferred copies, check the
prepared file's SHA-256 checksum:

```bash
sha256sum data/processed/noise/roads/roads.geojson
```

Source information: <https://www.dcmr.nl/verkeersgegevens-rvmk>.
The original preparation archive is `data/raw/noise/rvmk/RVMK2025j2024.zip`.
It is not needed to rerun from the prepared inputs, and downloading the raw
archive alone does not recreate our processed `roads.geojson`.

Redistribution terms for this specific RVMK release have not been verified in
this project. Source attribution is provided above; no open-data licence is
asserted here. The prepared file, together with the tracked scenario inputs,
is sufficient spatial input for rerunning the saved workflows. Keep the raw
archive separately for provenance and rebuilding the input.

## Rerun a scenario in NoiseModelling

1. Install NoiseModelling 6.0.0 and its Java runtime requirements. Retrieve the
   actual large ground files through Git LFS rather than leaving pointer files:

   ```bash
   git lfs install
   git lfs pull
   ```

2. Check that the prepared road file above and the scenario imports are present.
   All spatial input paths referenced by the three saved workflows are tracked
   in the repository; no external raw datasets are required for a rerun.
3. Start the NoiseModelling server with the **repository root as the Java
   process working directory**. Relative paths resolve on the server, not from
   the browser's download folder. Opening the workflow does not change that
   working directory.
4. Open `analysis/noise/{scenario}/workflow.json` in Builder. Create the export
   directory from the repository root, replacing the scenario as appropriate:

   ```bash
   mkdir -p outputs/data/noise/baseline
   ```

5. Run the following blocks in order. Import with SRID `28992`; when replacing
   an earlier scenario's tables, use the import block's `Overwrite` operation.

   | Block | Inputs / resulting table |
   | --- | --- |
   | `Import and Export / Import File` | Scenario buildings, ground and terrain; common roads and assessment boundary → `BUILDINGS`, `GROUND`, `DEM`, `ROADS`, `ASSESSMENT_AREA` |
   | `NoiseModelling / Road Emission from Traffic` | `ROADS`, coefficient version 2 → `LW_ROADS` |
   | `Receivers / Delaunay Grid` | `BUILDINGS`, `ROADS`, fence table `ASSESSMENT_AREA` → `RECEIVERS` and `TRIANGLES` |
   | `NoiseModelling / Noise level from source` | `LW_ROADS`, `BUILDINGS`, `GROUND`, `DEM`, `RECEIVERS` → `RECEIVERS_LEVEL` |
   | `Import and Export / Export Table` | Export `RECEIVERS_LEVEL` to the scenario's `receiver_levels.geojson` |
   | `Acoustic Tools / Create Isosurface` | `RECEIVERS_LEVEL`, field `LAEQ`; uses the matching native `TRIANGLES` table → `CONTOURING_NOISE_MAP` |
   | `Import and Export / Export Table` | Export `CONTOURING_NOISE_MAP` to the scenario's `noise_map.geojson` |

6. Verify both export paths contain the intended scenario **before** running
   the exports. Tables are reused across scenarios in the user's database;
   export the current run before importing or calculating the next scenario.

No custom receiver/triangle files are required. Generate both tables with
NoiseModelling's Delaunay Grid. Graph connections can rerun upstream blocks;
use the completed database table names for staged execution if the Builder
stalls while resolving a connected graph.

## Calculation settings

The common receiver boundary is `[87350, 435300, 89120, 436860]`, stored as
`detailed_bounds` in the current configuration (the visualization calls this
view `study_area`). Receiver height is 1.5 m; maximum triangle area is 2500 m²;
building buffer and road-width exclusion are 2 m. Triangle area does not imply
uniform receiver spacing. Triangle geometries are exported internally.

Saved propagation settings include maximum source distance 800 m, reflection
order 1, reflection distance 50 m, maximum error 0.1 dB, temperature 15 °C,
relative humidity 70% and wall absorption 0.1. The workflows retain their saved
thread counts (baseline 6, V1 8, V2 12); this is a machine-resource setting.
Terrain extends 900 m beyond the receiver boundary. The larger source-data
collection margin is distinct from the 800 m propagation distance.

Periods are day 07–19, evening 19–23 and night 23–07. `DEN` is Lden, including
5 dB evening and 10 dB night penalties. Isosurfaces use `LAEQ`, breaks
`35,40,45,50,55,60,65,70,75,80,200`, smoothing 0 and `keepTriangles=false`.
The workflows are the authoritative record of the full settings.

## Results and visualization

Final exports are under `outputs/data/noise/{scenario}/`. Both V1 and V2 have
`noise_map.geojson`; only V2 currently has a valid `receiver_levels.geojson`.
V1's receiver export was overwritten during the later V2 export. Its final
contours remain valid for band-based maps, thresholds and class rasters, but
cannot reconstruct precise V1 receiver levels or exact V1–V2 dB differences.

The visualization script needs Python, GeoPandas, NumPy, Matplotlib, a
GeoPackage-capable reader such as pyogrio, and Shapely with
`constrained_delaunay_triangles` support (Shapely 2.1+ with GEOS 3.10+).
It uses contour exports, prepared buildings/ground and the common road file;
it does not require receiver-level exports or a NoiseModelling database.

From the repository root:

```bash
python scripts/noise/visualize_noise.py scenario_a --view study_area
python scripts/noise/visualize_noise.py scenario_b --view study_area
```

Each command produces four PNGs in
`outputs/figures/noise/{scenario}/study_area/`: `noise_bands.png`,
`day_night.png`, `thresholds.png` and `noise_3d.png`. Those eight final V1/V2
PNGs are committed. No HTML or PDF files are generated. The default view is
`study_area`; thresholds and the 3D view default to `DEN` and can use
`--period D`, `E` or `N`. Thresholds are 45, 55, 65 and 75 dB; edit the settings
at the top of the script to change them at existing contour-band boundaries.

The 3D preview shows pedestrian noise bands above flat ground with relative
building heights and vertical scale 1. It is not terrain-following or a façade
noise calculation. Uncoloured areas may lack contour coverage, including
building setbacks. Threshold maps are not legal compliance assessments.
