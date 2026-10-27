"""Settings for the figures. These do not change the simulation."""

from pathlib import Path

# Case and output
ROOT = Path(__file__).resolve().parents[3]
SCENARIO = "baseline"  # baseline, scenario_a, scenario_b
TIME = 500  # None selects the latest saved positive iteration
CASE_TYPE = "decomposed"  # or reconstructed
VIEWS = ("overview", "peninsula")

CASE = ROOT / "analysis/wind" / SCENARIO / "wind_240"
OUTPUT = ROOT / "outputs/figures/wind" / SCENARIO
PLACEMENT = ROOT / "data/scenarios/cfd_wind_240/placement.json"
PENINSULA_SURFACE = ROOT / "data/scenarios/baseline/cfd_wind_240/terrain_hull.obj"

# Map orientation and height (display only)
ORIENTATION = "north"  # north (true north up) or cfd (downwind to the right)
HEIGHT = 1.5  # Vertical metres above the source ground/water surface
PENINSULA_MARGIN = 35.0

# True smooths colours between mesh points. False shows each cell value.
INTERPOLATE = True
SHOW_CELL_EDGES = False

# Arrows and 2D streamlines (spacing in display metres)
FLOW_SPACING = {"overview": 2.0, "peninsula": 0.5}
ARROW_SPACING = {"overview": 45.0, "peninsula": 12.0}
ARROW_LENGTH = {"overview": 25.0, "peninsula": 8.0}  # Length of a 10 m/s arrow
STREAM_DENSITY = 1.8

# Use the same colour limits for all scenarios. These are not comfort limits.
SPEED_RANGE = (0.0, 14.0)
PRESSURE_RANGE = (-30.0, 30.0)  # OpenFOAM kinematic p, m²/s²; not Pa
TURBULENCE_RANGE = (0.0, 10.0)  # k, m²/s²
SPEED_COLORS = "viridis"
PRESSURE_COLORS = "RdBu_r"
TURBULENCE_COLORS = "magma"

# 3D streamlines
SEED_HEIGHTS = (4.0, 8.0, 16.0, 30.0)  # Absolute CFD Z
SEEDS_PER_HEIGHT = 18
SEED_X = {"overview": -800.0, "peninsula": -200.0}
STREAM_LENGTH = {"overview": 2200.0, "peninsula": 700.0}
STREAM_STEP = 0.3  # Initial step in local cell lengths
STREAM_STEPS = 12000
TUBE_RADIUS = {"overview": 1.2, "peninsula": 0.45}

# 3D camera
SCENE_Z_RANGE = (-5.0, 100.0)
CAMERA_BEARING = 180.0  # View from the south: east right, north towards the top
CAMERA_ELEVATION = 55.0
IMAGE_SIZE = (3000, 2200)
OFF_SCREEN = True

# Peninsula section
SECTION_DIRECTION = "long_axis"  # long_axis or wind
SECTION_ANGLE = None  # Optional override, degrees from CFD +X
SECTION_BOTTOM = -3.0
SECTION_TOP = 80.0
SECTION_MARGIN = 30.0

# Image output
FIGURE_SIZE = (12, 11)
SECTION_FIGURE_SIZE = (13, 4.5)
DPI = 400
PRELIMINARY = True
