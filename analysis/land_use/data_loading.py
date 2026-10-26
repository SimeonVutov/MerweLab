import numpy as np
import rasterio

from config import (MIN_CHANGES_TO_ALLOW, STABLE_LABELS)


def load_raster(path):
    return rasterio.open(path).read(1)

def simplify_raster(raster):
    return raster // 10


def find_allowed_transitions(start, target, classes):
    n_classes = len(classes)
    counts = np.zeros((n_classes, n_classes), dtype=int)
    for old in range(n_classes):
        for new in range(n_classes):
            counts[old, new] = np.sum((start == old) & (target == new))

    # a change is allowed if it happened often enough
    allowed = counts >= MIN_CHANGES_TO_ALLOW

    # staying the same is always allowed
    np.fill_diagonal(allowed, True)

    # stable classes (water) can only stay the same
    for label in STABLE_LABELS:
        if label in classes:
            i = np.searchsorted(classes, label)
            allowed[i, :] = False
            allowed[i, i] = True

    return allowed