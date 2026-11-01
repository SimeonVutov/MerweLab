"""Extract terrain clipping polygons from the water OBJ, without Blender."""
from collections import Counter, defaultdict
import json
import numpy as np
from pyproj import Transformer
from coordinates import Placement
from download_grids import GRID_DIRECTORY, ROOT


def prepare_water_mask():
    vertices, edges = [], Counter()
    for line in (ROOT / 'data/scenarios/water_surface.obj').read_text().splitlines():
        if line.startswith('v '):
            vertices.append(list(map(float, line.split()[1:])))
        elif line.startswith('f '):
            face = [int(v.split('/')[0]) - 1 for v in line.split()[1:]]
            for a, b in zip(face, face[1:] + face[:1]):
                edges[tuple(sorted((a, b)))] += 1
    adjacency = defaultdict(list)
    for (a, b), count in edges.items():
        if count == 1:
            adjacency[a].append(b)
            adjacency[b].append(a)
        elif count != 2:
            raise ValueError('Non-manifold water mesh')
    if not adjacency or any(len(v) != 2 for v in adjacency.values()):
        raise ValueError('Expected closed water boundary rings')
    rings, seen = [], set()
    for start in adjacency:
        if start in seen:
            continue
        ring, previous, current = [], None, start
        while current not in seen:
            seen.add(current)
            ring.append(vertices[current])
            following = next(v for v in adjacency[current] if v != previous)
            previous, current = current, following
        if current != start:
            raise ValueError('Open water boundary')
        rings.append(ring)

    def contains(ring, point):
        x, y = point[:2]
        inside = False
        for a, b in zip(ring, ring[1:] + ring[:1]):
            if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
                inside = not inside
        return inside

    depths = [sum(contains(other, ring[0]) for other in rings if other is not ring) for ring in rings]
    config = json.loads((ROOT / 'config/merwelab_coordinates.json').read_text())
    placement = Placement(config['RD_origin'], GRID_DIRECTORY)
    geographic = Transformer.from_crs(4978, 4979, always_xy=True)
    converted = []
    for ring in rings:
        points = np.asarray(ring + [ring[0]])
        lon, lat, _ = geographic.transform(*placement.transformer.transform(*points.T, errcheck=True))
        converted.append(np.column_stack((lon, lat)).tolist())
    polygons = [[converted[i], *[converted[j] for j, hole in enumerate(rings)
                 if depths[j] == depths[i] + 1 and contains(ring, hole[0])]]
                for i, ring in enumerate(rings) if depths[i] % 2 == 0]
    output = ROOT / 'data/web/surfaces/water-mask.geojson'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'type': 'Feature', 'properties': {},
        'geometry': {'type': 'MultiPolygon', 'coordinates': polygons}}) + '\n')
    print(f'Prepared water mask: {len(polygons)} polygons, {len(rings)} rings')


if __name__ == '__main__':
    prepare_water_mask()
