"""Draw 3D streamlines and colour them by wind speed."""

import numpy as np
import pyvista as pv

import settings
from common import (
    create_scene,
    point_fields,
    read_case,
    save_scene,
    scene_bounds,
    view_bounds,
)
from coordinates import display_mesh


def seed_points(flow, view):
    """Place the starting points before the site. Keep only points in the air."""
    bounds = view_bounds(view)
    rows = np.linspace(bounds[2], bounds[3], settings.SEEDS_PER_HEIGHT)
    points = []
    for height in settings.SEED_HEIGHTS:
        for y in rows:
            points.append((settings.SEED_X[view], y, height))
    points = np.array(points)

    samples = pv.PolyData(points).sample(flow)
    in_air = samples["vtkValidPointMask"].astype(bool)
    seeds = pv.PolyData(points[in_air])
    if not seeds.n_points:
        raise ValueError("No seeds in air: adjust SEED_X or SEED_HEIGHTS.")

    print(f"{view}: {seeds.n_points}/{len(points)} seeds in air", flush=True)
    return seeds


def main():
    mesh, time = read_case(["U"])
    flow = point_fields(mesh)

    for view in settings.VIEWS:
        seeds = seed_points(flow, view)
        lines = flow.streamlines_from_source(
            seeds,
            vectors="U",
            integration_direction="forward",
            integrator_type=45,
            initial_step_length=settings.STREAM_STEP,
            max_steps=settings.STREAM_STEPS,
            max_length=settings.STREAM_LENGTH[view],
            compute_vorticity=False,
            interpolator_type="cell",
        )
        if not lines.n_cells:
            raise ValueError("No streamlines: check seed positions and U.")

        lines.point_data["speed"] = np.linalg.norm(lines.point_data["U"], axis=1)
        lines = lines.clip_box(scene_bounds(view), invert=False)
        if not lines.n_cells:
            raise ValueError("Streamlines miss this view: move the seed line.")

        plot = create_scene(view)
        plot.add_mesh(
            display_mesh(lines).tube(radius=settings.TUBE_RADIUS[view], n_sides=12),
            scalars="speed",
            cmap=settings.SPEED_COLORS,
            clim=settings.SPEED_RANGE,
            scalar_bar_args={
                "title": "Wind speed [m/s]",
                "position_y": 0.06,
                "title_font_size": 18,
                "label_font_size": 15,
            },
        )

        save_scene(plot, "streamlines_3d", view, time)


if __name__ == "__main__":
    main()
