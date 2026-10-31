# geometry.py: clean the drawn lines (snap, cut) and measure the wind on them

import geopandas as gpd
import numpy as np
import rasterio
from shapely.geometry import Point, LineString
from shapely.ops import unary_union, nearest_points, substring

from config import SNAP


def snap_lines(lines):
    # endpoints closer than SNAP are moved onto the nearest line
    lines = lines.copy()
    geoms = list(lines.geometry)
    for i, g in enumerate(geoms):
        coords = list(g.coords)
        others = unary_union([h for j, h in enumerate(geoms) if j != i])
        for k in [0, -1]:
            p = Point(coords[k])
            d = p.distance(others)
            if 0 < d < SNAP:
                coords[k] = nearest_points(p, others)[1].coords[0]
        # the quay ring is drawn as one line: close it if start and end almost touch
        if Point(coords[0]).distance(Point(coords[-1])) < SNAP:
            coords[-1] = coords[0]
        geoms[i] = LineString(coords)
    lines["geometry"] = geoms
    return lines


def cut_lines(lines):
    # cut every line where another line crosses it or ends on it
    geoms = list(lines.geometry)
    cuts = {i: {0, g.length} for i, g in enumerate(geoms)}
    for i, g in enumerate(geoms):
        for j, h in enumerate(geoms):
            if i == j:
                continue
            for xy in [h.coords[0], h.coords[-1]]:  # h ends on g
                if Point(xy).distance(g) < 0.05:
                    cuts[i].add(g.project(Point(xy)))
            x = g.intersection(h)  # h crosses g
            for p in getattr(x, "geoms", [x]):
                if p.geom_type == "Point":
                    cuts[i].add(g.project(p))
    rows = []
    for i, g in enumerate(geoms):
        d = sorted(cuts[i])
        for d0, d1 in zip(d[:-1], d[1:]):
            if d1 - d0 > 0.1:
                rows.append({"seg_id": lines["seg_id"][i], "kind": lines["kind"][i], "geometry": substring(g, d0, d1)})
    return gpd.GeoDataFrame(rows, crs=28992)


def add_wind(pieces, wind_map, transform):
    # mean wind speed along every piece
    def mean_wind(line):
        n = max(int(line.length), 2)
        pts = [line.interpolate(i / (n - 1), normalized=True) for i in range(n)]
        rows, cols = rasterio.transform.rowcol(transform, [p.x for p in pts], [p.y for p in pts])
        return np.nanmean([wind_map[r, c] for r, c in zip(rows, cols)])

    pieces = pieces.copy()
    pieces["wind"] = pieces.geometry.apply(mean_wind)
    return pieces
