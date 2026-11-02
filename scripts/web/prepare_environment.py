"""Prepare terrain colours and lightweight trees from the supplied 4.2 exports."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import numpy as np
from pyproj import Transformer

from coordinates import Placement
from download_grids import GRID_DIRECTORY, ROOT

OUTPUT = ROOT / 'data/web/environment'
TREE_SOURCE = ROOT / 'data/context/vegetation/GCS_FP_Trees_2.kmz'
ELEVATION_SOURCE = ROOT / 'data/context/elevation/GCS_FP_DTM_Elevation_Colours.tif'
COLLADA = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
KML = {'k': 'http://earth.google.com/kml/2.1'}


def write_asset(stem, content, extension):
    digest = hashlib.sha256(content).hexdigest()
    filename = f'{stem}-{digest[:12]}.{extension}'
    (OUTPUT / filename).write_bytes(content)
    return f'/web/environment/{filename}'


def local_axes(longitude, latitude):
    longitude, latitude = np.radians([longitude, latitude])
    return np.array([
        [-np.sin(longitude), -np.sin(latitude) * np.cos(longitude), np.cos(latitude) * np.cos(longitude)],
        [np.cos(longitude), -np.sin(latitude) * np.sin(longitude), np.cos(latitude) * np.sin(longitude)],
        [0, np.cos(latitude), np.sin(latitude)],
    ])


def validate_tree_conventions(model, geometry_document):
    # This exporter supplies metre-scale, Z-up geometry without node transforms.
    # Fail rather than silently misplace a future export with different conventions.
    if geometry_document.find('c:asset/c:up_axis', COLLADA).text != 'Z_UP':
        raise ValueError('Expected Z-up tree geometry')
    if float(geometry_document.find('c:asset/c:unit', COLLADA).get('meter')) != 1:
        raise ValueError('Expected tree coordinates in metres')
    for axis in ('heading', 'tilt', 'roll'):
        if float(model.find(f'k:Orientation/k:{axis}', KML).text) != 0:
            raise ValueError('Expected unrotated KML tree model')
    for axis in ('x', 'y', 'z'):
        if float(model.find(f'k:Scale/k:{axis}', KML).text) != 1:
            raise ValueError('Expected unscaled KML tree model')
    for node in geometry_document.findall('.//c:node', COLLADA):
        if node.find('c:instance_geometry', COLLADA) is not None and node.find('c:matrix', COLLADA) is not None:
            raise ValueError('Tree mesh node transforms need explicit handling')


def read_tree_shapes():
    with ZipFile(TREE_SOURCE) as archive:
        document = ET.fromstring(archive.read('GCS_FP_Trees_2.kml'))
        model = document.find('.//k:Model', KML)
        location = model.find('k:Location', KML)
        anchor = [float(location.find(f'k:{axis}', KML).text) for axis in ('longitude', 'latitude', 'altitude')]
        geometry_path = model.find('k:Link/k:href', KML).text
        geometry_document = ET.fromstring(archive.read(geometry_path))

    validate_tree_conventions(model, geometry_document)

    shapes = []
    for geometry in geometry_document.findall('.//c:geometry', COLLADA):
        positions = geometry.find("c:mesh/c:source[@name='position']/c:float_array", COLLADA)
        vertices = np.fromstring(positions.text, sep=' ').reshape(-1, 3)
        shapes.append((vertices.min(axis=0), vertices.max(axis=0)))

    return anchor, shapes


def read_terrain_grid():
    manifest = json.loads((ROOT / 'data/web/terrain/manifest.json').read_text())
    terrain_path = ROOT / 'data' / manifest['scenarios']['baseline']['url'].lstrip('/')
    heights = np.fromfile(terrain_path, dtype='<f4').reshape(manifest['height'], manifest['width'])
    return manifest, heights


def sample_terrain(longitude, latitude, terrain):
    manifest, heights = terrain
    west, south, east, north = manifest['bounds']
    core_west, core_south, core_east, core_north = manifest['coreBounds']
    if not (core_west <= longitude <= core_east and core_south <= latitude <= core_north):
        raise ValueError('Tree lies outside the numerical terrain core')

    column = (longitude - west) / (east - west) * (manifest['width'] - 1)
    row = (north - latitude) / (north - south) * (manifest['height'] - 1)
    left, top = int(column), int(row)
    column_fraction = column - left
    row_fraction = row - top
    interpolated_height = (
        heights[top, left] * (1 - column_fraction) * (1 - row_fraction)
        + heights[top, left + 1] * column_fraction * (1 - row_fraction)
        + heights[top + 1, left] * (1 - column_fraction) * row_fraction
        + heights[top + 1, left + 1] * column_fraction * row_fraction
    )
    return float(interpolated_height)



def tree_ground_position(centre, anchor_ecef, axes, geographic_transformer, terrain):
    centre_ecef = anchor_ecef + axes @ [centre[0], centre[1], 0]
    longitude, latitude, _ = geographic_transformer.transform(*centre_ecef)
    height = sample_terrain(longitude, latitude, terrain)
    return [longitude, latitude, height]


def locate_trees(anchor, shapes):
    geographic_transformer = Transformer.from_crs(4978, 4979, always_xy=True)
    geocentric_transformer = Transformer.from_crs(4979, 4978, always_xy=True)
    anchor_ecef = np.array(geocentric_transformer.transform(*anchor))
    axes = local_axes(*anchor[:2])
    terrain = read_terrain_grid()
    trees = {}

    # Trunks and crowns are separate meshes. Their common XY centre identifies
    # each tree; source heights are illustrative geometry, not measured heights.
    for minimum, maximum in shapes:
        centre = (minimum + maximum) / 2
        key = tuple(np.round(centre[:2], 2))
        if key not in trees:
            position = tree_ground_position(
                centre, anchor_ecef, axes, geographic_transformer, terrain,
            )
            trees[key] = {'position': position, 'shapes': []}
        trees[key]['shapes'].append((minimum, maximum))

    return list(trees.values())


def ellipsoid_mesh(radius, centre, segments=12, rings=8):
    vertices = []
    for row in range(rings + 1):
        latitude = -np.pi / 2 + np.pi * row / rings
        for column in range(segments):
            longitude = 2 * np.pi * column / segments
            direction = np.array([
                np.cos(latitude) * np.cos(longitude),
                np.cos(latitude) * np.sin(longitude),
                np.sin(latitude),
            ])
            vertices.append(centre + radius * direction)

    triangles = []
    for row in range(rings):
        for column in range(segments):
            lower = row * segments + column
            next_lower = row * segments + (column + 1) % segments
            upper = lower + segments
            next_upper = next_lower + segments
            if row > 0:
                triangles.append((lower, next_lower, upper))
            if row < rings - 1:
                triangles.append((next_lower, next_upper, upper))

    return np.array(vertices), np.array(triangles)


def trunk_mesh(radius, centre, segments=12):
    vertices = []
    for height in (-1, 1):
        for column in range(segments):
            angle = 2 * np.pi * column / segments
            vertices.append(centre + radius * [np.cos(angle), np.sin(angle), height])

    triangles = []
    for column in range(segments):
        following = (column + 1) % segments
        triangles.extend([(column, following, column + segments), (following, following + segments, column + segments)])
    for column in range(1, segments - 1):
        triangles.extend([(0, column + 1, column), (segments, segments + column, segments + column + 1)])

    return np.array(vertices), np.array(triangles)


def create_tree_shape(minimum, maximum, offset):
    radius = (maximum - minimum) / 2
    centre = offset + [0, 0, (minimum[2] + maximum[2]) / 2]
    if minimum[2] < 0.01:
        vertices, triangles = trunk_mesh(radius, centre)
        return vertices, triangles, [0.30, 0.20, 0.12, 1]

    vertices, triangles = ellipsoid_mesh(radius, centre)
    return vertices, triangles, [0.15, 0.37, 0.12, 1]


def triangle_attributes(vertices, triangles, colour):
    # glTF is Y-up; the georeferenced model frame is east/north/up.
    gltf_vertices = vertices[:, [0, 2, 1]] * [1, 1, -1]
    for triangle in triangles:
        points = gltf_vertices[triangle]
        normal = np.cross(points[1] - points[0], points[2] - points[0])
        normal_length = np.linalg.norm(normal)
        if normal_length < 1e-10:
            continue

        yield points, [normal / normal_length] * 3, [colour] * 3


def create_tile_attributes(trees, origin):
    geocentric = Transformer.from_crs(4979, 4978, always_xy=True)
    origin_ecef = np.array(geocentric.transform(*origin))
    axes = local_axes(*origin[:2])
    positions = []
    normals = []
    colours = []

    for tree in trees:
        tree_ecef = np.array(geocentric.transform(*tree['position']))
        offset = (tree_ecef - origin_ecef) @ axes
        for minimum, maximum in tree['shapes']:
            vertices, triangles, colour = create_tree_shape(minimum, maximum, offset)
            for points, face_normals, face_colours in triangle_attributes(vertices, triangles, colour):
                positions.extend(points)
                normals.extend(face_normals)
                colours.extend(face_colours)

    return [np.asarray(values, dtype='<f4') for values in (positions, normals, colours)]


def encode_vertex_buffers(attributes):
    binary = b''
    buffer_views = []
    accessors = []
    for index, values in enumerate(attributes):
        content = values.tobytes()
        buffer_views.append({
            'buffer': 0,
            'byteOffset': len(binary),
            'byteLength': len(content),
            'target': 34962,
        })
        accessor = {
            'bufferView': index,
            'componentType': 5126,
            'count': len(values),
            'type': f'VEC{values.shape[1]}',
        }
        if index == 0:
            accessor.update(min=values.min(axis=0).tolist(), max=values.max(axis=0).tolist())
        accessors.append(accessor)
        binary += content

    return binary, buffer_views, accessors


def encode_tree_glb(attributes):
    binary, buffer_views, accessors = encode_vertex_buffers(attributes)
    primitive = {
        'attributes': {'POSITION': 0, 'NORMAL': 1, 'COLOR_0': 2},
        'material': 0,
    }
    material = {'pbrMetallicRoughness': {'metallicFactor': 0, 'roughnessFactor': 1}}
    gltf = {
        'asset': {'version': '2.0', 'generator': 'MerweLab lightweight illustrative trees'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'mesh': 0}],
        'meshes': [{'primitives': [primitive]}],
        'materials': [material],
        'buffers': [{'byteLength': len(binary)}],
        'bufferViews': buffer_views,
        'accessors': accessors,
    }

    # GLB has a 12-byte header and two chunk headers. JSON must be padded to
    # a four-byte boundary; the float32 vertex buffers are already aligned.
    metadata = json.dumps(gltf, separators=(',', ':')).encode()
    metadata += b' ' * (-len(metadata) % 4)
    content = struct.pack('<4sII', b'glTF', 2, 28 + len(metadata) + len(binary))
    content += struct.pack('<I4s', len(metadata), b'JSON') + metadata
    content += struct.pack('<I4s', len(binary), b'BIN\0') + binary
    return content


def write_tree_tile(trees, tile_id):
    origin = trees[0]['position']
    attributes = create_tile_attributes(trees, origin)
    content = encode_tree_glb(attributes)
    url = write_asset(f'trees-{tile_id}', content, 'glb')

    centre = np.mean([tree['position'][:2] for tree in trees], axis=0).tolist()
    return {'url': url, 'origin': origin, 'centre': centre, 'count': len(trees)}


def prepare_trees():
    anchor, shapes = read_tree_shapes()
    trees = locate_trees(anchor, shapes)
    tiles = {}
    for tree in trees:
        longitude, latitude, _ = tree['position']
        key = f'{int(longitude * 150)}-{int(latitude * 250)}'
        tiles.setdefault(key, []).append(tree)

    prepared_tiles = [write_tree_tile(group, key) for key, group in tiles.items()]
    points = [tree['position'] for tree in trees]
    points_url = write_asset('tree-locations', json.dumps(points, separators=(',', ':')).encode(), 'json')
    return {
        'tiles': prepared_tiles,
        'locations': points_url,
        'count': len(trees),
        'source': TREE_SOURCE.relative_to(ROOT).as_posix(),
        'sourceSha256': hashlib.sha256(TREE_SOURCE.read_bytes()).hexdigest(),
        'notes': 'OSM-derived locations from the supplied Rhino model. Simplified illustrative crowns and trunks retain source dimensions; heights and crown sizes are not measurements. Bases follow the shared numerical terrain.',
    }


def elevation_bounds(pipeline):
    info = json.loads(subprocess.check_output(['gdalinfo', '-json', str(ELEVATION_SOURCE)]))
    transform = info['geoTransform']
    width, height = info['size']
    west, north = transform[0], transform[3]
    east = west + width * transform[1]
    south = north + height * transform[5]
    horizontal = Transformer.from_pipeline(pipeline)
    longitude, latitude = horizontal.transform([west, west, east, east], [south, north, south, north])
    return [min(longitude), min(latitude), max(longitude), max(latitude)]


def convert_elevation_image(bounds, pipeline):
    with tempfile.TemporaryDirectory(prefix='merwelab-elevation-') as temporary:
        warped = Path(temporary) / 'colours.tif'
        image = Path(temporary) / 'colours.png'
        subprocess.run([
            'gdalwarp', '--config', 'GDAL_PAM_ENABLED', 'NO', '-q', '-overwrite',
            '-s_srs', 'EPSG:28992', '-t_srs', 'OGC:CRS84', '-ct', pipeline,
            '-te', *map(str, bounds), '-ts', '1800', '0', '-r', 'bilinear',
            '-srcalpha', '-dstalpha', str(ELEVATION_SOURCE), str(warped),
        ], check=True)
        subprocess.run([
            'gdal_translate', '--config', 'GDAL_PAM_ENABLED', 'NO', '-q', '-of', 'PNG', str(warped), str(image),
        ], check=True)
        return write_asset('elevation-colours', image.read_bytes(), 'png')


def prepare_elevation(placement):
    pipeline = placement.horizontal_pipeline + '+step +proj=unitconvert +xy_in=rad +xy_out=deg'
    bounds = elevation_bounds(pipeline)
    url = convert_elevation_image(bounds, pipeline)

    return {
        'url': url,
        'bounds': bounds,
        'source': ELEVATION_SOURCE.relative_to(ROOT).as_posix(),
        'sourceSha256': hashlib.sha256(ELEVATION_SOURCE.read_bytes()).hexdigest(),
        'notes': 'Supplied rendered AHN elevation colours. No numerical colour legend was supplied; colours cannot provide exact height readings.',
    }


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    config = json.loads((ROOT / 'config/merwelab_coordinates.json').read_text())
    placement = Placement(config['RD_origin'], GRID_DIRECTORY)
    trees = prepare_trees()
    elevation = prepare_elevation(placement)

    manifest = {'version': 1, 'trees': trees, 'elevation': elevation}
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f"Prepared {trees['count']} trees in {len(trees['tiles'])} tiles and elevation imagery")


if __name__ == '__main__':
    main()
