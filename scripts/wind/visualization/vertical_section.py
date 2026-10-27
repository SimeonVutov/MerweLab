"""Draw a vertical section through the centre of the peninsula."""

import numpy as np

import settings
from common import (
    add_colorbar,
    baseline_peninsula_surface,
    draw_surface,
    point_fields,
    read_case,
    save_figure,
)
from coordinates import to_display
import matplotlib.pyplot as plt


def section_geometry():
    """Find the peninsula centre and the direction of the section.

    Use triangle areas as weights so smaller triangles do not shift the centre.
    """
    surface = baseline_peninsula_surface().triangulate()
    triangle_indices = surface.faces.reshape(-1, 4)[:, 1:]
    triangles = surface.points[triangle_indices]
    edge_a = triangles[:, 1] - triangles[:, 0]
    edge_b = triangles[:, 2] - triangles[:, 0]
    plan_areas = np.abs(np.cross(edge_a, edge_b)[:, 2]) / 2

    triangle_centres = triangles.mean(axis=1)
    centre = np.average(triangle_centres, axis=0, weights=plan_areas)
    offsets = triangle_centres[:, :2] - centre[:2]

    # Find the direction that follows the length of the peninsula.
    weighted_offsets = offsets * plan_areas[:, np.newaxis]
    covariance = weighted_offsets.T @ offsets / plan_areas.sum()
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    section_direction = eigenvectors[:, -1]
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


def cut_section(flow, centre, direction, start, end):
    """Cut through the centre and keep the selected distance and height range."""
    normal = np.array([-direction[1], direction[0], 0.0])
    section = flow.slice(normal=normal, origin=centre, generate_triangles=True)

    section.point_data["section_distance"] = (
        section.points[:, :2] - centre[:2]
    ) @ direction

    along = np.array([direction[0], direction[1], 0.0])
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
    return section


def main():
    mesh, time = read_case(["U"])
    flow = point_fields(mesh)

    centre, direction, start, end = section_geometry()
    section = cut_section(flow, centre, direction, start, end)

    coordinates = np.column_stack((
        section.point_data["section_distance"], section.points[:, 2]
    ))

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

    ax.set_xlim(start, end)
    ax.set_ylim(settings.SECTION_BOTTOM, settings.SECTION_TOP)
    ax.set_xlabel("Distance along the peninsula centreline [m]")
    ax.set_ylabel("Model elevation Z [m]")
    ax.set_aspect("equal")
    add_colorbar(fig, ax, image, "Wind speed |U| [m/s]", fraction=0.03)

    direction_3d = np.array([direction[0], direction[1], 0.0])
    direction_display = to_display(direction_3d)
    bearing = np.rad2deg(np.arctan2(direction_display[0], direction_display[1])) % 360
    note = (
        f"Native cell section through common peninsula centre | "
        f"line bearing {bearing:.1f}° true | grey = no air cells"
    )
    save_figure(fig, "vertical_section", "peninsula", time, note)


if __name__ == "__main__":
    main()
