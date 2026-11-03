Geospatial context layers (task 4.2)

This folder preserves the supplied context datasets. Browser-ready derivatives
are prepared separately in data/web/environment/. Do not move or rename the
source files without updating their preparation paths.

Aerial imagery
--------------
The application loads its background imagery through online imagery providers.
It is not stored in this folder. See app/frontend/src/scene/imagery.ts.

Elevation colours
-----------------
File: elevation/GCS_FP_DTM_Elevation_Colours.tif

The supplied PDOK/AHN-derived terrain-colour image was clipped to the research
context. It is an RGBA visualization, not a numerical height raster. No original
colour-to-height legend is included, so exact heights cannot be read from its
colours. The app drapes its prepared image over the separate numerical terrain.

Vegetation
----------
File: vegetation/GCS_FP_Trees_2.kmz

Source workflow: OSM tree points were selected using a QuickOSM natural=tree
query, exported to Rhino, and turned into illustrative crowns/trunks in
Grasshopper before KMZ export. This is not a complete inventory or a measurement
of tree sizes.

The original supplied visualization used a manual height adjustment. The current
web preparation instead reads the KMZ coordinate conventions and places tree
bases on the shared prepared numerical terrain. Do not apply an additional
manual 45 m offset to the prepared browser models.

Preparation
-----------
From the repository root, after preparing the shared terrain:

uv run --project scripts/web python scripts/web/prepare_environment.py

See scripts/web/README.md for environment setup, GDAL tools, transformation grids,
and dependency order. The exporter retains source dimensions, creates lightweight
tree tiles and top-down markers, and prepares elevation imagery for the app.
