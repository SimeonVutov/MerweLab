# MerweLab

**Merwehaven Urban Design & Simulation**

A geospatial analysis and urban simulation project developed for **BK7954 Geo-Computation Studio**, TU Delft, academic year **2026/27, Q1**.

MerweLab investigates residential development alternatives on **Kortevaarpier**, the smaller western peninsula in Merwehaven, Rotterdam. The project combines urban design, spatial analysis and environmental modelling to evaluate how different building layouts affect environmental quality, accessibility and the surrounding urban fabric.

The planned Cesium application will integrate existing buildings, proposed designs, urban morphology indicators, wind and noise simulations, weather observations and predictions, socio-demographic data and accessibility results.

## Project status

The repository contains spatial inputs, building geometry and analysis/simulation workflows. Road-traffic noise runs are complete for V1 and V2, with exported results and study-area PNG figures. Baseline noise inputs and a matching workflow are prepared; its simulation results will follow separately. See the [noise workflow README](analysis/noise/README.md) for setup, required data and current limitations.

## Design scenarios

| Identifier | Description |
| --- | --- |
| `baseline` | Existing buildings and infrastructure |
| `scenario_a` | V1: three proposed building volumes |
| `scenario_b` | V2: six proposed building volumes with a central gap |

Scenario-specific building and ground inputs are prepared for the noise simulations. Surrounding buildings provide a shared context for comparison.

Scenario identifiers are used consistently across input data, simulation configurations and results.

## Repository structure

| Path | Purpose |
| --- | --- |
| `app/frontend/` | Planned Cesium application and dashboard interface |
| `app/backend/` | Planned data API and backend services |
| `analysis/` | Analysis scripts and simulation configurations, organised by topic |
| `config/` | Shared scenario definitions and Cesium asset references |
| `data/boundaries/` | Development-site, research-area and wider context boundaries |
| `data/context/` | Surrounding-building geometry, footprints and placement metadata |
| `data/scenarios/` | Inputs specific to `baseline`, `scenario_a` and `scenario_b` |
| `data/cbs/` | CBS analysis inputs, tables, charts and GeoJSON exports |
| `data/web/` | Prepared spatial layers for application integration |
| `data/processed/noise/` | Prepared baseline/V1/V2 noise inputs and shared calculation boundary |
| `outputs/data/noise/` | Exported scenario noise contours and available receiver levels |
| `gis/` | Working QGIS projects |
| `outputs/figures/` | Selected analysis figures |
| `outputs/summaries/` | Result tables and scenario-comparison summaries |
| `scripts/` | Shared preparation and export utilities |
| `tools/3dbag_to_gml/` | Course-provided 3DBAG conversion tool |

## Available workflows

### CBS socio-demographic analysis

The CBS analysis script generates demographic summary tables, charts and GeoJSON exports.

**Requirements:** Python, GeoPandas, pandas and Matplotlib.

Run from the repository root:

```bash
(cd data/cbs && python ../../analysis/cbs/cbs_analysis.py)
```

Results are written to `data/cbs/cbs_output/`.

### Road-traffic noise simulation

Saved NoiseModelling 6.0.0 workflows are in `analysis/noise/{scenario}/workflow.json`. V1 and V2 outputs include day, evening, night and Lden contours. The baseline setup is ready for a future run.

Retrieve large ground files with `git lfs pull`. The common prepared road file, `data/processed/noise/roads/roads.geojson`, is committed alongside the scenario inputs. No raw RVMK download is needed to rerun the saved workflows.

The [noise workflow README](analysis/noise/README.md) describes imports, block order, required files, calculation settings and PNG visualization commands.

### 3DBAG conversion

The course-provided conversion tool prepares 3DBAG CityJSON tiles for import into Cesium ion.

Installation requirements and usage instructions are available in the [3DBAG conversion README](tools/3dbag_to_gml/README.md).

### QGIS project

The imported project is located at `gis/merwehaven.qgz`.

Before using it, repair the layer paths to reference the corresponding files under `data/`. Save subsequent work with relative paths so the project remains portable between team members.

## Working with spatial data

- Preserve the coordinate system, units and height reference when preparing or exporting datasets.
- Keep `data/context/Context_Placement.json` alongside the context geometry. It records the transformation and placement information for the local East–North–Up model.
- Treat the development site, surrounding-building selection and wider accessibility context as separate spatial extents. The context-selection buffer does not define the complete CFD domain.
- Keep scenario-specific geometry separate from the surrounding context so that designs can be compared using consistent inputs.

