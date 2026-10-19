# MerweLab

**Merwehaven Urban Design & Simulation**

A geospatial analysis and urban simulation project developed for **BK7954 Geo-Computation Studio**, TU Delft, academic year **2026/27, Q1**.

MerweLab investigates residential development alternatives on **Kortevaarpier**, the smaller western peninsula in Merwehaven, Rotterdam. The project combines urban design, spatial analysis and environmental modelling to evaluate how different building layouts affect environmental quality, accessibility and the surrounding urban fabric.

The planned Cesium application will integrate existing buildings, proposed designs, urban morphology indicators, wind and noise simulations, weather observations and predictions, socio-demographic data and accessibility results.

## Project status

The repository currently contains spatial inputs, surrounding-building geometry, CBS analysis and course-provided conversion utilities. The Cesium frontend, backend and remaining analysis workflows are planned.

## Design scenarios

| Identifier | Description |
| --- | --- |
| `baseline` | Existing buildings and infrastructure |
| `scenario_a` | Three larger building volumes with associated circulation routes |
| `scenario_b` | Smaller building volumes arranged around a central road |

The proposed building models and detailed infrastructure layouts are still being developed. Surrounding buildings provide a shared context for comparison.

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
