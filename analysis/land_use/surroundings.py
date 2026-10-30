"""Measurements on a class map: distances, neighbours, shares and public-facility blocks."""
import numpy as np
from scipy.ndimage import convolve, distance_transform_cdt, label, uniform_filter

from config import (
    CELL_SIZE_M, TRAFFIC, PUBLIC_FACILITY, WATER_SPACE, MIN_FACILITY_CLUSTER_SIZE,
)

# 3x3 block of ones with the middle cell left out -> counts the 8 surrounding cells
NEIGHBOUR_KERNEL = np.ones((3, 3))
NEIGHBOUR_KERNEL[1, 1] = 0


def usable_mask(start):
    """Cells that count for the shares: everything except water and traffic."""
    return (start != WATER_SPACE) & (start != TRAFFIC)


def distance_to_class(state, label_):
    """For every cell: Manhattan distance in cells (steps up/down/left/right) to the nearest cell of class `label_`.
    Returns inf everywhere if the class does not exist on the map."""
    is_label = state == label_
    if not is_label.any():
        return np.full(state.shape, np.inf)
    return distance_transform_cdt(~is_label, metric="taxicab").astype(float)


def count_same_neighbours(state, n_classes):
    """For every cell: how many of its 8 neighbours have the same class (0 to 8)."""
    one_hot = np.eye(n_classes)[state]
    # for every class: how many of the 8 neighbours belong to that class
    counts = np.stack([convolve(one_hot[:, :, k], NEIGHBOUR_KERNEL, mode="nearest")
                       for k in range(n_classes)], axis=-1)
    # keep only the count of the cell's own class
    return (counts * one_hot).sum(axis=-1)


def share_around(mask, distance_m):
    """For every cell: share of `mask` cells within `distance_m` (square window)."""
    return uniform_filter(mask.astype(float), size=2 * (distance_m // CELL_SIZE_M) + 1, mode="nearest")


def label_blocks(state, label_):
    """Connected blocks (up/down/left/right) of one class.
    Returns the block id of every cell (0 = not this class) and the size of each block (index 0 = background)."""
    block_ids, n_blocks = label(state == label_)
    sizes = np.bincount(block_ids.ravel(), minlength=n_blocks + 1)
    return block_ids, sizes


def count_facility_clusters(state):
    """Number of public-facility blocks that are big enough to count as a cluster."""
    _, sizes = label_blocks(state, PUBLIC_FACILITY)
    return int((sizes[1:] >= MIN_FACILITY_CLUSTER_SIZE).sum())


def count_lonely_facility_cells(state):
    """Number of public-facility cells that sit in a block too small to be a cluster."""
    block_ids, sizes = label_blocks(state, PUBLIC_FACILITY)
    too_small = sizes < MIN_FACILITY_CLUSTER_SIZE
    too_small[0] = False  # block 0 is the background
    return int(too_small[block_ids].sum())