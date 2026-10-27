"""Colour the building walls and roofs by pressure."""

import settings
from common import create_scene, point_fields, read_case, save_scene, scene_bounds
from coordinates import display_mesh


def main():
    walls, time = read_case(["p"], buildings_only=True)

    # Use the building faces for the pressure plot.
    walls = walls.extract_surface(algorithm="dataset_surface")
    if settings.INTERPOLATE:
        walls = point_fields(walls)

    for view in settings.VIEWS:
        visible = walls.clip_box(scene_bounds(view), invert=False)

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
