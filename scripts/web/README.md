# Prepare data for the web application

These scripts convert existing project datasets and analysis results into files that Cesium can load. They do **not** run wind/noise simulations, train models, or calculate new design proposals.

**You normally do not need to run them to start the app.** Use the committed files in `data/web/`. Run preparation when the source data changes, a prepared asset is missing, or an exporter has been updated.

## First-time setup

Run these commands from the **repository root**, not from `app/frontend`:

```bash
git lfs install
git lfs pull
uv sync --project scripts/web
uv run --project scripts/web python scripts/web/download_grids.py
```

You need:

- Python 3.12 or newer and `uv`.
- GDAL command-line tools for raster/vector conversion: `gdalinfo`, `gdal_translate`, `gdalwarp`, `gdal_rasterize`, and `ogr2ogr`.
- Blender only when generating building or site-surface GLB models.

`uv sync` installs the preparation environment's NumPy and pyproj dependencies. It does not install GDAL command-line tools or Blender. Install those separately and make them available on your terminal's `PATH`. On Windows, an OSGeo4W installation can supply GDAL; open a terminal where those commands are available. On Linux, use your distribution's GDAL packages.

Check the tools you need before running a conversion:

```bash
gdalinfo --version
ogr2ogr --version
blender --version
```

The grid downloader saves the coordinate-transformation grids in `.cache/web/proj/`. This first download requires internet access. Keep the grids locally: the conversion uses them to preserve the project's horizontal and vertical alignment.

## How to launch a script

Every preparation script uses the same command pattern:

```bash
uv run --project scripts/web python scripts/web/prepare_wind.py
```

Replace `prepare_wind.py` with the script you need. No virtual-environment activation is required. This command pattern works on Windows and Linux.

The examples use repository-root paths. Inside the scripts, source and output paths are resolved from the repository location rather than your shell's working directory. The scripts use fixed project inputs; they do not currently provide command-line input/output options.

## Which script should I run?

| Script | Run it when… | Main inputs | Prepared output |
|---|---|---|---|
| `prepare_buildings.py` | Building OBJ/MTL models or coordinate configuration change | `data/scenarios/`, `config/merwelab_coordinates.json` | `data/web/buildings/` |
| `prepare_surfaces.py` | Scenario pavement, green areas, quays, or water geometry change | Surface OBJ/MTL models in `data/scenarios/` | `data/web/surfaces/`, including the water mask |
| `prepare_water_mask.py` | Only the water footprint needs updating | `data/scenarios/water_surface.obj` | `data/web/surfaces/water-mask.geojson` |
| `prepare_cbs.py` | The supplied neighbourhood or summary export changes | `data/cbs/cbs_output/` | `data/web/cbs/data.json` |
| `prepare_terrain.py` | Baseline terrain, CBS context extent, or site boundary changes | Baseline processed terrain, CBS polygons, site boundary, building manifest | `data/web/terrain/` |
| `prepare_context.py` | Regional building footprints/heights or detailed-building coverage change | Baseline processed building GeoJSON, building and terrain manifests | `data/web/context/` |
| `prepare_building_outlines.py` | Building geometry or its context coverage changes | Building manifest, processed scenario buildings, terrain manifest | `data/web/building-outlines/` |
| `prepare_environment.py` | Supplied trees, elevation colours, or prepared terrain change | `data/context/`, prepared terrain | `data/web/environment/` |
| `prepare_morphology.py` | Exported indicator TIFFs, legends, or palettes change | `outputs/data/morphology/extended/`, `config/morphology_colours.json` | `data/web/morphology/` |
| `prepare_wind.py` | Exported wind results or display terrain change | `outputs/data/wind/app/`, prepared terrain | `data/web/wind/` |
| `prepare_noise.py` | Noise contours, trusted receiver exports, study bounds, or supporting terrain change | `outputs/data/noise/<scenario>/`, all three processed terrain rasters, prepared terrain | `data/web/noise/` and class TIFFs under `outputs/data/noise/app/` |
| `prepare_land_use.py` | Original, simplified, or optimized land-use rasters change | `data/land_use/` and its analysis configuration | `data/web/land-use/` |
| `prepare_network.py` | Saved network alternatives, accessibility results, or supporting surfaces change | `data/network/`, prepared terrain and surface data | `data/web/network/` |

A prepared manifest is an index of the files belonging to a layer. Keep it with the assets it references. Hashes in asset filenames identify their content; do not rename those files manually.

## Common examples

### Update wind maps

The source export must already exist for `baseline`, `scenario_a`, and `scenario_b`, including each scenario's `metadata.json`, rasters, arrows, and streamlines.

If the prepared terrain is current, run only:

```bash
uv run --project scripts/web python scripts/web/prepare_wind.py
```

If the baseline terrain changed, regenerate it first:

