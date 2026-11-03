"""Prepare shared geographic terrain heights and the local site clipping boundary."""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from pyproj import Geod, Transformer

from coordinates import Placement
from download_grids import GRID_DIRECTORY, ROOT


OUTPUT = ROOT / "data/web/terrain"
SPACING_M = 4


def prepare_site_boundary(placement):
    source = ROOT / "data/boundaries/GCS_FP_Development_Site.gpkg"
    with tempfile.TemporaryDirectory(prefix="merwelab-site-boundary-") as directory:
        converted = Path(directory) / "site.geojson"
        subprocess.run(["ogr2ogr", "-f", "GeoJSON", str(converted), str(source)], check=True)
        geometry = json.loads(converted.read_text())["features"][0]["geometry"]
    if geometry["type"] != "Polygon":
        raise ValueError("Expected a polygon for the development site")

    geographic = Transformer.from_crs(4978, 4979, always_xy=True)
    rings = []
    for ring in geometry["coordinates"]:
        points = np.asarray(ring)
        lon, lat, _ = geographic.transform(*placement.transformer.transform(
            points[:, 0], points[:, 1], np.zeros(len(points)), errcheck=True,
        ))
        rings.append(np.column_stack((lon, lat)).tolist())

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "site-boundary.geojson").write_text(json.dumps({
        "type": "Feature",
        "properties": {"source": source.relative_to(ROOT).as_posix()},
        "geometry": {"type": "Polygon", "coordinates": rings},
    }) + "\n")


def boundary_points(coordinates):
    if isinstance(coordinates[0], (int, float)):
        yield coordinates[:2]
    else:
        for child in coordinates:
            yield from boundary_points(child)


def read_raster(path, temporary):
    metadata = json.loads(subprocess.check_output([
        "gdalinfo", "--config", "GDAL_PAM_ENABLED", "NO", "-json", str(path),
    ]))
    binary = temporary / "terrain.bin"
    subprocess.run([
        "gdal_translate", "--config", "GDAL_PAM_ENABLED", "NO", "-q",
        "-of", "ENVI", "-ot", "Float32", str(path), str(binary),
    ], check=True)
    if "byte order = 0" not in binary.with_suffix(".hdr").read_text():
        raise ValueError("Expected little-endian terrain samples")
    width, height = metadata["size"]
    data = np.fromfile(binary, dtype="<f4").reshape(height, width)
    return data, metadata["geoTransform"], metadata["bands"][0].get("noDataValue")


def sample_raster(data, transform, nodata, x, y):
    if transform[2] != 0 or transform[4] != 0:
        raise ValueError("Rotated source rasters require an explicit resampling step")
    # GDAL transforms describe pixel edges; interpolation uses pixel centres.
    col = (x - transform[0]) / transform[1] - 0.5
    row = (y - transform[3]) / transform[5] - 0.5
    if np.any((col < 0) | (row < 0) | (col >= data.shape[1] - 1) | (row >= data.shape[0] - 1)):
        raise ValueError("Terrain does not cover the requested research context")

    column_index, row_index = col.astype(int), row.astype(int)
    column_fraction, row_fraction = col - column_index, row - row_index

    values = [
        data[row_index, column_index],
        data[row_index, column_index + 1],
        data[row_index + 1, column_index],
        data[row_index + 1, column_index + 1],
    ]
    if any(np.any(~np.isfinite(v) | (v == nodata)) for v in values):
        raise ValueError("Source terrain has missing samples; no implicit gap filling is allowed")
    return (
        values[0] * (1 - column_fraction) * (1 - row_fraction)
        + values[1] * column_fraction * (1 - row_fraction)
        + values[2] * (1 - column_fraction) * row_fraction
        + values[3] * column_fraction * row_fraction
    )


def grid_in_rd(bounds, width: int, height: int, placement: Placement):
    """Locate north-to-south geographic grid vertices in RD for raster sampling."""
    to_ecef = Transformer.from_crs(4979, 4978, always_xy=True)
    longitude, latitude = np.meshgrid(
        np.linspace(bounds[0], bounds[2], width),
        np.linspace(bounds[3], bounds[1], height),
    )
    lon, lat = longitude.ravel(), latitude.ravel()
    xyz = to_ecef.transform(lon, lat, np.zeros(len(lon)))
    rd_x, rd_y, _ = placement.transformer.transform(*xyz, direction="INVERSE", errcheck=True)
    return rd_x, rd_y


