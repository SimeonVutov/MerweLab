"""Kinematic pressure p; no assumed air-density conversion."""

import settings
from common import draw_scalar_maps


def main():
    draw_scalar_maps(
        "p",
        "p_map",
        settings.PRESSURE_COLORS,
        settings.PRESSURE_RANGE,
        "Kinematic pressure p [m²/s²]",
    )


if __name__ == "__main__":
    main()