```bash
uv run --project scripts/web python scripts/web/prepare_terrain.py
uv run --project scripts/web python scripts/web/prepare_wind.py
```

### Update noise maps

Prepare the existing contour exports and trusted receiver data:

```bash
uv run --project scripts/web python scripts/web/prepare_noise.py
```

The script exports all four periods: D, E, N, and DEN. **V1 receiver levels are deliberately excluded** because their source export was overwritten. The script uses V1's contour maps without reading that receiver table.

This also generates classified RD GeoTIFFs under `outputs/data/noise/app/`. It does not rerun NoiseModelling.

### Update indicator maps

After exporting the morphology TIFFs and legends from the analysis workflow:

```bash
uv run --project scripts/web python scripts/web/prepare_morphology.py
```

This converts the supplied coloured maps. It does not recompute the indicators.

Current indicator TIFFs belong in
`outputs/data/morphology/extended/baseline/imagery/`, using the same filenames
as the corresponding V1/V2 exports. The preparation script reads the
`Existing/...` entries in `metadata/legends.json` and maps them to `baseline`.
The eleven Current indicators use the same class legends and fixed continuous
scales as V1/V2. Four additional Current TIFFs (continuous height, nDSM,
density, and H/W) are retained as source exports but are not listed for web
preparation because the app has no controls for them. The height and nDSM
exports use the notebook's maximum-roof height model despite the legacy
`mean_height` filename.

SVF change versus Existing is available for V1/V2 only; no Current-versus-itself
map is generated. The source TIFFs and the morphology notebook are not modified
by preparation.

### Update only water

```bash
uv run --project scripts/web python scripts/web/prepare_water_mask.py
```

This reads the water OBJ footprint directly and does not require Blender. For updated 3D surface models as well, use `prepare_surfaces.py` instead; it also regenerates the water mask.

## Rebuilding all web assets

Only do this if you actually need a full rebuild and have all the source datasets and analysis exports. Missing upstream simulation or analysis results must be prepared by their respective workflows first.

Start with the shared model and terrain dependencies:

```bash
uv run --project scripts/web python scripts/web/prepare_buildings.py
uv run --project scripts/web python scripts/web/prepare_surfaces.py
uv run --project scripts/web python scripts/web/prepare_cbs.py
uv run --project scripts/web python scripts/web/prepare_terrain.py
```

Then prepare the layers that consume those assets:

```bash
uv run --project scripts/web python scripts/web/prepare_context.py
uv run --project scripts/web python scripts/web/prepare_building_outlines.py
uv run --project scripts/web python scripts/web/prepare_environment.py
uv run --project scripts/web python scripts/web/prepare_morphology.py
uv run --project scripts/web python scripts/web/prepare_wind.py
uv run --project scripts/web python scripts/web/prepare_noise.py
uv run --project scripts/web python scripts/web/prepare_land_use.py
uv run --project scripts/web python scripts/web/prepare_network.py
```

Building and surface exports require Blender. Raster/vector exporters require the relevant GDAL tools. The standalone CBS exporter uses only Python's standard library.

If a shared input changes, rerun its dependants too. In particular, updating the coordinate origin or transformation grids affects the georeferenced exports across the project; updating terrain can affect wind/noise display meshes, building context coverage, outlines, vegetation placement, and network display heights.

## After a successful run

1. Check the terminal summary and any errors. Resolve a failed conversion before using its output.
2. Restart the frontend development server so it picks up newly generated assets, then reload the browser.
3. Inspect the affected layer in Explore and Compare, including its placement, legend, transparency, and selected-location values where available.
4. Review the generated files before committing them. Do not commit temporary files, local environments, or the downloaded grid cache.

The scripts write prepared outputs and may replace existing files and manifests. Content-addressed exporters can leave older assets behind. They do not automatically remove every unused asset; do not delete files still referenced by a manifest.

The existing building checks can be run with:

```bash
uv run --project scripts/web python -m unittest discover -s scripts/web -p 'test_*.py'
```

These checks inspect building conversion fidelity. They do not test every preparation script or replace a visual alignment check.

## Common problems

| Problem | What to check |
|---|---|
| `gdalwarp`, `ogr2ogr`, or `blender` cannot be found | Install the required tool and check that it is on the terminal's `PATH`. |
| A PROJ grid is missing | Run `download_grids.py` using the setup command above. |
| A source raster, model, or analysis export is missing | Run `git lfs pull` where applicable, then check that the required upstream result exists. Preparation does not generate missing simulations. |
| An asset request returns HTML or a 404 in the app | Check that preparation succeeded and restart the frontend server. |
| Terrain coverage or NoData validation fails | Check the source extent and missing-data mask. Do not replace missing samples with zero to bypass validation. |

The preparation scripts do not require the Flask weather backend or a KNMI API token.
