import hashlib
import gzip
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from pyproj import Geod, Transformer

from coordinates import Placement
from download_grids import GRID_DIRECTORY, ROOT
from prepare_terrain import read_raster


OUTPUT = ROOT / 'data/web/wind'


def binary_asset(folder, name, content, suffix='bin'):
    if suffix in ('bin', 'json'):
        content = gzip.compress(content, compresslevel=6, mtime=0)
        suffix += '.gz'
    digest = hashlib.sha256(content).hexdigest()
    filename = f'{name}-{digest[:12]}.{suffix}'
    (folder / filename).write_bytes(content)
    return f'/web/wind/{folder.name}/{filename}'


def warp(source, destination, placement, bounds, width, height):
    pipeline = placement.horizontal_pipeline + '+step +proj=unitconvert +xy_in=rad +xy_out=deg'
    subprocess.run([
        'gdalwarp', '--config', 'GDAL_PAM_ENABLED', 'NO', '-q', '-overwrite',
        '-s_srs', 'EPSG:28992', '-t_srs', 'OGC:CRS84', '-ct', pipeline,
        '-te', *map(str, bounds), '-ts', str(width), str(height),
        '-r', 'near', '-srcnodata', '-9999', '-dstnodata', '-9999', str(source), str(destination),
    ], check=True)


def rgba_image(folder, name, rgba, temporary):
    raw = temporary / 'rgba.bin'
    height, width, _ = rgba.shape
    np.moveaxis(rgba, -1, 0).astype(np.uint8).tofile(raw)
    raw.with_suffix('.hdr').write_text(f'ENVI\nsamples = {width}\nlines = {height}\nbands = 4\nheader offset = 0\nfile type = ENVI Standard\ndata type = 1\ninterleave = bsq\nbyte order = 0\n')
    png = temporary / 'image.png'
    subprocess.run(['gdal_translate', '--config', 'GDAL_PAM_ENABLED', 'NO', '-q', '-of', 'PNG', str(raw), str(png)], check=True)
    return binary_asset(folder, name, png.read_bytes(), 'png')


def terrain_clearance(lon, lat, terrain):
    metadata, heights = terrain
    west, south, east, north = metadata['bounds']
    x = (lon - west) / (east - west) * (metadata['width'] - 1)
    y = (north - lat) / (north - south) * (metadata['height'] - 1)
    if np.any((x < 0) | (x > metadata['width'] - 1) | (y < 0) | (y > metadata['height'] - 1)):
        raise ValueError('Display terrain does not cover the wind surface')
    col = np.minimum(x.astype(int), metadata['width'] - 2)
    row = np.minimum(y.astype(int), metadata['height'] - 2)
    dx, dy = x - col, y - row
    return (heights[row, col] * (1 - dx) * (1 - dy) + heights[row, col + 1] * dx * (1 - dy)
            + heights[row + 1, col] * (1 - dx) * dy + heights[row + 1, col + 1] * dx * dy) + 1.5


def mesh_asset(folder, heights, bounds, placement, terrain):
    height, width = heights.shape
    rows = np.linspace(0, height, int(np.ceil(height / 2)) + 1)
    cols = np.linspace(0, width, int(np.ceil(width / 2)) + 1)
    cc, rr = np.meshgrid(cols, rows)
    sample_r = np.minimum(np.floor(rr).astype(int), height - 1)
    sample_c = np.minimum(np.floor(cc).astype(int), width - 1)
    nap = heights[sample_r, sample_c]
    valid = np.isfinite(nap) & (nap != -9999)
    lon = bounds[0] + cc / width * (bounds[2] - bounds[0])
    lat = bounds[3] - rr / height * (bounds[3] - bounds[1])
    horizontal = Transformer.from_pipeline(placement.horizontal_pipeline + '+step +proj=unitconvert +xy_in=rad +xy_out=deg')
    rd_x, rd_y = horizontal.transform(lon.ravel(), lat.ravel(), direction='INVERSE', errcheck=True)
    points = np.column_stack((rd_x, rd_y, np.where(valid, nap + 1.5, 0).ravel()))
    ecef = placement.transformer.transform(*points.T, errcheck=True)
    geographic = Transformer.from_crs(4978, 4979, always_xy=True)
    true_lon, true_lat, ellipsoid = geographic.transform(*ecef, errcheck=True)
    # Display draping is independent of the original CFD sampling heights.
    floor = terrain_clearance(np.asarray(true_lon), np.asarray(true_lat), terrain)
    display_height = np.where(valid.ravel(), np.maximum(ellipsoid, floor), floor)
    to_ecef = Transformer.from_crs(4979, 4978, always_xy=True)
    display_ecef = np.column_stack(to_ecef.transform(true_lon, true_lat, display_height, errcheck=True))
    positions = ((display_ecef - placement.origin_ecef) @ placement.axes).astype('<f4')
    st = np.column_stack((np.clip(cc.ravel() / width, 0.5 / width, 1 - 0.5 / width),
                          np.clip(1 - rr.ravel() / height, 0.5 / height, 1 - 0.5 / height))).astype('<f4')
    ids = np.arange(cc.size, dtype=np.uint32).reshape(cc.shape)
    a, b, c, d = ids[:-1, :-1], ids[:-1, 1:], ids[1:, :-1], ids[1:, 1:]
    indices = np.stack((a, c, b, b, c, d), axis=-1).astype('<u4').ravel()
    return {
        'positions': binary_asset(folder, 'surface-positions', positions.tobytes()),
        'st': binary_asset(folder, 'surface-st', st.tobytes()),
        'indices': binary_asset(folder, 'surface-indices', indices.tobytes()),
        'vertexCount': len(positions), 'indexCount': len(indices),
    }


