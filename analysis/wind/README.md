# Merwehaven wind simulations

This setup compares wind around the existing peninsula (`baseline`) and the two designs (`scenario_a` / V1 and `scenario_b` / V2). It uses OpenFOAM v2606 to identify exposed areas, shelter and changes in airflow, mainly at pedestrian height.

## Where the files are

Paths below are relative to the project root.

| Location                                                 | Purpose                                                                                                                                                             |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `data/scenarios/`                                        | Shared source models: yellow, red and additional context buildings, ground, quays and water, in Dutch RD coordinates. Some models already include geometry repairs. |
| `data/scenarios/baseline/`, `scenario_a/`, `scenario_b/` | Existing peninsula geometry and the two designs, including their buildings and ground surfaces.                                                                     |
| `data/scenarios/cfd_wind_240/`                           | Prepared context buildings, translated and rotated for the selected wind direction. `placement.json` records this transformation.                                   |
| `data/scenarios/<scenario>/cfd_wind_240/`                | Prepared peninsula buildings and the complete terrain for each scenario.                                                                                            |
| `analysis/wind/<scenario>/wind_240/`                     | The OpenFOAM case: configuration, copies of its input geometry and locally generated simulation data.                                                               |
| `scripts/wind/visualization/`                            | Scripts that read saved results and create figures.                                                                                                                 |
| `outputs/figures/wind/`                                  | Figures grouped by scenario and iteration. Current scripts save to `north_up_native/`; older baseline figures also exist outside that subfolder.                    |
| `config/merwelab_coordinates.json`                       | Source-model locations and coordinate metadata. Earlier geometry checks are in `analysis/wind/geometry_review/`.                                                    |

OpenFOAM reads geometry from each case. Context buildings are repeated, while peninsula buildings and terrain change between scenarios. Each peninsula model is renamed `peninsula_buildings.obj` so the configuration can use the same name.

**Editing a source model does not update the case automatically.** The prepared geometry and case copies must also be updated, followed by a new mesh.

## Inside each case

| File or folder                                         | What it does                                                                                                                                                                           |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `0.orig/`                                              | Templates for initial fields and boundary conditions. `U` is velocity, `p` is pressure, and `k`, `epsilon` and `nut` describe modelled turbulence. A fresh run uses a copy named `0/`. |
| `0.orig/include/`                                      | Shared definitions and mappings that give generated building and terrain surfaces the correct conditions.                                                                              |
| `constant/triSurface/`                                 | Input surfaces made from triangles. These describe geometry; they are not the volume mesh of the air.                                                                                  |
| `constant/transportProperties`, `turbulenceProperties` | Air properties and the turbulence model.                                                                                                                                               |
| `system/domainParameters`, `blockMeshDict`             | Domain dimensions and the initial coarse grid.                                                                                                                                         |
| `system/snappyHexMeshDict`                             | The active geometry, refinement and surface-fitting settings. `refinementParameters` records the targets but does not automatically control them.                                      |
| `system/surfaceFeatureExtractDict`, `meshQualityDict`  | Sharp-edge extraction and mesh-quality checks. Extracted `.eMesh` files help cells follow building corners.                                                                            |
| `system/controlDict`, `decomposeParDict`               | Run limits, saved results, monitoring and parallel process count.                                                                                                                      |
| `system/fvSchemes`, `fvSolution`                       | Numerical methods used to solve the flow.                                                                                                                                              |

### What the surface models represent

In `triSurface`, the building OBJs are physical obstacles. `additional_buildings_lod22_review.obj` is included as context despite its inherited `_review` name; this name does not confirm that every building is current.

`terrain_hull.obj` combines land, water, quay transitions and extended terrain into a closed ground body. Groups allow different roughness values; buried sides and bottom close it below the air. Water is fixed, with no water-flow simulation. OBJ materials only control appearance.

`pedestrian_refinement.obj` and `peninsula_surroundings.obj` request smaller air cells. They do not create walls. `pedestrian_1p5m.obj` is a surface for sampling results at pedestrian height.

## Main choices and reasons

