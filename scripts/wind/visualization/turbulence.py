"""Modelled turbulent kinetic energy k, not instantaneous gust speed."""

import settings
from common import draw_scalar_maps


def main():
    draw_scalar_maps(
        "k",
        "turbulence",
        settings.TURBULENCE_COLORS,
        settings.TURBULENCE_RANGE,
        "Turbulent kinetic energy k [m²/s²]",
    )


if __name__ == "__main__":
    main()