def main():
    config = json.loads((ROOT / 'config/merwelab_coordinates.json').read_text())
    placement = Placement(config['RD_origin'], GRID_DIRECTORY)
    geographic = Transformer.from_crs(4978, 4979, always_xy=True)
    terrain_metadata = json.loads((ROOT / 'data/web/terrain/manifest.json').read_text())
    terrain_url = terrain_metadata['scenarios']['baseline']['url']
    terrain_heights = np.fromfile(ROOT / 'data/web' / terrain_url.removeprefix('/web/'), dtype='<f4').reshape(terrain_metadata['height'], terrain_metadata['width'])
    terrain = terrain_metadata, terrain_heights
    scenarios = {}
    common_bounds = None
    for scenario in ('baseline', 'scenario_a', 'scenario_b'):
        source = ROOT / f'outputs/data/wind/app/{scenario}'
        metadata = json.loads((source / 'metadata.json').read_text())
        west, south, east, north = metadata['bounds_rd']
        points = np.array([[west, south, 0], [west, north, 0], [east, south, 0], [east, north, 0]])
        lon, lat, _ = geographic.transform(*placement.transformer.transform(*points.T, errcheck=True))
        bounds = [min(lon), min(lat), max(lon), max(lat)]
        if common_bounds is None:
            common_bounds = bounds
        elif not np.allclose(bounds, common_bounds, atol=1e-9, rtol=0):
            raise ValueError('Wind cases must use the same display grid')
        geod = Geod(ellps='WGS84')
        width = int(np.ceil(geod.inv(bounds[0], (bounds[1] + bounds[3]) / 2, bounds[2], (bounds[1] + bounds[3]) / 2)[2]))
        height = int(np.ceil(geod.inv(bounds[0], bounds[1], bounds[0], bounds[3])[2]))
        folder = OUTPUT / scenario
        folder.mkdir(parents=True, exist_ok=True)
        metrics = {}
        with tempfile.TemporaryDirectory(prefix='merwelab-web-wind-') as directory:
            temporary = Path(directory)
            warped = temporary / 'warped.tif'
            warp(source / 'ground_nap.tif', warped, placement, bounds, width, height)
            ground, _, _ = read_raster(warped, temporary)
            mesh = mesh_asset(folder, ground, bounds, placement, terrain)
            for key, info in metadata['metrics'].items():
                warp(source / info['file'], warped, placement, bounds, width, height)
                values, _, _ = read_raster(warped, temporary)
                valid = np.isfinite(values) & (values != -9999)
                low, high = info['range']
                indices = np.rint(np.clip((values - low) / (high - low), 0, 1) * 255).astype(np.uint8)
                rgba = np.array(info['colours'], dtype=np.uint8)[indices]
                rgba[~valid, 3] = 0
                metrics[key] = {
                    'label': info['label'], 'units': info['units'], 'range': info['range'],
                    'colours': ['#' + ''.join(f'{v:02x}' for v in colour[:3]) for colour in info['colours']],
                    'image': rgba_image(folder, key, rgba, temporary),
                    'values': binary_asset(folder, key, values.astype('<f4').tobytes()),
                    'rawMaximum': info['maximum'], 'outsideDisplayRange': info['outside_display_range'],
                }
        overlays = {}
        arrows = json.loads((source / 'arrows.json').read_text())
        origins = np.asarray(arrows['points'])
        tips = origins.copy()
        tips[:, :2] += np.asarray(arrows['velocity_rd'])[:, :2] * arrows['arrow_scale_seconds']
        starts, ends = placement.to_local(origins), placement.to_local(tips)
        arrow_lines = [{'points': [start.round(5).tolist(), end.round(5).tolist()], 'speed': [speed, speed]} for start, end, speed in zip(starts, ends, arrows['speed'])]
        overlays['arrows'] = binary_asset(folder, 'arrows', json.dumps({'lines': arrow_lines}, separators=(',', ':')).encode(), 'json')
        for key in ('streamlines_2d', 'streamlines_3d'):
            lines = json.loads((source / f'{key}.json').read_text())['lines']
            for line in lines:
                line['points'] = placement.to_local(np.asarray(line['points'])).round(5).tolist()
            overlays[key] = binary_asset(folder, key, json.dumps({'lines': lines}, separators=(',', ':')).encode(), 'json')
        scenarios[scenario] = {'iteration': metadata['iteration'], 'width': width, 'height': height, 'bounds': bounds, 'mesh': mesh, 'metrics': metrics, 'overlays': overlays, 'quality': metadata['quality']}
        print(f'Prepared web wind assets: {scenario}', flush=True)
    manifest = {
        'version': 1, 'originEcef': placement.origin_ecef.tolist(), 'scenarios': scenarios,
        'windFromDegrees': 240, 'referenceSpeed': 16, 'referenceHeight': 60, 'samplingHeight': 1.5,
        'notes': ['Fixed steady RANS results; not live weather or annual wind comfort.', 'Scalar grids are reprojected with nearest sampling; no-data remains transparent.', 'A continuous 2 m display mesh shares vertices across all cells and drapes at least 1.5 m above shared AHN terrain, rising to original CFD ground plus 1.5 m where higher. Geometry spans missing ground samples; scalar missing-data transparency alone determines coverage. Display slopes bridge ground steps. Values remain sampled 1.5 m above original CFD ground/water and are not resampled vertically.', '2D lines follow horizontal flow at pedestrian height; 3D lines follow the mean three-dimensional field.', 'Pressure is kinematic m²/s², not Pa. Raw extremes are retained for review.'],
    }
    temporary = OUTPUT / 'manifest.json.tmp'
    temporary.write_text(json.dumps(manifest, indent=2) + '\n')
    temporary.replace(OUTPUT / 'manifest.json')


if __name__ == '__main__':
    main()
