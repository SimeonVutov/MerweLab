"""All settings in one place."""
from dataclasses import dataclass
from pathlib import Path

# ---- Paths ----
ROOT = Path(__file__).resolve().parents[2]
DATA_LAND_USE_DIR = ROOT / "data/land_use"
LAND_USE_PATH = DATA_LAND_USE_DIR.joinpath("land_use_in_context_area_smaller.tif")
SIMPLIFIED_MAP_PATH = DATA_LAND_USE_DIR / "simplified_land_use.tif"
PREDICTED_MAP_PATH = DATA_LAND_USE_DIR.joinpath("predicted_map_corrected.tif")
MODEL_PATH = DATA_LAND_USE_DIR.joinpath("results/land_use_prediction_corrected.keras")

# ---- Raw land-use codes, grouped by category ----
TRAFFIC_AREAS = {10, 11, 12, 13}
BUILT_UP_AREAS = {20, 21, 22, 23, 24}
SEMI_BUILT_UP_AREAS = {30, 31, 32, 33, 34, 35, 36}
RECREATION_AREAS = {40, 41, 42, 43, 44}
AGRICULTURE_AREAS = {50, 51, 52, 53}
NATURAL_AREAS = {60, 61, 62}
WATER_AREAS = {70, 71, 72, 73, 74, 75, 76, 77, 78}

ALL_LABELS = [*TRAFFIC_AREAS,
              *BUILT_UP_AREAS,
              *SEMI_BUILT_UP_AREAS,
              *RECREATION_AREAS,
              *AGRICULTURE_AREAS,
              *NATURAL_AREAS,
              *WATER_AREAS]

# ---- Simplified classes the model works with ----
OTHER = 0
TRAFFIC = 1
RESIDENTIAL = 2
PUBLIC_FACILITY = 3
GREEN_SPACE = 4
WATER_SPACE = 5

CLASS_NAMES = ["other", "traffic", "residential", "public facility", "green space", "water"]
SIMPLIFIED_LABELS = list(range(len(CLASS_NAMES)))

# raw code -> simplified class (later entries overwrite the OTHER default)
SIMPLIFY_LABELS_MAP = {
    **dict.fromkeys(ALL_LABELS, OTHER),
    **dict.fromkeys(TRAFFIC_AREAS, TRAFFIC),
    **dict.fromkeys([20], RESIDENTIAL),
    **dict.fromkeys([22], PUBLIC_FACILITY),
    **dict.fromkeys(RECREATION_AREAS, GREEN_SPACE),
    **dict.fromkeys(WATER_AREAS, WATER_SPACE),
}


# ---- Model and training ----
@dataclass(frozen=True)
class ModelConfig:
    dense_neurons: int = 96
    learning_rate: float = 0.001
    epochs: int = 3  # fit epochs per episode
    batch_size: int = 256


@dataclass(frozen=True)
class TrainingConfig:
    episodes: int = 250
    epsilon_start: float = 0.75
    epsilon_decay: float = 0.9875
    epsilon_min: float = 0.05


# ---- Features ----
NEIGHBOURHOOD_SIZES = [3, 5, 9, 21, 41, 61, 81]  # window sizes (cells) for the class-share features
MAX_FEATURE_DISTANCE_CELLS = 40  # distance features are capped here (40 cells = 320 m)

# ---- Map rules (8 m cells) ----
CELL_SIZE_M = 8

# Shares are measured on the usable area only (everything except water and traffic)
MIN_GREEN_SHARE = 0.15
MAX_GREEN_SHARE = 0.25
MIN_RESIDENTIAL_SHARE = 0.50
MAX_PUBLIC_FACILITY_SHARE = 0.05

# Public facility must come in blocks: at least N separate blocks of at least M connected cells each
MIN_FACILITY_CLUSTERS = 4
MIN_FACILITY_CLUSTER_SIZE = 36 # average size of a supermarket in netherlands is 1000 m^2

# Distances in metres
MAX_DIST_TO_TRAFFIC_M = 160  # residential is penalised without TRAFFIC within this distance
MAX_DIST_TO_FACILITY_M = 240  # residential gets a bonus with PUBLIC_FACILITY within this distance
MAX_DIST_TO_GREEN_M = 160  # residential gets a bonus with GREEN_SPACE within this distance
MAX_DIST_TO_WATER_FOR_GREEN_M = 16  # green space gets a bonus this close to WATER

MIN_SAME_NEIGHBOURS = 3  # every cell wants this many same-class cells among its 8 neighbours
MIN_FACILITY_NEIGHBOURS = 5

# ---- Reward weights ----
CELL_NEIGHBOURING_PENALTY = 1.0  # per cell with fewer than MIN_SAME_NEIGHBOURS same-class neighbours
FACILITY_SMALL_BLOCK_PENALTY = 0.75 # facility cell in a block smaller than MIN_FACILITY_CLUSTER_SIZE
CELL_PENALTY = 1.0  # residential without TRAFFIC nearby
CELL_CHANGE_PENALTY_WEIGHT = 0.75  # per changed cell (changes from OTHER are free)
FACILITY_LONELY_PENALTY = 1.5

# Global share rules: only the cells that fix the shortage get the bonus, only the cells that cause an excess the penalty
GLOBAL_RESIDENTIAL_BONUS_WEIGHT = 2.0
GLOBAL_GREEN_SPACE_BONUS_WEIGHT = 2.0
GLOBAL_GREEN_SPACE_PENALTY_WEIGHT = 10.0
GLOBAL_PUBLIC_FACILITY_PENALTY_WEIGHT = 10.0

# Proximity bonuses
RESIDENTIAL_NEAR_GREEN_BONUS = 0.75
RESIDENTIAL_NEAR_FACILITY_BONUS = 1.25
GREEN_NEAR_WATER_BONUS = 1.0
FACILITY_SERVICE_BONUS = 6.0  # scaled by the share of residential around the facility cell
GREEN_SERVICE_BONUS = 3.0  # same for green space
