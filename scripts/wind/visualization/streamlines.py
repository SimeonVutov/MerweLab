"""2D paths of horizontal velocity on the height-following north-up map."""

import numpy as np
from matplotlib.colors import Normalize

import settings
from common import create_map, point_fields, read_case, sample_map, save_figure


def main():
    mesh, time = read_case(["U"])
    flow = point_fields(mesh)
    for view in settings.VIEWS:
        x, y, sampled, valid = sample_map(flow, view)
        velocity = sampled.point_data["U"].reshape((*valid.shape, 3))
        east = np.ma.array(velocity[:, :, 0], mask=~valid)
        north = np.ma.array(velocity[:, :, 1], mask=~valid)
        fig, ax = create_map(view)
        paths = ax.streamplot(
            x,
            y,
            east,
            north,
            color=np.hypot(east, north),
            cmap=settings.SPEED_COLORS,
            norm=Normalize(*settings.SPEED_RANGE),
            density=settings.STREAM_DENSITY,
            linewidth=1.3,
            arrowsize=1.1,
            zorder=3,
        )
        fig.colorbar(
            paths.lines,
            ax=ax,
            label="Horizontal wind speed [m/s]",
            fraction=0.035,
            pad=0.025,
            extend="both",
        )
        save_figure(
            fig,
            "streamlines",
            view,
            time,
            "2D paths of horizontal velocity; these are not full 3D trajectories",
        )


if __name__ == "__main__":
    main()
