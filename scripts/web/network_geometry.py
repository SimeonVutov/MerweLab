"""Place network graphics above the existing terrain and design pavement."""
import json
import math

import numpy as np
from pyproj import Transformer

from coordinates import Placement
from download_grids import GRID_DIRECTORY, ROOT


def inside_ring(point, ring):
    x, y = point
    inside = False
    for first, second in zip(ring, ring[1:]):
        x1, y1 = first[:2]
        x2, y2 = second[:2]
        if (y1 > y) == (y2 > y):
            continue

        crossing = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        if x < crossing:
            inside = not inside

    return inside


def inside_pavement(point, polygons):
    for rings in polygons:
        in_outline = inside_ring(point, rings[0]) or near_ring(point, rings[0])
        in_hole = any(inside_ring(point, hole) and not near_ring(point, hole) for hole in rings[1:])
        if in_outline and not in_hole:
            return True
    return False


def near_ring(point, ring, tolerance=0.5):
    # Candidate lines were snapped separately from pavement polygons. Include
    # their edges within half a metre to avoid alternating display heights.
    for first, second in zip(ring, ring[1:]):
        dx, dy = second[0] - first[0], second[1] - first[1]
        length_squared = dx * dx + dy * dy
        if length_squared == 0:
            continue

        along = ((point[0] - first[0]) * dx + (point[1] - first[1]) * dy) / length_squared
        along = max(0, min(1, along))
        closest = [first[0] + along * dx, first[1] + along * dy]
        if math.dist(point, closest) <= tolerance:
            return True
    return False


def densify_line(coordinates, spacing=5):
    points = [coordinates[0][:2]]
    for first, second in zip(coordinates, coordinates[1:]):
        count = max(1, math.ceil(math.dist(first[:2], second[:2]) / spacing))
        for step in range(1, count + 1):
            fraction = step / count
            points.append([first[axis] + fraction * (second[axis] - first[axis]) for axis in (0, 1)])
    return points


class NetworkPlacement:
    def __init__(self):
        coordinates = json.loads((ROOT / 'config/merwelab_coordinates.json').read_text())
        self.placement = Placement(coordinates['RD_origin'], GRID_DIRECTORY)
        self.geographic = Transformer.from_crs(4978, 4979, always_xy=True)
        self.surfaces = json.loads((ROOT / 'data/web/surfaces/manifest.json').read_text())
        self.terrain = json.loads((ROOT / 'data/web/terrain/manifest.json').read_text())

        url = self.terrain['scenarios']['baseline']['url']
        path = ROOT / 'data' / url.lstrip('/')
        shape = (self.terrain['height'], self.terrain['width'])
        self.heights = np.fromfile(path, dtype='<f4').reshape(shape)

    def deck_height(self, scenario):
        pavements = [model for model in self.surfaces['models'][scenario] if '/pavement_' in model['source']]
        if len(pavements) != 1:
            raise ValueError(f'Expected one design pavement surface for {scenario}')
        return pavements[0]['bounds_rd'][1][2]

    def terrain_height(self, longitude, latitude):
        west, south, east, north = self.terrain['bounds']
        column = (longitude - west) / (east - west) * (self.terrain['width'] - 1)
        row = (north - latitude) / (north - south) * (self.terrain['height'] - 1)
        if not (0 <= column < self.terrain['width'] - 1 and 0 <= row < self.terrain['height'] - 1):
            raise ValueError('Network lies outside the prepared terrain')

        left, top = int(column), int(row)
        dx, dy = column - left, row - top
        return float(
            self.heights[top, left] * (1 - dx) * (1 - dy)
            + self.heights[top, left + 1] * dx * (1 - dy)
            + self.heights[top + 1, left] * (1 - dx) * dy
            + self.heights[top + 1, left + 1] * dx * dy
        )

    def point(self, xy, deck_height, pavement, bridge=False):
        ecef = self.placement.transformer.transform(*xy[:2], deck_height, errcheck=True)
        longitude, latitude, deck_ellipsoid = self.geographic.transform(*ecef, errcheck=True)
        height = self.terrain_height(longitude, latitude)
        if bridge or inside_pavement(xy[:2], pavement):
            height = max(height, deck_ellipsoid)

        # These are display heights only. A small clearance prevents the lines
        # disappearing inside opaque pavement; analysis distances remain in RD.
        return [round(longitude, 8), round(latitude, 8), round(height + 0.2, 3)]

    def geometry(self, geometry, deck_height, pavement, bridge=False):
        if geometry['type'] == 'Point':
            point = self.point(geometry['coordinates'], deck_height, pavement)
            return {'type': 'Point', 'coordinates': point}

        if geometry['type'] != 'LineString':
            raise ValueError('Expected point or line network geometry')

        points = densify_line(geometry['coordinates'])
        coordinates = [self.point(point, deck_height, pavement, bridge) for point in points]
        return {'type': 'LineString', 'coordinates': coordinates}
