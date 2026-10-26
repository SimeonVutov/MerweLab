"""All settings in one place."""
from dataclasses import dataclass
from pathlib import Path

LAND_USE_2010_PATH = Path("../../data/land_use/train_land_use_2010.tif")
LAND_USE_2015_PATH = Path("../../data/land_use/train_land_use_2015.tif")

TARGET_LAND_USE_2010_PATH = Path("../../data/land_use/land_use_2010.tif")

TRAFFIC_AREAS = {10, 11, 12, 13}

BUILT_UP_AREAS = {20, 21, 22, 23, 24}

SEMI_BUILT_UP_AREAS = {30, 32, 33, 34, 35, 36}

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

SIMPLIFIED_LABELS = [1, 2, 3, 4, 5, 6, 7]
# Land use that is never allowed to change
STABLE_LABELS = [*WATER_AREAS, 7]

# A change is only allowed if it happened at least this many times
MIN_CHANGES_TO_ALLOW = 100

NEIGHBOURHOOD_SIZE = 9


@dataclass(frozen=True)
class ModelConfig:
    dense_neurons: int = 64
    learning_rate: float = 0.001
    epochs: int = 3
    batch_size: int = 512


@dataclass(frozen=True)
class TrainingConfig:
    episodes: int = 300
    epsilon_start: float = 1.0
    epsilon_decay: float = 0.98
    epsilon_min: float = 0.05
    changing_cells_per_episode: int = 15000
    same_cells_per_episode: int = 20000 