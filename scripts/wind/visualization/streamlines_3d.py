"""Integrate full 3D streamlines in CFD coordinates, then rotate for display."""

import numpy as np
import pyvista as pv

import settings
from common import create_scene, point_fields, read_case, save_scene, view_bounds
from coordinates import display_mesh


def main():
    mesh, time = read_case(["U"])
    flow = point_fields(mesh)
    for view in settings.VIEWS:
        bounds = view_bounds(view)
        y = np.linspace(bounds[2], bounds[3], settings.SEEDS_PER_HEIGHT)
        points = np.array(
            [(settings.SEED_X[view], yy, z) for z in settings.SEED_HEIGHTS for yy in y]
        )
        samples = pv.PolyData(points).sample(flow)
        seeds = pv.PolyData(points[samples["vtkValidPointMask"].astype(bool)])
        if not seeds.n_points:
            raise ValueError("No seeds in air: adjust SEED_X or SEED_HEIGHTS.")
        print(f"{view}: {seeds.n_points}/{len(points)} seeds in air", flush=True)
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
        lines = lines.clip_box([*bounds[:4], *settings.SCENE_Z_RANGE], invert=False)
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
