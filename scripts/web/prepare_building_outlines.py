"""Prepare shared and scenario building silhouettes from committed building geometry."""
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
import subprocess
import tempfile

from pyproj import Transformer
from coordinates import Placement
from download_grids import GRID_DIRECTORY, ROOT

OUTPUT = ROOT / 'data/web/building-outlines'


def rings(geometry):
    if geometry['type'] == 'Polygon':
        yield from geometry['coordinates']
    elif geometry['type'] == 'MultiPolygon':
        for polygon in geometry['coordinates']:
            yield from polygon
    elif geometry['type'] == 'GeometryCollection':
        for child in geometry['geometries']:
            yield from rings(child)


def save(group, lines):
    content = gzip.compress(json.dumps({'lines': lines}, separators=(',', ':')).encode(), mtime=0)
    name = f'{group}-{hashlib.sha256(content).hexdigest()[:12]}.json.gz'
    (OUTPUT / name).write_bytes(content)
    return f'/web/building-outlines/{name}'


def main():
    config = json.loads((ROOT / 'config/merwelab_coordinates.json').read_text())
    placement = Placement(config['RD_origin'], GRID_DIRECTORY)
    geographic = Transformer.from_crs(4978, 4979, always_xy=True)
    horizontal = Transformer.from_pipeline(placement.horizontal_pipeline + '+step +proj=unitconvert +xy_in=rad +xy_out=deg')
    bounds = json.loads((ROOT / 'data/web/terrain/manifest.json').read_text())['coreBounds']
    x, y = horizontal.transform(
        [bounds[0], bounds[0], bounds[2], bounds[2]],
        [bounds[1], bounds[3], bounds[1], bounds[3]],
        direction='INVERSE',
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    assets = {}
    models = json.loads((ROOT / 'data/web/buildings/manifest.json').read_text())
    detailed_ids = {identifier for group in models['models'].values()
                    for asset in group for identifier in asset.get('bag_ids', [])}

    with tempfile.TemporaryDirectory(prefix='merwelab-outlines-') as directory:
        for scenario in ('baseline', 'scenario_a', 'scenario_b'):
            source = ROOT / f'data/processed/noise/{scenario}/buildings.geojson'
            data = json.loads(source.read_text())
            filtered = []
            for feature in data['features']:
                properties = feature['properties']
                base = properties.get('MODEL_BASE')
                if base is None:
                    base = properties.get('GROUND_Z')
                if base is None or not math.isfinite(base):
                    raise ValueError('Building has no valid base height')
                identifier = properties.get('BUILDING') or properties.get('BAG_ID')
                bag = re.search(r'\d{16}', str(identifier))
                if properties['SOURCE'] == '3DBAG' and bag and bag.group() in detailed_ids:
                    continue
                polygons = feature['geometry']['coordinates']
                if feature['geometry']['type'] == 'Polygon':
                    polygons = [polygons]
                cleaned = []
                for polygon in polygons:
                    clean_rings = []
                    for ring in polygon:
                        points = []
                        for point in ring:
                            xy = point[:2]
                            if not points or xy != points[-1]:
                                points.append(xy)
                        if points and points[-1] != points[0]:
                            points.append(points[0])
                        area = abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points, points[1:])))
                        if len(points) >= 4 and area > 0.0001:
                            clean_rings.append(points)
                    if clean_rings:
                        cleaned.append(clean_rings)
                if not cleaned:
                    continue
                points = [point for polygon in cleaned for ring in polygon for point in ring]
                if max(p[0] for p in points) < min(x) or min(p[0] for p in points) > max(x):
                    continue
                if max(p[1] for p in points) < min(y) or min(p[1] for p in points) > max(y):
                    continue
                filtered.append({
                    'type': 'Feature',
                    'properties': {'SOURCE': properties['SOURCE'], 'BUILDING': str(identifier), 'MODEL_BASE': base},
                    'geometry': {'type': 'MultiPolygon', 'coordinates': cleaned},
                })
            source = Path(directory) / f'{scenario}-input.geojson'
            source.write_text(json.dumps({'type': 'FeatureCollection', 'name': 'buildings', 'features': filtered}))
            layer = 'buildings' 
            merged = Path(directory) / f'{scenario}.geojson'
            query = f'SELECT SOURCE, BUILDING, MIN(MODEL_BASE) AS base_nap, ST_Union(geometry) AS geometry FROM "{layer}" GROUP BY SOURCE, BUILDING'
            subprocess.run([
                'ogr2ogr', '-f', 'GeoJSON', '-dim', 'XY', '-dialect', 'SQLite', '-sql', query,
                '-spat', str(min(x)), str(min(y)), str(max(x)), str(max(y)),
                str(merged), str(source),
            ], check=True)

            shared = []
            design = []
            for feature in json.loads(merged.read_text())['features']:
                properties = feature['properties']
                group = shared
                if properties['SOURCE'].startswith(('baseline/', 'scenario_a/', 'scenario_b/')):
                    group = design
                elif scenario != 'baseline':
                    continue

                for ring in rings(feature['geometry']):
                    xx = [point[0] for point in ring]
                    yy = [point[1] for point in ring]
                    zz = [properties['base_nap']] * len(ring)
                    xyz = placement.transformer.transform(xx, yy, zz, errcheck=True)
                    longitude, latitude, height = geographic.transform(*xyz, errcheck=True)
                    group.append([value for point in zip(longitude, latitude, height) for value in point])

            if scenario == 'baseline':
                assets['shared'] = save('shared', shared)
            assets[scenario] = save(scenario, design)
            print(f'Prepared building outlines: {scenario} ({len(design)} design rings)')

    (OUTPUT / 'manifest.json').write_text(json.dumps({'version': 1, 'groups': assets}, indent=2) + '\n')


if __name__ == '__main__':
    main()
