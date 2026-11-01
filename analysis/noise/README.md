# Noise simulation inputs and final results

V1 is `scenario_a`; V2 is `scenario_b`. The saved `workflow.json` in each
scenario folder uses NoiseModelling 6.0.0 native Delaunay receiver generation.
The workflow files preserve scenario-specific propagation settings.

Run NoiseModelling with the MerweLab repository root as its working directory
so that the saved relative paths resolve. Import the prepared buildings,
ground, terrain, roads and assessment boundary; compute road emissions; run
Delaunay Grid; calculate receiver levels; create isosurfaces; export results.
Do not import the abandoned custom receiver or triangle GeoJSON files.

The calculation area is `data/processed/noise/assessment_area.geojson`, matching
`detailed_bounds` in `config/noise/study_area.json`. Coordinates use EPSG:28992.
Native receiver height is 1.5 m above ground, maximum triangle area is 2500 m²,
and building and road setbacks are 2 m. Input collection and terrain margins
are larger than the receiver area to retain surrounding source contributions.

## Prepared data

`data/processed/noise/{scenario}/buildings.geojson`, `ground.geojson.gz` and
`terrain.geojson.gz` are the V1/V2 import files. The GeoPackages, terrain TIFFs,
common ground classification and original baseline geometry are preserved as
preparation sources and for project reuse. Large ground files use Git LFS.
The baseline pilot workflow and outputs were experiments, not a final baseline
run across the detailed study area, and are not included as final results.

The required road input is `data/processed/noise/roads/roads.geojson`.
It is derived from DCMR RVMK 2025, reference situation 2024:
https://www.dcmr.nl/verkeersgegevens-rvmk
The original local archive is `data/raw/noise/rvmk/RVMK2025j2024.zip`.
The road input and raw source are kept locally; redistribution terms have not
been established in this project, so they are not included in these commits.
Colleagues need an appropriately shared copy of the prepared road input to rerun.

## Final exports

- `outputs/data/noise/scenario_a/noise_map.geojson`: final native V1 contours.
- `outputs/data/noise/scenario_b/noise_map.geojson`: final native V2 contours.
- `outputs/data/noise/scenario_b/receiver_levels.geojson`: precise V2 receiver results.

The V1 receiver-level export was overwritten with V2 data. The correct V2 export
is retained unchanged, and its wrongly labelled duplicate is removed from V1. Precise V1 receiver
values are therefore unavailable in this export set. Do not substitute the old
pilot/custom-mesh results. V1 contours remain usable for band-based maps,
threshold layers and band-class rasters, not recovery of exact receiver levels.

Contours retain D, E, N and DEN periods. Period interpretation is day 07–19,
evening 19–23 and night 23–07. Isosurface breaks are
35,40,45,50,55,60,65,70,75,80,200 dB, with exported open-ended labels such as 80+.
Maps represent modelled road-traffic noise, not all environmental noise sources.
Contour comparisons are band-based; they do not provide exact dB differences.

Final V1/V2 PNG/PDF figures remain local. Experimental figures, temporary scripts,
custom meshes and pilot-only files have been removed. NoiseModelling database
files and native tables are outside this repository cleanup and are unchanged.
