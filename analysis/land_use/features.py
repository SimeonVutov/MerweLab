"""Turn a class map into one feature vector per cell."""
import numpy as np
from scipy.ndimage import uniform_filter

from config import (
    NEIGHBOURHOOD_SIZES, MAX_FEATURE_DISTANCE_CELLS,
    TRAFFIC, PUBLIC_FACILITY, GREEN_SPACE, WATER_SPACE,
)
from surroundings import distance_to_class


def distance_feature(state, label_):
    """Manhattan distance to the nearest cell of class `label_`, scaled to 0 (on it) .. 1 (far or missing)."""
    return np.minimum(distance_to_class(state, label_), MAX_FEATURE_DISTANCE_CELLS) / MAX_FEATURE_DISTANCE_CELLS


def make_features(state, n_classes):
    """Returns (height, width, n_classes * (1 + len(NEIGHBOURHOOD_SIZES)) + 4)."""
    # one-hot class of the cell itself
    state_class = np.eye(n_classes)[state]
    # class shares around the cell, for every window size
    arounds = [np.stack([uniform_filter(state_class[:, :, k], size=size) for k in range(n_classes)], axis=-1)
               for size in NEIGHBOURHOOD_SIZES]
    # distance to the things the reward cares about
    distances = np.stack([distance_feature(state, TRAFFIC),
                          distance_feature(state, PUBLIC_FACILITY),
                          distance_feature(state, GREEN_SPACE),
                          distance_feature(state, WATER_SPACE)], axis=-1)
    return np.concatenate([state_class, *arounds, distances], axis=-1)