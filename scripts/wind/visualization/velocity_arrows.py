"""Draw wind arrows over the wind-speed map."""

import numpy as np

import settings
from common import (
    add_colorbar,
    create_map,
    draw_surface,
    height_surface,
    point_fields,
    read_case,
    sample_map,
    save_figure,
)


def main():
    mesh, time = read_case(["U"])
    flow = point_fields(mesh)
    surface = height_surface(flow)

    for view in settings.VIEWS:
        x, y, velocity, valid = sample_map(
            flow, view, spacing=settings.ARROW_SPACING[view]
        )
        xx, yy = np.meshgrid(x, y)

        fig, ax = create_map(view)
        image = draw_surface(
            ax, surface, "U", settings.SPEED_COLORS, settings.SPEED_RANGE
        )

        arrows = ax.quiver(
            xx[valid],
            yy[valid],
            velocity[:, :, 0][valid],
            velocity[:, :, 1][valid],
            color="#172632",
            angles="xy",
            scale_units="xy",
            scale=10.0 / settings.ARROW_LENGTH[view],
            width=0.002,
            zorder=7,
        )

        ax.quiverkey(arrows, 0.67, 0.97, 10, "10 m/s", labelpos="E", coordinates="axes")
        add_colorbar(fig, ax, image, "Wind speed |U| [m/s]")

        save_figure(
            fig,
            "velocity_arrows",
            view,
            time,
            f"Horizontal velocity vectors | {settings.HEIGHT:g} m above source ground/water",
        )


if __name__ == "__main__":
    main()
