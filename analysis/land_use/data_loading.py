"""Reading and writing rasters, and which class changes are allowed."""
import numpy as np
import rasterio

from config import SIMPLIFY_LABELS_MAP, OTHER, TRAFFIC, RESIDENTIAL, PUBLIC_FACILITY, GREEN_SPACE, WATER_SPACE


def load_raster(path):
    with rasterio.open(path) as src:
        return src.read(1)


def simplify_raster(raster):
    """Raw land-use codes -> the simplified classes from config."""
    f = np.vectorize(lambda x: SIMPLIFY_LABELS_MAP[x])
    return f(raster)


def save_raster(path, array, reference_path):
    """Write a class map with the georeferencing of the reference raster."""
    with rasterio.open(reference_path) as ref:
        profile = ref.profile
    profile.update(dtype="uint8", count=1, nodata=None, compress="lzw")
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array.astype("uint8"), 1)


def find_allowed_transitions(classes):
    """Boolean matrix: allowed[from_class, to_class]."""
    n_classes = len(classes)
    allowed = np.zeros((n_classes, n_classes), dtype=bool)

    # OTHER can change into anything
    allowed[OTHER, :] = True

    # PUBLIC_FACILITY and RESIDENTIAL can swap, and both can become GREEN_SPACE
    allowed[RESIDENTIAL, PUBLIC_FACILITY] = True
    allowed[RESIDENTIAL, GREEN_SPACE] = True
    allowed[PUBLIC_FACILITY, GREEN_SPACE] = True
    allowed[PUBLIC_FACILITY, RESIDENTIAL] = True

    # TRAFFIC and WATER can't be removed, and nothing can become them
    for fixed in (TRAFFIC, WATER_SPACE):
        allowed[fixed, :] = False
        allowed[:, fixed] = False

    # staying the same is always allowed
    np.fill_diagonal(allowed, True)
    return allowed