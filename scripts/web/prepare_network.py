"""Prepare saved route-optimization results for the app without rerunning search."""
import ast
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

from download_grids import ROOT
from network_geometry import NetworkPlacement

sys.path.insert(0, str(ROOT))
from analysis.network.optimization.config import WEIGHT_SETS  # noqa: E402

SOURCE = ROOT / 'data/network'
OUTPUT = ROOT / 'data/web/network'
VARIANTS = [('balanced', 'Balanced'), ('access_first', 'Accessibility first'),
            ('green_first', 'Green first'), ('no_wind', 'Without wind')]
INDICATORS = ('access', 'detour', 'wind', 'car', 'green_loss', 'cost')


def read_features(path, layer):
    command = ['ogr2ogr', '-f', 'GeoJSON', '/vsistdout/', str(path), layer]
    try:
        content = subprocess.check_output(command, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(error.stderr.decode(errors='replace').strip()) from None

    data = json.loads(content)
    if data.get('type') != 'FeatureCollection' or not data.get('features'):
        raise ValueError(f'Missing features in {path.name}: {layer}')
    return data['features']


def read_table(path):
    with path.open(newline='', encoding='utf-8') as source:
        return list(csv.DictReader(source))


def path_length(feature):
    coordinates = feature['geometry']['coordinates']
    return sum(math.dist(a[:2], b[:2]) for a, b in zip(coordinates, coordinates[1:]))


def select_saved_result(features, table):
    built = sorted({feature['properties']['seg_id'] for feature in features
                    if feature['properties']['use'] != 'not built'
                    and feature['properties']['kind'] not in ('quay', 'exit')})
    car_paths = [feature for feature in features if feature['properties']['use'] == 'car + walk']
    car_length = sum(path_length(feature) for feature in car_paths)
    candidates = [row for row in table if row['method'] == 'greedy' and sorted(row['built'].split()) == built]
    candidates = [row for row in candidates if math.isclose(float(row['car']), car_length, abs_tol=0.01)]
    if not candidates:
        raise ValueError('The saved network does not match any greedy result row')

    # main.py writes the greedy network to GPKG, even when the CSV also contains
    # an exhaustive-search result. Select the row matching that saved geometry.
    result = min(candidates, key=lambda row: float(row['score']))
    ramp = list(ast.literal_eval(result['ramp']))
    endpoints = [point for feature in car_paths for point in
                 (feature['geometry']['coordinates'][0], feature['geometry']['coordinates'][-1])]
    if not any(math.dist(ramp, point[:2]) < 0.2 for point in endpoints):
        raise ValueError('Garage ramp does not meet the saved car route')

    return result, built, ramp


def prepare_paths(features, placement, deck, pavement):
    paths = []
    for index, feature in enumerate(features):
        properties = feature['properties']
        if properties['use'] not in ('walk + bike', 'car + walk', 'not built'):
            raise ValueError('Unknown route use')

        paths.append({
            'type': 'Feature',
            'id': f'path-{index}',
            'properties': {
                'layer': 'path', **properties,
                'built': properties['use'] != 'not built',
                'length': round(path_length(feature), 3),
            },
            'geometry': placement.geometry(feature['geometry'], deck, pavement, properties['kind'] == 'bridge'),
        })
    return paths


def prepare_points(entrances, ramp, placement, deck, pavement):
    points = []
    for index, feature in enumerate(entrances):
        points.append({
            'type': 'Feature', 'id': f'entrance-{index}',
            'properties': {'layer': 'entrance', 'building_id': feature['properties']['building_id']},
            'geometry': placement.geometry(feature['geometry'], deck, pavement),
        })

    points.append({
        'type': 'Feature', 'id': 'garage-ramp', 'properties': {'layer': 'garage_ramp'},
        'geometry': placement.geometry({'type': 'Point', 'coordinates': ramp}, deck, pavement),
    })
    return points


def write_asset(stem, content, extension):
    name = f'{stem}-{hashlib.sha256(content).hexdigest()[:12]}.{extension}'
    (OUTPUT / name).write_bytes(content)
    return f'/web/network/{name}'


def feature_bounds(features):
    points = []
    for feature in features:
        geometry = feature['geometry']
        if geometry['type'] == 'Point':
            points.append(geometry['coordinates'])
        else:
            points.extend(geometry['coordinates'])
    return [min(point[0] for point in points), min(point[1] for point in points),
            max(point[0] for point in points), max(point[1] for point in points)]


def prepare_variant(scenario, letter, variant, placement, entrances, pavement):
    stem = f'{letter}_{variant}_bridge'
    network_path = SOURCE / 'output' / f'network_{stem}.gpkg'
    result_path = SOURCE / 'output' / f'results_{stem}.csv'
    features = read_features(network_path, 'network')
    result, built, ramp = select_saved_result(features, read_table(result_path))
    deck = placement.deck_height(scenario)

    prepared = prepare_paths(features, placement, deck, pavement)
    prepared.extend(prepare_points(entrances, ramp, placement, deck, pavement))
    content = json.dumps({'type': 'FeatureCollection', 'features': prepared}, allow_nan=False).encode()
    car_trips = max(feature['properties']['car_trips_per_day'] for feature in features)
    bridge = any(feature['properties']['kind'] == 'bridge' and feature['properties']['use'] != 'not built'
                 for feature in features)

    figure_path = SOURCE / 'output' / f'network_{stem}.png'
    entry = {
        'url': write_asset(f'{scenario}-{variant}', content, 'geojson'),
        'figure': write_asset(f'{scenario}-{variant}', figure_path.read_bytes(), 'png'),
        'bounds': feature_bounds(prepared),
        'summary': {
            'method': 'greedy', 'built': built, 'rampRd': ramp,
            'score': float(result['score']), 'weights': WEIGHT_SETS[variant],
            'carTripsPerDay': car_trips, 'bridgeBuilt': bridge,
            'indicators': {key: float(result[key]) for key in INDICATORS},
        },
        'sources': [{'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                    for path in (network_path, result_path)],
    }
    return entry, prepared


def prepare_baseline():
    rows = read_table(SOURCE / 'baseline/pier_accessibility.csv')
    accessibility = [{'facility': row['facility'], 'meanDistance': float(row['mean_m']),
                      'maximumDistance': float(row['max_m']), 'walkMinutes': float(row['mean_walk_min'])}
                     for row in rows]
    figures = []
    for name, label in [('walk_time_metro', 'Walking time to metro'),
                        ('walk_time_supermarket', 'Walking time to supermarket'),
                        ('check_vs_cbs', 'Accessibility check against CBS')]:
        path = SOURCE / 'baseline' / f'{name}.png'
        figures.append({'label': label, 'url': write_asset(name, path.read_bytes(), 'png')})
    return {'accessibility': accessibility, 'figures': figures}


def prepare_sensitivity():
    results = []
    for name, parameter in [('sensitivity_cost_weight_A', 'cost_weight'),
                            ('sensitivity_bridge_cost_A', 'bridge_cost_factor')]:
        rows = read_table(SOURCE / 'output' / f'{name}.csv')
        results.append({
            'parameter': parameter,
            'rows': [{'value': float(row[parameter]), 'bridgeBuilt': row['bridge_built'] == 'True',
                      'built': row['built'].split(),
                      'indicators': {key: float(row[key]) for key in ('access', 'wind', 'car', 'green_loss', 'cost')}}
                     for row in rows],
        })
    return results


def pavement_polygons(features):
    polygons = []
    for feature in features:
        geometry = feature['geometry']
        if geometry['type'] == 'Polygon':
            polygons.append(geometry['coordinates'])
        elif geometry['type'] == 'MultiPolygon':
            polygons.extend(geometry['coordinates'])
        else:
            raise ValueError('Expected polygon design pavement')
    return polygons


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    placement = NetworkPlacement()
    scenarios = {}
    all_features = []

    for letter, scenario in [('A', 'scenario_a'), ('B', 'scenario_b')]:
        entrances = read_features(SOURCE / 'design/network_design.gpkg', f'entrances_{letter}')
        footprints = read_features(SOURCE / 'design' / f'scenario_{letter}_layout.gpkg', 'pavement')
        pavement = pavement_polygons(footprints)
        scenarios[scenario] = {}

        for variant, _ in VARIANTS:
            entry, features = prepare_variant(scenario, letter, variant, placement, entrances, pavement)
            scenarios[scenario][variant] = entry
            all_features.extend(features)

    all_paths = [feature for feature in all_features if feature['properties']['layer'] == 'path']
    ranges = {}
    for metric in ('wind', 'residents_walking', 'car_trips_per_day'):
        values = [feature['properties'][metric] for feature in all_paths]
        ranges[metric] = [min(values), max(values)]

    manifest = {
        'version': 1, 'scenarios': scenarios,
        'variants': [{'id': key, 'label': label} for key, label in VARIANTS],
        'bounds': feature_bounds(all_features), 'ranges': ranges,
        'baseline': prepare_baseline(), 'sensitivity': prepare_sensitivity(),
        'placementSources': [
            {'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in (SOURCE / 'design/network_design.gpkg',
                         SOURCE / 'design/scenario_A_layout.gpkg', SOURCE / 'design/scenario_B_layout.gpkg',
                         ROOT / 'data/web/terrain/manifest.json', ROOT / 'data/web/surfaces/manifest.json')
        ],
        'notes': ['Saved design alternatives, not live route calculation.',
                  'Cost and scores are relative within each scenario; they are not comparable monetary costs.',
                  'Wind is a relative indicator for the 240-degree simulation direction.',
                  'Walking assignments and car trips are model estimates, not measured traffic.',
                  'Display heights clear prepared terrain and proposal pavement by 0.2 m; analytical lengths are unchanged.'],
    }
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    print('Prepared eight saved route alternatives, baseline accessibility and sensitivity results.')


if __name__ == '__main__':
    main()
