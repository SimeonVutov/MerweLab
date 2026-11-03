"""Prepare class-preserving imagery, cell samples and area summaries for Cesium.

Run with the scripts/web environment; GDAL command-line tools must be on PATH.
Original TIFFs and the trained model are never modified or rerun here.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
from pyproj import Transformer

from coordinates import Placement
from download_grids import GRID_DIRECTORY, ROOT

sys.path.insert(0, str(ROOT))
from analysis.land_use.config import (  # noqa: E402
    CLASS_NAMES, LAND_USE_PATH, PREDICTED_MAP_PATH, SIMPLIFIED_MAP_PATH,
    SIMPLIFY_LABELS_MAP,
)

OUTPUT = ROOT / 'data/web/land-use'
NO_DATA = 255
COLOURS = ['#9a9489', '#bda66b', '#cd8b76', '#9276af', '#5b9970', '#5797b4']
MAPS = [('existing', 'Existing land use'), ('optimized', 'Optimized proposal'), ('changes', 'Changed cells')]


def run_gdal(command):
    try:
        return subprocess.check_output(command, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as error:
        message = error.stderr.decode(errors='replace').strip()
        raise RuntimeError(f'{command[0]} failed: {message}') from None


def read_raster(path, temporary):
    metadata = json.loads(run_gdal(['gdalinfo', '-json', str(path)]))
    width, height = metadata['size']
    if len(metadata['bands']) != 1:
        raise ValueError(f'Expected one class band in {path.name}')

    authority = run_gdal(['gdalsrsinfo', '-o', 'epsg', str(path)]).decode()
    if 'EPSG:28992' not in authority:
        raise ValueError(f'Expected RD New coordinates in {path.name}')

    raw = temporary / f'{path.stem}.bin'
    run_gdal(['gdal_translate', '-q', '-of', 'ENVI', '-ot', 'Float64', str(path), str(raw)])
    values = np.fromfile(raw, dtype=np.float64).reshape(height, width)
    return metadata, values


def validate_sources(raw, existing, optimized):
    reference, original_values = raw
    for metadata, _ in (existing, optimized):
        if metadata['size'] != reference['size']:
            raise ValueError('Land-use maps must use the same dimensions')
        if not np.allclose(metadata['geoTransform'], reference['geoTransform'], rtol=0, atol=1e-8):
            raise ValueError('Land-use maps must use the same pixel grid')

    transform = reference['geoTransform']
    if transform[2] != 0 or transform[4] != 0 or transform[1] <= 0 or transform[5] >= 0:
        raise ValueError('Expected a north-up land-use grid')

    valid = np.isfinite(original_values)
    missing = reference['bands'][0].get('noDataValue')
    if missing is not None:
        valid &= original_values != missing

    for _, values in (existing, optimized):
        known = np.isin(values, range(len(CLASS_NAMES)))
        if np.any(valid & ~known):
            raise ValueError('Land-use map contains unknown or missing classes inside the source coverage')

    # Class zero is valid "Other". Only the original source identifies no-data.
    expected = np.full(original_values.shape, NO_DATA, dtype=np.uint8)
    for raw_code, class_code in SIMPLIFY_LABELS_MAP.items():
        expected[valid & (original_values == raw_code)] = class_code

    if np.any(valid & (expected != existing[1])):
        raise ValueError('Existing classes do not match the documented raw-code mapping')
    if not valid.any():
        raise ValueError('Land-use source contains no valid cells')

    return valid


def write_class_grid(path, values, transform, crs, palette=False):
    height, width = values.shape
    binary = path.with_suffix('.bin')
    values.astype(np.uint8).tofile(binary)

    dataset = ET.Element('VRTDataset', rasterXSize=str(width), rasterYSize=str(height))
    ET.SubElement(dataset, 'SRS').text = crs
    ET.SubElement(dataset, 'GeoTransform').text = ', '.join(map(str, transform))
    band = ET.SubElement(dataset, 'VRTRasterBand', dataType='Byte', band='1', subClass='VRTRawRasterBand')
    ET.SubElement(band, 'NoDataValue').text = str(NO_DATA)
    ET.SubElement(band, 'SourceFilename', relativeToVRT='1').text = binary.name
    ET.SubElement(band, 'ImageOffset').text = '0'
    ET.SubElement(band, 'PixelOffset').text = '1'
    ET.SubElement(band, 'LineOffset').text = str(width)

    if palette:
        ET.SubElement(band, 'ColorInterp').text = 'Palette'
        table = ET.SubElement(band, 'ColorTable')
        for code in range(NO_DATA + 1):
            colour = [0, 0, 0, 0]
            if code < len(COLOURS):
                colour = [int(COLOURS[code][offset:offset + 2], 16) for offset in (1, 3, 5)] + [255]
            ET.SubElement(table, 'Entry', **dict(zip(('c1', 'c2', 'c3', 'c4'), map(str, colour))))

    ET.ElementTree(dataset).write(path, encoding='utf-8', xml_declaration=True)


def geographic_placement(metadata):
    coordinates = json.loads((ROOT / 'config/merwelab_coordinates.json').read_text())
    placement = Placement(coordinates['RD_origin'], GRID_DIRECTORY)
    pipeline = placement.horizontal_pipeline + '+step +proj=unitconvert +xy_in=rad +xy_out=deg'
    transformer = Transformer.from_pipeline(pipeline)

    width, height = metadata['size']
    west, dx, _, north, _, dy = metadata['geoTransform']
    east, south = west + width * dx, north + height * dy
    longitude, latitude = transformer.transform([west, west, east, east], [south, north, south, north])
    bounds = [min(longitude), min(latitude), max(longitude), max(latitude)]
    return pipeline, bounds


def reproject_classes(values, metadata, placement, temporary, name):
    pipeline, bounds = placement
    source = temporary / f'{name}.vrt'
    write_class_grid(source, values, metadata['geoTransform'], 'EPSG:28992')

    warped = temporary / f'{name}-geographic.tif'
    width, height = metadata['size']
    run_gdal([
        'gdalwarp', '--config', 'GDAL_PAM_ENABLED', 'NO', '-q', '-overwrite',
        '-t_srs', 'OGC:CRS84', '-ct', pipeline, '-te', *map(str, bounds),
        '-ts', str(width * 2), str(height * 2), '-r', 'near',
        '-srcnodata', str(NO_DATA), '-dstnodata', str(NO_DATA), str(source), str(warped),
    ])
    binary = temporary / f'{name}-geographic.bin'
    run_gdal(['gdal_translate', '-q', '-of', 'ENVI', '-ot', 'Byte', str(warped), str(binary)])
    return np.fromfile(binary, dtype=np.uint8).reshape(height * 2, width * 2)


def write_asset(stem, content, extension):
    digest = hashlib.sha256(content).hexdigest()[:12]
    filename = f'{stem}-{digest}.{extension}'
    (OUTPUT / filename).write_bytes(content)
    return f'/web/land-use/{filename}'


def export_map(name, label, values, bounds, temporary):
    height, width = values.shape
    west, south, east, north = bounds
    transform = [west, (east - west) / width, 0, north, 0, -(north - south) / height]
    source = temporary / f'{name}-colours.vrt'
    image = temporary / f'{name}.png'
    write_class_grid(source, values, transform, 'OGC:CRS84', palette=True)

    run_gdal([
        'gdal_translate', '--config', 'GDAL_PAM_ENABLED', 'NO', '-q',
        '-of', 'PNG', '-expand', 'rgba', str(source), str(image),
    ])
    return {
        'id': name,
        'label': label,
        'image': write_asset(name, image.read_bytes(), 'png'),
        'codes': write_asset(name, values.tobytes(), 'uint8'),
    }


def area_summary(existing, optimized, valid, transform):
    cell_area = abs(transform[1] * transform[5])
    existing_counts = np.bincount(existing[valid].astype(int), minlength=len(CLASS_NAMES))
    optimized_counts = np.bincount(optimized[valid].astype(int), minlength=len(CLASS_NAMES))
    changed = valid & (existing != optimized)

    return {
        'areaSquareMetres': int(valid.sum()) * cell_area,
        'changedAreaSquareMetres': int(changed.sum()) * cell_area,
        'cellAreaSquareMetres': cell_area,
        'classes': [
            {'code': code, 'existingArea': int(existing_counts[code]) * cell_area,
             'optimizedArea': int(optimized_counts[code]) * cell_area}
            for code in range(len(CLASS_NAMES))
        ],
    }


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='merwelab-land-use-') as directory:
        temporary = Path(directory)
        raw = read_raster(LAND_USE_PATH, temporary)
        existing = read_raster(SIMPLIFIED_MAP_PATH, temporary)
        optimized = read_raster(PREDICTED_MAP_PATH, temporary)
        valid = validate_sources(raw, existing, optimized)
        placement = geographic_placement(raw[0])

        # Warp classes with nearest-neighbour sampling. Interpolation would
        # invent class numbers and blur categorical boundaries.
        grids = {}
        for name, raster in (('existing', existing), ('optimized', optimized)):
            masked = np.where(valid, raster[1], NO_DATA).astype(np.uint8)
            grids[name] = reproject_classes(masked, raw[0], placement, temporary, name)

        grids['changes'] = np.where(grids['existing'] != grids['optimized'], grids['optimized'], NO_DATA)
        maps = [export_map(name, label, grids[name], placement[1], temporary) for name, label in MAPS]
        height, width = grids['existing'].shape

    manifest = {
        'version': 1,
        'scope': 'shared-proposal',
        'bounds': placement[1],
        'width': width,
        'height': height,
        'noData': NO_DATA,
        'classes': [{'code': code, 'label': name.capitalize(), 'colour': COLOURS[code]} for code, name in enumerate(CLASS_NAMES)],
        'maps': maps,
        'summary': area_summary(existing[1], optimized[1], valid, raw[0]['geoTransform']),
        'sources': [
            {'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in (LAND_USE_PATH, SIMPLIFIED_MAP_PATH, PREDICTED_MAP_PATH)
        ],
        'notes': ['One shared optimized proposal was supplied, not separate V1/V2 predictions.',
                  'Changed-cell colours show the proposed class; unchanged cells are transparent.',
                  'Areas use original RD cells; browser pixels do not increase analytical resolution.'],
    }
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    print(f'Prepared {len(maps)} land-use maps from unchanged source TIFFs.')


if __name__ == '__main__':
    main()
