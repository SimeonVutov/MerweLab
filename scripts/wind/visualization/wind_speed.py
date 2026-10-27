"""Draw wind speed at the selected height above the ground."""

import settings
from common import draw_scalar_maps


def main():
    draw_scalar_maps(
        "U",
        "U_map",
        settings.SPEED_COLORS,
        settings.SPEED_RANGE,
        "Wind speed |U| [m/s]",
    )


if __name__ == "__main__":
    main()
