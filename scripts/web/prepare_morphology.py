"""Prepare browser imagery from the supplied coloured morphology GeoTIFFs."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from coordinates import Placement
from download_grids import GRID_DIRECTORY, ROOT
from pyproj import Transformer

SOURCE = ROOT / 'outputs/data/morphology/extended'
OUTPUT = ROOT / 'data/web/morphology'


def main():
    metadata = json.loads((SOURCE / 'metadata/legends.json').read_text())
    palettes = json.loads((ROOT / 'config/morphology_colours.json').read_text())
    coordinates = json.loads((ROOT / 'config/merwelab_coordinates.json').read_text())
    placement = Placement(coordinates['RD_origin'], GRID_DIRECTORY)
    horizontal = Transformer.from_pipeline(
        placement.horizontal_pipeline + '+step +proj=unitconvert +xy_in=rad +xy_out=deg'
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    layers = []

    for key, legend in metadata['layers'].items():
        group, name = key.split('/', 1)
        directory = {'V1': 'scenario_a', 'V2': 'scenario_b', 'Existing': 'baseline'}.get(group, group)
        source = SOURCE / directory / 'imagery' / f'{name}.tif'
        info = json.loads(subprocess.check_output(['gdalinfo', '-json', str(source)]))
        transform = info['geoTransform']
        width, height = info['size']
        west, north = transform[0], transform[3]
        east = west + width * transform[1]
        south = north + height * transform[5]
        longitude, latitude = horizontal.transform([west, west, east, east], [south, north, south, north])
        bounds = [min(longitude), min(latitude), max(longitude), max(latitude)]

        with tempfile.TemporaryDirectory(prefix='merwelab-morphology-') as temporary:
            warped = Path(temporary) / 'map.tif'
            image = Path(temporary) / 'map.png'
            pipeline = placement.horizontal_pipeline + '+step +proj=unitconvert +xy_in=rad +xy_out=deg'
            subprocess.run([
                'gdalwarp', '--config', 'GDAL_PAM_ENABLED', 'NO', '-q', '-overwrite',
                '-s_srs', 'EPSG:28992', '-t_srs', 'OGC:CRS84', '-ct', pipeline,
                '-te', *map(str, bounds), '-ts', '1800', '0',
                '-r', 'near', '-srcalpha', '-dstalpha', str(source), str(warped),
            ], check=True)
            subprocess.run([
                'gdal_translate', '--config', 'GDAL_PAM_ENABLED', 'NO', '-q',
                '-of', 'PNG', str(warped), str(image),
            ], check=True)
            content = image.read_bytes()

        digest = hashlib.sha256(content).hexdigest()
        filename = f'{directory}-{name}-{digest[:12]}.png'
        (OUTPUT / filename).write_bytes(content)
        legend['gradient'] = palettes.get(legend.get('cmap'))
        layers.append({
            'id': key,
            'indicator': name,
            'scenario': directory,
            'url': f'/web/morphology/{filename}',
            'bounds': bounds,
            'legend': legend,
            'source': source.relative_to(ROOT).as_posix(),
            'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        })

    manifest = {
        'version': 1,
        'kind': 'rendered-imagery',
        'layers': layers,
        'notes': metadata['notes'],
    }
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Prepared {len(layers)} morphology maps; original TIFFs unchanged.')


if __name__ == '__main__':
    main()
