# MerweLab geometry tools v1

This folder contains the active RD geometry catalogue. File names are simple;
source qualifications and checksums are in config/merwelab_coordinates.json.
Every OBJ has a same-stem MTL beside it. Keep the pair together.

## Load shared geometry plus ONE scenario

| Location | Geometry |
|---|---|
| data/scenarios/ | yellow_buildings_lod12, red_buildings_lod12, context_ground, context_quays, water_surface |
| data/scenarios/baseline/ | buildings_existing, ground_existing, quays_existing |
| data/scenarios/scenario_a/ | buildings_v1, pavement_v1, green_areas_v1 |
| data/scenarios/scenario_b/ | buildings_v2, pavement_v2, green_areas_v2 |

If present, additional_buildings_lod22_review.obj is the partial downloaded
building set. It is included by the Blender importer for inspection, and its
manifest entry is review_only. It is not a completed replacement set or an
approved simulation input. Do not use a wildcard of every OBJ as CFD input.
The previous approximate purple objects are archived outside this folder.
PDOK source ZIPs have not been converted or merged by this organizer.

## Coordinates

All OBJ files here use metres, absolute RD XY (EPSG:28992), Z up. AHN/3DBAG
heights use NAP where documented; the supplied design datum remains assumed.
Water is a constant Z=0 surface, not an observed tide. Derived ground/quay
surfaces are not surveyed CAD. File reorganization changes no coordinates,
faces, object/group identifiers or material assignments.

For Blender, open a fresh file, use the Text Editor to open
scripts/wind/import_geometry_blender.py and click Run Script. It reads this
catalogue and subtracts the SAME origin from every mesh before Blender stores
the vertices. This preserves RD alignment while avoiding large scene numbers.
Choose the MerweLab_BASELINE, MerweLab_V1 or MerweLab_V2 scene, then press Home
in the 3D Viewport to frame it. Do not translate, rotate or rescale individual
objects. Reimport from a fresh file if scenes already exist.

Blender local coordinates = RD coordinates - RD_origin. Recover RD by adding
the origin back. This is a translated RD frame, not a true ENU reprojection.
scripts/wind/check_geometry_blender.py checks every registered mesh vertex in
the current scene against its canonical RD source (tolerance 1 mm). This is a
placement check, not a claim about source data survey accuracy or current age.

## Materials and source review

An MTL stores display materials such as colour and transparency, referenced by
the OBJ mtllib line. It is not needed to define vertex/face geometry and does
not configure OpenFOAM aerodynamic roughness or wall functions. These small
MTL files are retained for general OBJ/Blender viewers; the supplied Blender
importer uses the catalogue colours directly.

Terrain sheets, assumed vertical references, building overlaps, current
existence and missing buildings still need review before final CFD meshing or
Cesium publication. Reorganization does not solve those source issues.

## Temporary and superseded files

Downloads/temp/merwelab_organization/<run>/ contains the moved old export
folders, previous local/prepared/proxy geometry, refinement drafts, download
sources, old temporary setup and configuration backups. organization_log.json
records moves. No permanent deletion is performed. Archived scripts, symlinks
and the archived virtual environment retain old paths and are historical only.
Keep the source downloads until the missing-building review is complete.

Permanent tools: scripts/wind/. Permanent coordinate catalogue: config/.
Geometry-review evidence: analysis/wind/geometry_review/inventory/.
Unrelated GIS, data/raw/team, project PDFs and analysis files remain in place.
Other application/GIS configurations are not automatically rewritten; point
their OBJ references at the new paths before using them.