def main():
    boundary = ROOT / "data/cbs/cbs_output/buurten.geojson"
    cbs = json.loads(boundary.read_text(encoding="utf-8"))
    coordinates = []
    for feature in cbs["features"]:
        coordinates.extend(boundary_points(feature["geometry"]["coordinates"]))
    points = np.array(coordinates)
    west, south = points.min(axis=0)
    east, north = points.max(axis=0)
    # Preserve the context core and its outer display transition as separate extents.
    core = [west - 0.002, south - 0.001, east + 0.002, north + 0.001]
    bounds = [west - 0.01, south - 0.006, east + 0.01, north + 0.006]

    geod = Geod(ellps="WGS84")
    middle_latitude = (south + north) / 2
    width_m = geod.inv(bounds[0], middle_latitude, bounds[2], middle_latitude)[2]
    width = int(np.ceil(width_m / SPACING_M)) + 1
    height = int(np.ceil(geod.inv(west, bounds[1], west, bounds[3])[2] / SPACING_M)) + 1

    config = json.loads((ROOT / "config/merwelab_coordinates.json").read_text())
    placement = Placement(config["RD_origin"], GRID_DIRECTORY)
    prepare_site_boundary(placement)
    rd_x, rd_y = grid_in_rd(bounds, width, height, placement)
    to_geographic = Transformer.from_crs(4978, 4979, always_xy=True)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    assets = {}
    with tempfile.TemporaryDirectory(prefix="merwelab-terrain-") as directory:
        scenario = "baseline"
        source = ROOT / f"data/processed/noise/{scenario}/terrain.tif"
        data, transform, nodata = read_raster(source, Path(directory))
        nap = sample_raster(data, transform, nodata, np.asarray(rd_x), np.asarray(rd_y))
        ecef = placement.transformer.transform(rd_x, rd_y, nap, errcheck=True)
        heights = np.asarray(to_geographic.transform(*ecef, errcheck=True)[2], dtype="<f4")
        if not np.isfinite(heights).all():
            raise ValueError("Invalid ellipsoidal terrain heights")

        content = heights.tobytes()
        digest = hashlib.sha256(content).hexdigest()
        name = f"{scenario}-{digest[:12]}.bin"
        (OUTPUT / name).write_bytes(content)
        assets[scenario] = {
            "url": f"/web/terrain/{name}",
            "sha256": digest,
            "source": source.relative_to(ROOT).as_posix(),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
        print(f"Prepared {scenario}: {width} x {height}, {len(content):,} bytes")

    building_manifest = json.loads(
        (ROOT / "data/web/buildings/manifest.json").read_text(encoding="utf-8")
    )
    manifest = {
        "version": 1,
        "width": width,
        "height": height,
        "bounds": bounds,
        "coreBounds": core,
        "format": "float32-le",
        "rowOrder": "north-to-south",
        "heightReference": "WGS84 ellipsoid",
        "nominalSpacingM": SPACING_M,
        "source": "AHN-based completed terrain from the existing noise preparation",
        "assumptions": [
            (
                'Sources include documented water at NAP zero, building-ground '
                'estimates and interpolated gaps; not every sample is a measured '
                'AHN elevation.'
            ),
            (
                'Approximately 4 m display sampling from approximately 2 m source '
                'rasters; bilinear resampling does not improve source accuracy.'
            ),
            (
                'Current terrain is shared across scenarios; local surface models '
                'supply the proposal ground.'
            ),
            (
                'Outside coreBounds, the display blends to the ellipsoid at bounds. '
                'This transition is outside the CBS context and is not measured '
                'terrain.'
            ),
        ],
        "boundary_source": boundary.relative_to(ROOT).as_posix(),
        "grids": list(building_manifest["placement"]["grids"]),
        "scenarios": assets,
    }

    temporary = OUTPUT / "manifest.json.tmp"
    temporary.write_text(json.dumps(manifest, indent=2) + "\n")
    temporary.replace(OUTPUT / "manifest.json")


if __name__ == "__main__":
    main()
