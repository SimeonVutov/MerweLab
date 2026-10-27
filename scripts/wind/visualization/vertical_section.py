"""Vertical section through the common peninsula centre; peninsula view only."""

import numpy as np
import pyvista as pv
import settings
from common import (
    read_case,
    baseline_peninsula_surface,
    save_figure,
    point_fields,
    draw_surface,
)
from coordinates import to_display
import matplotlib.pyplot as plt


def section_geometry():
    """Find the shared footprint centre, section direction and distance limits.

    Weight triangles by their horizontal area so dense triangulation does not
    dominate the centre. The principal axis estimates the longest direction.
    """
    surface = baseline_peninsula_surface().triangulate()
    triangle_indices = surface.faces.reshape(-1, 4)[:, 1:]
    triangles = surface.points[triangle_indices]
    plan_areas = (
        np.abs(
            np.cross(
                triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
            )[:, 2]
        )
        / 2
    )
    triangle_centres = triangles.mean(axis=1)
    centre = np.average(triangle_centres, axis=0, weights=plan_areas)
    offsets = triangle_centres[:, :2] - centre[:2]
    # The eigenvector with the largest variance follows the footprint's long axis.
    covariance = (offsets * plan_areas[:, None]).T @ offsets / plan_areas.sum()
    section_direction = np.linalg.eigh(covariance)[1][:, -1]
    if section_direction[0] < 0:
        section_direction *= -1
    if settings.SECTION_DIRECTION not in ("wind", "long_axis"):
        raise ValueError("SECTION_DIRECTION must be wind or long_axis.")
    if settings.SECTION_DIRECTION == "wind":
        section_direction = np.array([1.0, 0.0])
    if settings.SECTION_ANGLE is not None:
        angle = np.deg2rad(settings.SECTION_ANGLE)
        section_direction = np.array([np.cos(angle), np.sin(angle)])
    distances = (surface.points[:, :2] - centre[:2]) @ section_direction
    return (
        centre,
        section_direction,
        distances.min() - settings.SECTION_MARGIN,
        distances.max() + settings.SECTION_MARGIN,
    )


def main():
    mesh, time = read_case(["U"])
    flow = point_fields(mesh)
    centre, direction, start, end = section_geometry()
    normal = np.array([-direction[1], direction[0], 0.0])
    section = flow.slice(normal=normal, origin=centre, generate_triangles=True)
    section.point_data["section_distance"] = (
        section.points[:, :2] - centre[:2]
    ) @ direction
    along = np.r_[direction, 0.0]
    section = section.clip(normal=along, origin=centre + start * along, invert=False)
    section = section.clip(normal=along, origin=centre + end * along, invert=True)
    section = section.clip(
        normal="z", origin=(0, 0, settings.SECTION_BOTTOM), invert=False
    )
    section = section.clip(
        normal="z", origin=(0, 0, settings.SECTION_TOP), invert=True
    ).triangulate()
    if not section.n_cells:
        raise ValueError("No native section cells: check section bounds.")
    coordinates = np.c_[section.point_data["section_distance"], section.points[:, 2]]
    fig, ax = plt.subplots(figsize=settings.SECTION_FIGURE_SIZE, layout="constrained")
    ax.set_facecolor("#b1bec8")
    image = draw_surface(
        ax,
        section,
        "U",
        settings.SPEED_COLORS,
        settings.SPEED_RANGE,
        coordinates=coordinates,
    )
    ax.set(
        xlim=(start, end),
        ylim=(settings.SECTION_BOTTOM, settings.SECTION_TOP),
        xlabel="Distance along the peninsula centreline [m]",
        ylabel="Model elevation Z [m]",
        aspect="equal",
    )
    fig.colorbar(
        image,
        ax=ax,
        label="Wind speed |U| [m/s]",
        fraction=0.03,
        pad=0.025,
        extend="both",
    )
    direction_display = to_display(np.r_[direction, 0.0])
    bearing = np.rad2deg(np.arctan2(direction_display[0], direction_display[1])) % 360
    note = (
        f"Native cell section through common peninsula centre | "
        f"line bearing {bearing:.1f}° true | grey = no air cells"
    )
    save_figure(fig, "vertical_section", "peninsula", time, note)


if __name__ == "__main__":
    main()
