"""Plot settings. These do not change the simulation or its saved results."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCENARIO = "baseline"  # baseline, scenario_a, scenario_b
TIME = 500  # None selects the latest saved positive iteration
CASE_TYPE = "decomposed"  # or reconstructed
VIEWS = ("overview", "peninsula")

CASE = ROOT / "analysis/wind" / SCENARIO / "wind_240"
OUTPUT = ROOT / "outputs/figures/wind" / SCENARIO
PLACEMENT = ROOT / "data/scenarios/cfd_wind_240/placement.json"
PENINSULA_SURFACE = ROOT / "data/scenarios/baseline/cfd_wind_240/terrain_hull.obj"

# North-up is a display transform only. Original RD/CFD files stay unchanged.
ORIENTATION = "north"  # north (true north up) or cfd (downwind to the right)
HEIGHT = 1.5  # Vertical metres above the source ground/water surface
PENINSULA_MARGIN = 35.0

# Scalar maps and the vertical section cut the native CFD cells, without a raster
# sampling grid or mesh decimation. Interpolation averages neighbouring cell
# values at vertices; False shows the original piecewise-constant cell values.
INTERPOLATE = True
SHOW_CELL_EDGES = False

# Only arrows and 2D streamlines need a regular grid, in display coordinates.
FLOW_SPACING = {"overview": 2.0, "peninsula": 0.5}
ARROW_SPACING = {"overview": 45.0, "peninsula": 12.0}
ARROW_LENGTH = {"overview": 25.0, "peninsula": 8.0}  # Length of a 10 m/s arrow
STREAM_DENSITY = 1.8

# These are display limits, not comfort thresholds. Keep them fixed when comparing
# scenarios. Colour-bar extensions indicate values outside the displayed range.
SPEED_RANGE = (0.0, 14.0)
PRESSURE_RANGE = (-30.0, 30.0)  # OpenFOAM kinematic p, m²/s²; not Pa
TURBULENCE_RANGE = (0.0, 10.0)  # k, m²/s²
SPEED_COLORS = "viridis"
PRESSURE_COLORS = "RdBu_r"
TURBULENCE_COLORS = "magma"

# Integration stays in CFD coordinates; only the finished streamlines rotate.
SEED_HEIGHTS = (4.0, 8.0, 16.0, 30.0)  # Absolute CFD Z
SEEDS_PER_HEIGHT = 18
SEED_X = {"overview": -800.0, "peninsula": -200.0}
STREAM_LENGTH = {"overview": 2200.0, "peninsula": 700.0}
STREAM_STEP = 0.3  # Initial step in local cell lengths
STREAM_STEPS = 12000
TUBE_RADIUS = {"overview": 1.2, "peninsula": 0.45}

SCENE_Z_RANGE = (-5.0, 100.0)
CAMERA_BEARING = 180.0  # View from the south: east right, north towards the top
CAMERA_ELEVATION = 55.0
IMAGE_SIZE = (3000, 2200)
OFF_SCREEN = True

SECTION_DIRECTION = "long_axis"  # long_axis or wind
SECTION_ANGLE = None  # Optional override, degrees from CFD +X
SECTION_BOTTOM = -3.0
SECTION_TOP = 80.0
SECTION_MARGIN = 30.0

FIGURE_SIZE = (12, 11)
SECTION_FIGURE_SIZE = (13, 4.5)
DPI = 400
PRELIMINARY = True
