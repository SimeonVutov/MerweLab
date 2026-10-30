"""Hard rules that are repaired after the model has chosen a map: class shares and public-facility clusters."""
import warnings
from collections import deque

import numpy as np
from scipy.ndimage import uniform_filter

from config import (
    OTHER, RESIDENTIAL, PUBLIC_FACILITY, GREEN_SPACE,
    MIN_RESIDENTIAL_SHARE, MIN_GREEN_SHARE, MAX_GREEN_SHARE, MAX_PUBLIC_FACILITY_SHARE,
    MIN_FACILITY_CLUSTERS, MIN_FACILITY_CLUSTER_SIZE,
)
from surroundings import distance_to_class, usable_mask, label_blocks, count_facility_clusters

SMOOTHING = 6  # flips are ranked on a smoothed score, so they form patches instead of single cells
CLUSTER_GAP_CELLS = 30  # a new facility cluster starts at least this far from an existing facility


def _chosen_q(state, q_full):
    """Q-value of the class every cell currently has."""
    return np.take_along_axis(q_full, state[..., None], axis=-1)[..., 0]


def _best_other(q_full, excluded):
    """Best class per cell once the `excluded` classes are ruled out, and its Q-value (-inf if nothing is left)."""
    q = q_full.copy()
    q[..., excluded] = -np.inf
    return q.argmax(axis=-1), q.max(axis=-1)


def _pick(score, candidates, how_many):
    """Row/col of the `how_many` best candidate cells (highest score). The score is smoothed first."""
    rows, cols = np.nonzero(candidates)
    how_many = min(how_many, len(rows))
    if how_many <= 0:
        return rows[:0], cols[:0]
    filled = np.where(candidates, score, score[candidates].min())
    smooth = uniform_filter(filled, size=SMOOTHING)[rows, cols]
    best = np.argsort(-smooth)[:how_many]
    return rows[best], cols[best]


def _lower_share(state, q_full, usable, label_, max_share):
    """Share of `label_` above the maximum: flip the cells that lose the least by becoming something else."""
    excess = int(((state == label_) & usable).sum() - np.floor(max_share * usable.sum()))
    if excess <= 0:
        return
    # flipped cells become OTHER or RESIDENTIAL, never another capped class (green / facility)
    best_other, best_q = _best_other(q_full, [label_, GREEN_SPACE, PUBLIC_FACILITY])
    candidates = usable & (state == label_) & np.isfinite(best_q)
    score = np.zeros(state.shape)
    score[candidates] = best_q[candidates] - q_full[..., label_][candidates]
    rows, cols = _pick(score, candidates, excess)
    state[rows, cols] = best_other[rows, cols]
    if len(rows) < excess:
        warnings.warn(f"class {label_} is above its maximum share and can not be lowered further")


def _raise_share(state, q_full, usable, label_, target_share, donors):
    """Share of `label_` below the target: turn the cells (currently one of `donors`) that like `label_` most into `label_`."""
    need = int(np.ceil(target_share * usable.sum()) - ((state == label_) & usable).sum())
    if need <= 0:
        return
    candidates = usable & np.isin(state, donors) & np.isfinite(q_full[..., label_])
    score = np.zeros(state.shape)
    score[candidates] = q_full[..., label_][candidates] - _chosen_q(state, q_full)[candidates]
    rows, cols = _pick(score, candidates, need)
    state[rows, cols] = label_
    if len(rows) < need:
        warnings.warn(f"not enough free cells to reach the minimum share for class {label_}")


def _dissolve_small_facilities(state, q_full, start):
    """Lonely facility pixels / blocks too small to be a cluster become OTHER or RESIDENTIAL again.
    Facilities that already exist in the start map are left alone."""
    block_ids, sizes = label_blocks(state, PUBLIC_FACILITY)
    too_small = sizes < MIN_FACILITY_CLUSTER_SIZE
    too_small[0] = False  # block 0 is the background
    too_small[np.unique(block_ids[(start == PUBLIC_FACILITY) & (block_ids > 0)])] = False
    replacement, replacement_q = _best_other(q_full, [PUBLIC_FACILITY, GREEN_SPACE])
    lonely = too_small[block_ids] & np.isfinite(replacement_q)
    state[lonely] = replacement[lonely]


def _grow_block(free, seed, size):
    """Breadth-first growth of `size` connected cells from `seed` through `free` cells.
    Returns None if the free area around the seed is too small."""
    height, width = free.shape
    block = [seed]
    seen = {seed}
    queue = deque([seed])
    while queue and len(block) < size:
        r, c = queue.popleft()
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < height and 0 <= nc < width and free[nr, nc] and (nr, nc) not in seen:
                seen.add((nr, nc))
                block.append((nr, nc))
                queue.append((nr, nc))
                if len(block) == size:
                    return block
    return block if len(block) == size else None


def _add_facility_clusters(state, q_full, usable):
    """Fewer than MIN_FACILITY_CLUSTERS clusters: grow a new connected block where the model likes facilities most."""
    for _ in range(max(0, MIN_FACILITY_CLUSTERS - count_facility_clusters(state))):
        free = usable & np.isin(state, [OTHER, RESIDENTIAL]) & np.isfinite(q_full[..., PUBLIC_FACILITY])
        free &= distance_to_class(state, PUBLIC_FACILITY) > CLUSTER_GAP_CELLS  # don't merge with an existing facility
        rows, cols = np.nonzero(free)
        if len(rows) == 0:
            break
        gain = np.zeros(state.shape)
        gain[free] = q_full[..., PUBLIC_FACILITY][free] - _chosen_q(state, q_full)[free]
        smooth = uniform_filter(np.where(free, gain, gain[free].min()), size=SMOOTHING)[rows, cols]
        # best seed first; a seed in a pocket of free cells that is too small is skipped
        for seed in np.argsort(-smooth):
            block = _grow_block(free, (int(rows[seed]), int(cols[seed])), MIN_FACILITY_CLUSTER_SIZE)
            if block is not None:
                state[tuple(np.array(block).T)] = PUBLIC_FACILITY
                break
        else:
            break
    if count_facility_clusters(state) < MIN_FACILITY_CLUSTERS:
        warnings.warn("could not create the minimum number of public facility clusters")


def enforce_constraints(state, q_full, start):
    """state: predicted map. q_full: (h, w, n_classes) Q-values, -inf where a class is not allowed.
    start: the map before the prediction."""
    state = state.copy()
    usable = usable_mask(start)
    # facility first: only real clusters, at most MAX share, trimming must not leave stray bits behind
    _dissolve_small_facilities(state, q_full, start)
    _lower_share(state, q_full, usable, PUBLIC_FACILITY, MAX_PUBLIC_FACILITY_SHARE)
    _dissolve_small_facilities(state, q_full, start)
    _lower_share(state, q_full, usable, GREEN_SPACE, MAX_GREEN_SHARE)
    _add_facility_clusters(state, q_full, usable)
    # green may take cells the model made residential (if there are too many of them), residential only takes OTHER cells,
    # so it goes last and refills whatever the steps before it took away
    _raise_share(state, q_full, usable, GREEN_SPACE, MIN_GREEN_SHARE, donors=[OTHER, RESIDENTIAL])
    _raise_share(state, q_full, usable, RESIDENTIAL, MIN_RESIDENTIAL_SHARE, donors=[OTHER])
    return state