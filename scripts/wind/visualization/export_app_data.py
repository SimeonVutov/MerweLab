import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault('MPLCONFIGDIR', '/tmp/merwelab-wind-matplotlib')

import numpy as np
from osgeo import gdal, osr
from matplotlib import colormaps

from app_sampling import check_memory, ground_surface, probe, read_flow, to_cfd_rd
from app_streamlines import streamlines_2d, streamlines_3d
from coordinates import placement
import settings


ITERATIONS = {'baseline': 500, 'scenario_a': 800, 'scenario_b': 800}
OUTPUT = settings.ROOT / 'outputs/data/wind/app'
METRICS = {
    'speed': {'label': 'Wind speed', 'units': 'm/s', 'range': [0, 14], 'palette': 'viridis'},
    'turbulence': {'label': 'Turbulent kinetic energy k', 'units': 'm²/s²', 'range': [0, 10], 'palette': 'magma'},
    'pressure': {'label': 'Kinematic pressure p', 'units': 'm²/s²', 'range': [-30, 30], 'palette': 'RdBu_r'},
}


def write_tiff(path, values, bounds, scenario, iteration, units):
    if values.ndim == 2:
        values = values[..., None]
    height, width, bands = values.shape
    raster = gdal.GetDriverByName('GTiff').Create(str(path), width, height, bands, gdal.GDT_Float32, ['COMPRESS=DEFLATE', 'PREDICTOR=3', 'TILED=YES'])
    raster.SetGeoTransform([bounds[0], 1, 0, bounds[3], 0, -1])
    reference = osr.SpatialReference()
    reference.ImportFromEPSG(28992)
    raster.SetProjection(reference.ExportToWkt())
    raster.SetMetadata({
        'scenario': scenario, 'iteration': str(iteration), 'units': units,
        'height_above_source_ground_m': '1.5', 'wind_from_true_degrees': '240',
        'inlet_reference_speed_m_s': '16', 'inlet_reference_height_m': '60',
        'assessment': 'Saved steady RANS; not live wind, gusts or annual comfort',
        'sampling': 'Cell-to-point interpolation, then 1 m RD grid at 1.5 m above original CFD ground/water',
    })
    for band in range(bands):
        raster.GetRasterBand(band + 1).SetNoDataValue(-9999)
        raster.GetRasterBand(band + 1).WriteArray(values[..., band])
    raster = None


