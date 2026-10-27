"""Rotate coordinates for the figures. Keep the original files unchanged."""

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
    """Return the direction the wind comes from, measured clockwise from north."""
    return float(placement()["wind_from_true_degrees"]) % 360


def display_rotation():
    """Find the rotation from the simulation view to the map view."""
    if settings.ORIENTATION == "cfd":
        return np.eye(2)
    if settings.ORIENTATION != "north":
        raise ValueError("ORIENTATION must be north or cfd.")

    angle = np.deg2rad((wind_bearing() + 180) % 360)
    east, north = np.sin(angle), np.cos(angle)
    return np.array([[east, -north], [north, east]])


def to_display(values):
    """Rotate the horizontal coordinates. Keep the height unchanged."""
    result = np.array(values, dtype=float, copy=True)
    result[..., :2] = result[..., :2] @ display_rotation().T
    return result


def to_cfd(values):
    """Rotate map coordinates back to the simulation coordinates."""
    result = np.array(values, dtype=float, copy=True)
    result[..., :2] = result[..., :2] @ display_rotation()
    return result


def to_rd(points):
    """Convert simulation coordinates back to the original RD coordinates."""
    fx, fy, _ = placement()["flow_unit_vector_RD"]
    result = np.array(points, dtype=float, copy=True)
    result[..., :2] = result[..., :2] @ np.array([[fx, fy], [-fy, fx]])
    return result + np.asarray(placement()["RD_origin"])


def display_mesh(mesh):
    """Rotate a copy of the mesh and its wind vectors."""
    result = mesh.copy(deep=True)
    result.points = to_display(mesh.points)

    for data in (result.point_data, result.cell_data):
        if "U" in data:
            data["U"] = to_display(data["U"])

    return result
