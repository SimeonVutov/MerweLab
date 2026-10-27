"""Coordinate transforms for display; never rewrite geometry or result files."""

import json
from functools import lru_cache

import numpy as np

import settings


@lru_cache(maxsize=1)
def placement():
    with settings.PLACEMENT.open() as source:
        data = json.load(source)
    flow = np.asarray(data["flow_unit_vector_RD"], dtype=float)
    if not np.isclose(np.linalg.norm(flow), 1.0) or not np.isclose(flow[2], 0.0):
        raise ValueError("placement.json must contain a horizontal unit flow vector.")
    return data


def wind_bearing():
    """Meteorological bearing: where the wind comes FROM, relative to true north."""
    return float(placement()["wind_from_true_degrees"]) % 360


def display_rotation():
    """Rotate CFD +X to the downwind true bearing, or keep the solver axes."""
    if settings.ORIENTATION == "cfd":
        return np.eye(2)
    if settings.ORIENTATION != "north":
        raise ValueError("ORIENTATION must be north or cfd.")
    angle = np.deg2rad((wind_bearing() + 180) % 360)
    east, north = np.sin(angle), np.cos(angle)
    return np.array([[east, -north], [north, east]])


def to_display(values):
    """Rotate XY components of points or vectors; keep Z unchanged."""
    result = np.array(values, dtype=float, copy=True)
    result[..., :2] = result[..., :2] @ display_rotation().T
    return result


def to_cfd(values):
    """Inverse display rotation, used when probing a north-up map."""
    result = np.array(values, dtype=float, copy=True)
    result[..., :2] = result[..., :2] @ display_rotation()
    return result


def to_rd(points):
    """Recover original absolute RD coordinates using the saved placement."""
    fx, fy, _ = placement()["flow_unit_vector_RD"]
    result = np.array(points, dtype=float, copy=True)
    result[..., :2] = result[..., :2] @ np.array([[fx, fy], [-fy, fx]])
    return result + np.asarray(placement()["RD_origin"])


def display_mesh(mesh):
    """Rotate a separate display copy, including vector U when present."""
    result = mesh.copy(deep=True)
    result.points = to_display(mesh.points)
    for data in (result.point_data, result.cell_data):
        if "U" in data:
            data["U"] = to_display(data["U"])
    return result