- **Wind from 240°:** the prepared geometry is rotated so simulation `+X` points downwind towards true 060°. The extended ground uses the same coordinates, so it must not be rotated again. North-up figures only rotate the display.
- **Incoming profile:** 16 m/s at 60 m with regional roughness `z0 = 0.7 m`, recorded as a KNMI-derived strong-wind reference and Peutz Merwehaven exposure assumption. Wind increases with height. This is one wind condition, not annual pedestrian comfort.
- **Steady `simpleFoam` with `realizableKE`:** this estimates average flow and modelled turbulence at a manageable cost. Individual gusts are not resolved.
- **Domain and extended ground:** approximately 2.5 × 2.4 km, reaching Z = 550 m, leaving space for incoming flow and building wakes. Outer terrain continues the ground to the boundaries, beyond the main assessment area.
- **Local refinement:** about 16 m background cells, 2 m in the wider site region, 1 m near buildings and around the peninsula, and 0.5 m in the pedestrian band up to 3 m above ground. The band includes all outdoor ground because future walking routes are not fixed.
- **Laptop cost:** the earlier 0.25 m pedestrian band produced a much larger mesh. Reduced refinement brought the baseline from about 14.3 million to 6.7 million cells. This is a practical compromise, not a demonstrated mesh-independent solution. Extra wall layers are disabled.
- **Surface roughness:** water and paving use `z0 = 0.0002 m`, low vegetation `0.03 m`, and mixed/unclassified land `0.005 m`. These are representative classes rather than measurements. Regional inlet roughness is separate. Tree-canopy drag is not modelled.

### The green region

`greenRegion` is a rectangular **air-refinement box** around the site. It keeps more detail in the lower airflow approaching and passing the peninsula without refining the whole domain equally.

The name comes from the preview colour. It is separate from actual green ground (`terrain_peninsula_green`) and adds no vegetation, wall or drag. Its cell-size change can affect results and appear in maps, especially `k`. A visible rectangle is not a physical wind boundary; its sensitivity has not been established.

## Fixes and limitations

Geometry repairs addressed gaps beneath buildings and extended and closed the terrain. Foundation extensions are modelling repairs, not surveyed geometry. The tutorial grid was replaced, and surface-name mappings connect buildings and ground to their conditions.

Poorly shaped faces appeared during meshing. Snapping was adjusted to fit surfaces more carefully, with the same snapping and quality controls used for V1 and V2.

Later checks reported no faces violating the configured mesher limits, but extended checks still flagged skewness, small cell determinants and concave cells. The meshes therefore did not pass every check.

Plotting was revised to use native mesh cuts for scalar maps and sections, consistent north-up orientation and masks for the original ground coverage. Arrows and 2D streamlines still use a sampling grid. Display improvements do not repair the CFD solution.

## Workflow and figures

A fresh case follows this order: prepare geometry, extract edges, generate the mesh, check quality, initialise fields and run the solver. Parallel process counts must match the mesh partitions. Existing completed cases can be plotted or resumed without regenerating their mesh.

The current run limits are 500 iterations for baseline and 800 for V1/V2. These are computational limits, not proof of convergence. Residuals, flow balance and stable assessment values must also be considered.

For plotting, edit `scripts/wind/visualization/settings.py`: select `SCENARIO`, `TIME` (`None` means latest), `CASE_TYPE`, height and views. Defaults select baseline at iteration 500. Colour and camera settings are also there; keep colour scales consistent between scenarios.

| Script                                                      | Output                                                                                                   |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `wind_speed.py`, `pressure.py`, `turbulence.py`             | Wind speed, pressure and turbulent kinetic energy maps. Pressure is kinematic pressure in m²/s², not Pa. |
| `velocity_arrows.py`, `streamlines.py`, `streamlines_3d.py` | Wind arrows, horizontal flow paths and 3D flow paths.                                                    |
| `vertical_section.py`                                       | A vertical section through the shared peninsula centre.                                                  |
| `pressure_buildings.py`                                     | Buildings coloured by saved pressure.                                                                    |
| `common.py`, `coordinates.py`                               | Shared reading, plotting and coordinate helpers.                                                         |

`requirements.txt` lists plotting dependencies. Run scripts with the plotting Python environment. Separately, `scripts/wind/import_geometry_blender.py` loads source models into Blender.

Git contains configuration, input surfaces, plotting code and selected figures. Meshes, processor partitions, solver fields and extracted `.eMesh` files stay local. **Pulling the branch does not provide the solved datasets.** Replotting requires these results separately or a local simulation.

Background: [Blocken (2015)](https://doi.org/10.1016/j.buildenv.2015.02.015) and the [OpenFOAM meshing guide](https://www.openfoam.com/documentation/user-guide/4-mesh-generation-and-conversion/4.4-mesh-generation-with-the-snappyhexmesh-utility). Refinement extents and runtime compromises are project choices, not universal values prescribed by those references.
