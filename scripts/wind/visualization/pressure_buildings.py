"""Colour actual CFD building boundary faces by their saved pressure."""

import settings
from common import create_scene, point_fields, read_case, save_scene, view_bounds
from coordinates import display_mesh


def main():
    walls, time = read_case(["p"], buildings_only=True)
    # Work with surface polygons directly, avoiding volume-cell clipping warnings.
    walls = walls.extract_surface(algorithm="dataset_surface")
    if settings.INTERPOLATE:
        walls = point_fields(walls)
    for view in settings.VIEWS:
        visible = walls.clip_box(
            [*view_bounds(view)[:4], *settings.SCENE_Z_RANGE], invert=False
        )
        plot = create_scene(view, show_buildings=False)
        plot.add_mesh(
            display_mesh(visible),
            scalars="p",
            preference="point" if settings.INTERPOLATE else "cell",
            cmap=settings.PRESSURE_COLORS,
            clim=settings.PRESSURE_RANGE,
            scalar_bar_args={
                "title": "Kinematic p [m²/s²]",
                "position_y": 0.06,
                "title_font_size": 18,
                "label_font_size": 15,
            },
        )
        save_scene(plot, "pressure_buildings", view, time)


if __name__ == "__main__":
    main()
