"""Prepare shared and scenario building silhouettes from committed building geometry."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile

from pyproj import Transformer

from coordinates import Placement
from download_grids import GRID_DIRECTORY, ROOT

OUTPUT = ROOT / 'data/web/building-outlines'
SCENARIOS = ('baseline', 'scenario_a', 'scenario_b')
DESIGN_SOURCE_PREFIXES = tuple(f'{scenario}/' for scenario in SCENARIOS)
MIN_DOUBLED_RING_AREA = 0.0001


def iter_geometry_rings(geometry):
    geometry_type = geometry['type']
    if geometry_type == 'Polygon':
        yield from geometry['coordinates']
        return

    if geometry_type == 'MultiPolygon':
        for polygon in geometry['coordinates']:
            yield from polygon
        return

    if geometry_type == 'GeometryCollection':
        for child in geometry['geometries']:
            yield from iter_geometry_rings(child)


def clean_footprint_ring(ring):
    # Mesh faces can repeat XY coordinates at different heights. Flattening them
    # removes duplicate vertices and lets us reject vertical, zero-area faces.
    points = []
    for vertex in ring:
        horizontal_point = vertex[:2]
        if not points or horizontal_point != points[-1]:
            points.append(horizontal_point)

    if points and points[-1] != points[0]:
        points.append(points[0])

    if len(points) < 4:
        return []

    doubled_area = abs(sum(
        start[0] * end[1] - end[0] * start[1]
        for start, end in zip(points, points[1:])
    ))
    if not doubled_area > MIN_DOUBLED_RING_AREA:
        return []

    return points


def clean_footprint_polygons(geometry):
    polygons = geometry['coordinates']
    if geometry['type'] == 'Polygon':
        polygons = [polygons]

    cleaned_polygons = []
    for polygon in polygons:
        cleaned_rings = [clean_footprint_ring(ring) for ring in polygon]
        valid_rings = [ring for ring in cleaned_rings if ring]
        if valid_rings:
            cleaned_polygons.append(valid_rings)

    return cleaned_polygons


def intersects_bounds(polygons, bounds):
    points = [point for polygon in polygons for ring in polygon for point in ring]
    eastings = [point[0] for point in points]
    northings = [point[1] for point in points]
    west, south, east, north = bounds

    outside_east_west = max(eastings) < west or min(eastings) > east
    outside_north_south = max(northings) < south or min(northings) > north
    return not (outside_east_west or outside_north_south)


def read_base_height(properties):
    base_height = properties.get('MODEL_BASE')
    if base_height is None:
        base_height = properties.get('GROUND_Z')

    if base_height is None or not math.isfinite(base_height):
        raise ValueError('Building has no valid base height')

    return base_height


def is_duplicate_regional_building(properties, identifier, detailed_ids):
    if properties['SOURCE'] != '3DBAG':
        return False

    bag_match = re.search(r'\d{16}', str(identifier))
    return bag_match is not None and bag_match.group() in detailed_ids


def prepare_building_feature(feature, detailed_ids, bounds):
    properties = feature['properties']
    base_height = read_base_height(properties)
    identifier = properties.get('BUILDING') or properties.get('BAG_ID')

    # Detailed models already supply these outlines; keeping their regional
    # counterparts would draw the same building twice.
    if is_duplicate_regional_building(properties, identifier, detailed_ids):
        return None

    polygons = clean_footprint_polygons(feature['geometry'])
    if not polygons or not intersects_bounds(polygons, bounds):
        return None

    return {
        'type': 'Feature',
        'properties': {
            'SOURCE': properties['SOURCE'],
            'BUILDING': str(identifier),
            'MODEL_BASE': base_height,
        },
        'geometry': {'type': 'MultiPolygon', 'coordinates': polygons},
    }


def read_detailed_building_ids():
    manifest = json.loads((ROOT / 'data/web/buildings/manifest.json').read_text())
    return {
        identifier
        for model_group in manifest['models'].values()
        for asset in model_group
        for identifier in asset.get('bag_ids', [])
    }


def terrain_bounds_in_rd(placement):
    manifest = json.loads((ROOT / 'data/web/terrain/manifest.json').read_text())
    west, south, east, north = manifest['coreBounds']
    horizontal_transformer = Transformer.from_pipeline(
        placement.horizontal_pipeline + '+step +proj=unitconvert +xy_in=rad +xy_out=deg'
    )

    # Transform all four corners: the projected envelope is not aligned with
    # longitude and latitude, so two opposite corners are insufficient.
    eastings, northings = horizontal_transformer.transform(
        [west, west, east, east],
        [south, north, south, north],
        direction='INVERSE',
    )
    return min(eastings), min(northings), max(eastings), max(northings)


def dissolve_building_fragments(scenario, directory, detailed_ids, bounds):
    source_path = ROOT / f'data/processed/noise/{scenario}/buildings.geojson'
    source_data = json.loads(source_path.read_text())
    prepared_features = []
    for feature in source_data['features']:
        prepared_feature = prepare_building_feature(feature, detailed_ids, bounds)
        if prepared_feature is not None:
            prepared_features.append(prepared_feature)

    prepared_path = directory / f'{scenario}-input.geojson'
    prepared_path.write_text(json.dumps({
        'type': 'FeatureCollection',
        'name': 'buildings',
        'features': prepared_features,
    }))

    # Dissolving mesh fragments removes internal triangulation edges. Both
    # source and building ID are needed to keep unrelated buildings separate.
    query = (
        'SELECT SOURCE, BUILDING, MIN(MODEL_BASE) AS base_nap, '
        'ST_Union(geometry) AS geometry FROM "buildings" GROUP BY SOURCE, BUILDING'
    )
    dissolved_path = directory / f'{scenario}.geojson'
    subprocess.run([
        'ogr2ogr', '-f', 'GeoJSON', '-dim', 'XY', '-dialect', 'SQLite', '-sql', query,
        '-spat', *[str(coordinate) for coordinate in bounds],
        str(dissolved_path), str(prepared_path),
    ], check=True)

    return json.loads(dissolved_path.read_text())['features']


def transform_outline_ring(ring, base_height, placement, geographic_transformer):
    eastings = [point[0] for point in ring]
    northings = [point[1] for point in ring]
    base_heights = [base_height] * len(ring)

    # Preserve the original NAP base height through the placement transform;
    # the browser expects longitude, latitude and ellipsoid height.
    geocentric_coordinates = placement.transformer.transform(
        eastings, northings, base_heights, errcheck=True,
    )
    longitudes, latitudes, heights = geographic_transformer.transform(
        *geocentric_coordinates, errcheck=True,
    )
    return [
        coordinate
        for point in zip(longitudes, latitudes, heights)
        for coordinate in point
    ]


def collect_outline_groups(features, scenario, placement, geographic_transformer):
    shared_outlines = []
    design_outlines = []
    for feature in features:
        properties = feature['properties']
        is_design_building = properties['SOURCE'].startswith(DESIGN_SOURCE_PREFIXES)
        if not is_design_building and scenario != 'baseline':
            continue

        target_outlines = shared_outlines
        if is_design_building:
            target_outlines = design_outlines

        for ring in iter_geometry_rings(feature['geometry']):
            outline = transform_outline_ring(
                ring, properties['base_nap'], placement, geographic_transformer,
            )
            target_outlines.append(outline)

    return shared_outlines, design_outlines


def save_outlines(group, outlines):
    serialized_outlines = json.dumps({'lines': outlines}, separators=(',', ':')).encode()
    content = gzip.compress(serialized_outlines, mtime=0)
    filename = f'{group}-{hashlib.sha256(content).hexdigest()[:12]}.json.gz'
    (OUTPUT / filename).write_bytes(content)
    return f'/web/building-outlines/{filename}'


def main():
    config = json.loads((ROOT / 'config/merwelab_coordinates.json').read_text())
    placement = Placement(config['RD_origin'], GRID_DIRECTORY)
    geographic_transformer = Transformer.from_crs(4978, 4979, always_xy=True)
    bounds = terrain_bounds_in_rd(placement)
    detailed_ids = read_detailed_building_ids()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    assets = {}
    with tempfile.TemporaryDirectory(prefix='merwelab-outlines-') as directory:
        for scenario in SCENARIOS:
            features = dissolve_building_fragments(
                scenario, Path(directory), detailed_ids, bounds,
            )
            shared_outlines, design_outlines = collect_outline_groups(
                features, scenario, placement, geographic_transformer,
            )

            # Surrounding buildings are common to every scenario and saved once.
            if scenario == 'baseline':
                assets['shared'] = save_outlines('shared', shared_outlines)
            assets[scenario] = save_outlines(scenario, design_outlines)
            print(f'Prepared building outlines: {scenario} ({len(design_outlines)} design rings)')

    manifest = {'version': 1, 'groups': assets}
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
