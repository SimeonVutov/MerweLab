from pathlib import Path

import numpy as np
from pyproj import Transformer, network

from download_grids import GRID_NAMES


class Placement:
    def __init__(self, origin_rd, grid_directory: Path):
        for name in GRID_NAMES:
            if not (grid_directory / name).is_file():
                raise FileNotFoundError(f"Missing {name}; run scripts/web/download_grids.py")

        network.set_network_enabled(False)
        self.horizontal_pipeline = (
            "+proj=pipeline +step +inv +proj=sterea "
            "+lat_0=52.1561605555556 +lon_0=5.38763888888889 "
            "+k=0.9999079 +x_0=155000 +y_0=463000 +ellps=bessel "
            f'+step +proj=hgridshift +grids="{grid_directory / GRID_NAMES[0]}" '
        )
        self.pipeline = (
            self.horizontal_pipeline +
            f'+step +proj=vgridshift +grids="{grid_directory / GRID_NAMES[1]}" +multiplier=1 '
            "+step +proj=cart +ellps=WGS84"
        )
        self.transformer = Transformer.from_pipeline(self.pipeline)
        self.origin_rd = np.asarray(origin_rd, dtype=np.float64)
        self.origin_ecef = np.asarray(self.transformer.transform(*self.origin_rd, errcheck=True))
        geographic = Transformer.from_crs(4978, 4979, always_xy=True)
        self.origin_geographic = geographic.transform(*self.origin_ecef, errcheck=True)
        lon, lat = np.radians(self.origin_geographic[:2])
        self.axes = np.array([
            [-np.sin(lon), -np.sin(lat) * np.cos(lon), np.cos(lat) * np.cos(lon)],
            [np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat) * np.sin(lon)],
            [0, np.cos(lat), np.sin(lat)],
        ])

    def to_local(self, points):
        points = np.asarray(points, dtype=np.float64)
        ecef = np.column_stack(self.transformer.transform(*points.T, errcheck=True))
        return (ecef - self.origin_ecef) @ self.axes

    def to_rd(self, points):
        ecef = self.origin_ecef + np.asarray(points) @ self.axes.T
        return np.column_stack(
            self.transformer.transform(*ecef.T, direction="INVERSE", errcheck=True)
        )