def export(scenario):
    gdal.UseExceptions()
    iteration = ITERATIONS[scenario]
    grounds = [ground_surface(key) for key in ITERATIONS]
    bounds = np.array([min(b[0] for _, b in grounds), min(b[1] for _, b in grounds), max(b[2] for _, b in grounds), max(b[3] for _, b in grounds)])
    ground = grounds[list(ITERATIONS).index(scenario)][0]
    del grounds
    x = np.arange(bounds[0] + 0.5, bounds[2], 1)
    y = np.arange(bounds[3] - 0.5, bounds[1], -1)
    xx, yy = np.meshgrid(x, y)
    points = to_cfd_rd(np.column_stack((xx.ravel(), yy.ravel(), np.zeros(xx.size))))
    points[:, 2] = 0
    heights = probe(ground, points)
    points[:, 2] = heights['ground_z'] + 1.5
    on_ground = heights['vtkValidPointMask'].astype(bool)
    flow = read_flow(scenario, iteration)
    print(f'Sampling {len(points):,} pedestrian positions...', flush=True)
    samples = probe(flow, points)
    check_memory()
    valid = on_ground & samples['vtkValidPointMask'].astype(bool) & np.isfinite(samples['U']).all(axis=1)
    fx, fy, _ = placement()['flow_unit_vector_RD']
    velocity = samples['U'].copy()
    velocity[:, :2] = velocity[:, :2] @ np.array([[fx, fy], [-fy, fx]])
    speed = np.linalg.norm(velocity, axis=1)
    shape = (len(y), len(x))
    values = {'speed': speed, 'turbulence': samples['k'], 'pressure': samples['p']}
    target = OUTPUT / scenario
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.export-', dir=target) as temporary:
        staging = Path(temporary)
        metrics = {}
        for key, value in values.items():
            good = valid & np.isfinite(value)
            if key == 'turbulence':
                good &= value >= 0
            masked = np.where(good, value, -9999).reshape(shape)
            write_tiff(staging / f'{key}_1p5m.tif', masked, bounds, scenario, iteration, METRICS[key]['units'])
            metrics[key] = {**METRICS[key], 'file': f'{key}_1p5m.tif', 'valid_samples': int(good.sum()), 'minimum': float(value[good].min()), 'maximum': float(value[good].max()), 'outside_display_range': int(np.count_nonzero(good & ((value < METRICS[key]['range'][0]) | (value > METRICS[key]['range'][1])))), 'colours': (colormaps[METRICS[key]['palette']](np.linspace(0, 1, 256)) * 255).astype(int).tolist()}
        ground_nap = np.where(on_ground, heights['ground_z'] + placement()['RD_origin'][2], -9999).reshape(shape)
        write_tiff(staging / 'ground_nap.tif', ground_nap, bounds, scenario, iteration, 'm NAP')
        write_tiff(staging / 'velocity_rd_1p5m.tif', np.where(valid[:, None], velocity, -9999).reshape(*shape, 3), bounds, scenario, iteration, 'm/s; bands RD east, RD north, up')
        stride = 30
        indices = np.arange(len(points)).reshape(shape)[::stride, ::stride].ravel()
        indices = indices[valid[indices]]
        rd_points = np.column_stack((xx.ravel(), yy.ravel(), ground_nap.ravel() + 1.5))
        arrows = {'crs': 'EPSG:7415', 'points': rd_points[indices].round(5).tolist(), 'velocity_rd': velocity[indices].round(6).tolist(), 'speed': speed[indices].round(6).tolist(), 'arrow_scale_seconds': 2}
        (staging / 'arrows.json').write_text(json.dumps(arrows, separators=(',', ':')))
        for file in list(staging.iterdir()):
            file.replace(target / file.name)
        print('Exporting 2D streamlines...', flush=True)
        lines_2d = streamlines_2d(velocity.reshape(*shape, 3), valid.reshape(shape), x, y, ground)
        print('Exporting 3D streamlines...', flush=True)
        lines_3d = streamlines_3d(flow, ground, bounds)
        for key, lines in [('streamlines_2d', lines_2d), ('streamlines_3d', lines_3d)]:
            (staging / f'{key}.json').write_text(json.dumps({'crs': 'EPSG:7415', 'lines': lines}, separators=(',', ':')))
        metadata = {
            'version': 1, 'scenario': scenario, 'iteration': iteration, 'bounds_rd': bounds.tolist(),
            'metrics': metrics, 'height_above_ground_m': 1.5, 'wind_from_true_degrees': 240,
            'inlet_reference_speed_m_s': 16, 'inlet_reference_height_m': 60,
            'streamlines_2d': len(lines_2d), 'streamlines_3d': len(lines_3d),
            'quality': {'speed_above_100_m_s': int(np.count_nonzero(valid & (speed > 100))), 'note': 'Raw extremes are retained and flagged; not a validated annual comfort assessment.'},
            'placement_sha256': hashlib.sha256(settings.PLACEMENT.read_bytes()).hexdigest(),
        }
        for file in staging.iterdir():
            file.replace(target / file.name)
        (target / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    del flow
    gc.collect()
    print(f'Completed {scenario}: {target}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=list(ITERATIONS) + ['all'], default='all')
    args = parser.parse_args()
    if args.scenario == 'all':
        for scenario in ITERATIONS:
            subprocess.run([sys.executable, __file__, '--scenario', scenario], check=True)
    else:
        export(args.scenario)


if __name__ == '__main__':
    main()
