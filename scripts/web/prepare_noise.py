"""Prepare classified noise rasters and trusted receiver values without running simulations."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
from pyproj import Geod, Transformer

from coordinates import Placement
from download_grids import GRID_DIRECTORY, ROOT
from prepare_terrain import read_raster, sample_raster

OUTPUT = ROOT / "data/web/noise"
RASTERS = ROOT / "outputs/data/noise/app"
SCENARIOS = ("baseline", "scenario_a", "scenario_b")
PERIODS = ("D", "E", "N", "DEN")
LIMITS = (35, 40, 45, 50, 55, 60, 65, 70, 75, 80)
SPACING_M = 2
COLOURS = (
    "#440154", "#482475", "#414487", "#355f8d", "#2a788e", "#21918c",
    "#22a884", "#44bf70", "#7ad151", "#bddf26", "#fde725",
)
# V1's receiver export was overwritten and must never be read or used.
TRUSTED_RECEIVERS = {"baseline", "scenario_b"}


def run(arguments):
    subprocess.run(arguments, check=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset(folder, name, content, extension):
    if extension in ("json", "bin"):
        content = gzip.compress(content, compresslevel=6, mtime=0)
        extension += ".gz"

    filename = f"{name}-{hashlib.sha256(content).hexdigest()[:12]}.{extension}"
    (folder / filename).write_bytes(content)
    return f"/web/noise/{folder.name}/{filename}"


def class_code(label):
    text = str(label).strip()
    if text in ("-35", "<35"):
        return 1
    if text == "80+":
        return 11

    numbers = [int(value) for value in re.findall(r"\d+", text)]
    for index, interval in enumerate(zip(LIMITS[:-1], LIMITS[1:]), 2):
        if numbers == list(interval):
            return index

    raise ValueError(f"Unexpected noise contour band: {label}")


def prepare_contours(path):
    data = json.loads(path.read_text())
    crs = data.get("crs", {}).get("properties", {}).get("name")
    if crs != "urn:ogc:def:crs:EPSG::28992":
        raise ValueError(f"Expected RD contour geometry: {path}")

    periods = set()
    for feature in data["features"]:
        properties = feature["properties"]
        period = str(properties["PERIOD"]).strip().upper()
        if period not in PERIODS:
            raise ValueError(f"Unsupported noise period: {period}")
        if feature["geometry"]["type"] not in ("Polygon", "MultiPolygon"):
            raise ValueError("Noise contours must be polygons")

        periods.add(period)
        feature["properties"] = {
            "PERIOD": period,
            "classCode": class_code(properties["ISOLABEL"]),
        }

    if periods != set(PERIODS):
        raise ValueError("Noise contours must cover all four periods")

    return data


def export_receivers(scenario, folder, horizontal):
    if scenario not in TRUSTED_RECEIVERS:
        return None

    # Do not read or infer V1 receiver levels: its source export was overwritten.
    path = ROOT / f"outputs/data/noise/{scenario}/receiver_levels.geojson"
    data = json.loads(path.read_text())
    crs = data.get("crs", {}).get("properties", {}).get("name")
    if crs != "urn:ogc:def:crs:EPSG::28992":
        raise ValueError("Expected RD receiver geometry")

    receivers = {}
    for feature in data["features"]:
        properties = feature["properties"]
        identifier = str(properties["IDRECEIVER"])
        period = properties["PERIOD"]
        coordinates = feature["geometry"]["coordinates"][:2]
        if feature["geometry"]["type"] != "Point" or period not in PERIODS:
            raise ValueError("Invalid receiver geometry or period")

        receiver = receivers.setdefault(identifier, {"rd": coordinates, "levels": {}})
        if receiver["rd"] != coordinates or period in receiver["levels"]:
            raise ValueError("Inconsistent or duplicate receiver period")

        value = properties["LAEQ"]
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError("Invalid A-weighted receiver level")
        if value == -9999:
            value = None
        receiver["levels"][period] = value

    points = []
    for identifier in sorted(receivers):
        receiver = receivers[identifier]
        if set(receiver["levels"]) != set(PERIODS):
            raise ValueError("Receiver is missing a noise period")

        longitude, latitude = horizontal.transform(*receiver["rd"], errcheck=True)
        points.append({
            "id": identifier,
            "longitude": longitude,
            "latitude": latitude,
            "levels": receiver["levels"],
        })

    content = json.dumps({"receivers": points}, allow_nan=False, separators=(",", ":")).encode()
    return {
        "url": asset(folder, "receivers", content, "json"),
        "count": len(points),
        "source": path.relative_to(ROOT).as_posix(),
        "sourceSha256": digest(path),
        "valueField": "LAEQ",
    }


def prepare_scenario(scenario, placement, horizontal, bounds_rd, bounds, width, height):
    source = ROOT / f"outputs/data/noise/{scenario}/noise_map.geojson"
    folder = OUTPUT / scenario
    rasters = RASTERS / scenario
    folder.mkdir(parents=True, exist_ok=True)
    rasters.mkdir(parents=True, exist_ok=True)

    contours = prepare_contours(source)
    maps = {}
    with tempfile.TemporaryDirectory(prefix="merwelab-noise-") as directory:
        temporary = Path(directory)
        features = temporary / "contours.geojson"
        features.write_text(json.dumps(contours))

        for period in PERIODS:
            raster = temporary / f"{period}_bands_rd.tif"
            run([
                "gdal_rasterize", "--config", "GDAL_PAM_ENABLED", "NO", "-q",
                "-a", "classCode", "-where", f"PERIOD = '{period}'",
                "-te", *map(str, bounds_rd), "-tr", str(SPACING_M), str(SPACING_M),
                "-ot", "Byte", "-init", "0", "-a_nodata", "0", "-a_srs", "EPSG:28992",
                "-co", "COMPRESS=DEFLATE", str(features), str(raster),
            ])

            warped = temporary / "bands.tif"
            pipeline = placement.horizontal_pipeline + "+step +proj=unitconvert +xy_in=rad +xy_out=deg"
            run([
                "gdalwarp", "--config", "GDAL_PAM_ENABLED", "NO", "-q", "-overwrite",
                "-s_srs", "EPSG:28992", "-t_srs", "OGC:CRS84", "-ct", pipeline,
                "-te", *map(str, bounds), "-ts", str(width), str(height),
                "-r", "near", "-srcnodata", "0", "-dstnodata", "0", str(raster), str(warped),
            ])

            image = temporary / "bands.png"
            run([
                "gdal_translate", "--config", "GDAL_PAM_ENABLED", "NO", "-q",
                "-of", "PNG", "-ot", "Byte", str(warped), str(image),
            ])
            maps[period] = {"image": asset(folder, period, image.read_bytes(), "png")}
            (rasters / raster.name).write_bytes(raster.read_bytes())

    return {
        "source": source.relative_to(ROOT).as_posix(),
        "sourceSha256": digest(source),
        "bounds": bounds,
        "width": width,
        "height": height,
        "maps": maps,
        "receivers": export_receivers(scenario, folder, horizontal),
    }


def terrain_upper_envelope(longitude, latitude, terrain_metadata, terrain):
    """Sample a 5 x 5 terrain maximum so the display mesh clears nearby quay steps."""
    west, south, east, north = terrain_metadata["bounds"]
    column = (longitude - west) / (east - west) * (terrain_metadata["width"] - 1)
    row = (north - latitude) / (north - south) * (terrain_metadata["height"] - 1)
    if np.any(column < 2) or np.any(column > terrain.shape[1] - 4):
        raise ValueError("Noise mesh extends beyond prepared terrain")
    if np.any(row < 2) or np.any(row > terrain.shape[0] - 4):
        raise ValueError("Noise mesh extends beyond prepared terrain")

    column = column.astype(int)
    row = row.astype(int)
    # A local upper envelope keeps the continuous display mesh above quay-height steps.
    envelope = np.full(len(longitude), -np.inf)
    for offset_y in range(-2, 3):
        for offset_x in range(-2, 3):
            envelope = np.maximum(envelope, terrain[row + offset_y, column + offset_x])

    return envelope


def prepare_mesh(bounds, width, height, placement, horizontal):
    """Build one ENU display mesh above shared and scenario ground, without changing acoustics."""
    terrain_metadata = json.loads((ROOT / "data/web/terrain/manifest.json").read_text())
    terrain_url = terrain_metadata["scenarios"]["baseline"]["url"]
    terrain_path = ROOT / "data/web" / terrain_url.removeprefix("/web/")
    terrain = np.fromfile(terrain_path, dtype="<f4").reshape(
        terrain_metadata["height"], terrain_metadata["width"]
    )

    columns = np.linspace(0, width, math.ceil(width / 2) + 1)
    rows = np.linspace(0, height, math.ceil(height / 2) + 1)
    column_grid, row_grid = np.meshgrid(columns, rows)
    longitude = bounds[0] + column_grid.ravel() / width * (bounds[2] - bounds[0])
    latitude = bounds[3] - row_grid.ravel() / height * (bounds[3] - bounds[1])
    envelope = terrain_upper_envelope(longitude, latitude, terrain_metadata, terrain)

    # Compare NAP scenario heights in the same ellipsoid datum as the shared terrain.
    rd_x, rd_y = horizontal.transform(longitude, latitude, direction="INVERSE", errcheck=True)
    geographic = Transformer.from_crs(4978, 4979, always_xy=True)
    with tempfile.TemporaryDirectory(prefix="merwelab-noise-ground-") as directory:
        for scenario in SCENARIOS:
            source = ROOT / f"data/processed/noise/{scenario}/terrain.tif"
            ground, transform, nodata = read_raster(source, Path(directory))
            ground_nap_m = sample_raster(
                ground,
                transform,
                nodata,
                np.asarray(rd_x),
                np.asarray(rd_y),
            )
            ecef = placement.transformer.transform(rd_x, rd_y, ground_nap_m, errcheck=True)
            ground_ellipsoid_m = np.asarray(geographic.transform(*ecef, errcheck=True)[2])
            envelope = np.maximum(envelope, ground_ellipsoid_m)

    display_height = envelope + 1.5
    to_ecef = Transformer.from_crs(4979, 4978, always_xy=True)
    display_ecef = np.column_stack(to_ecef.transform(
        longitude,
        latitude,
        display_height,
        errcheck=True,
    ))
    positions = ((display_ecef - placement.origin_ecef) @ placement.axes).astype("<f4")
    texture_coordinates = np.column_stack((column_grid.ravel() / width, 1 - row_grid.ravel() / height)).astype("<f4")

    identifiers = np.arange(column_grid.size, dtype=np.uint32).reshape(column_grid.shape)
    top_left = identifiers[:-1, :-1]
    top_right = identifiers[:-1, 1:]
    bottom_left = identifiers[1:, :-1]
    bottom_right = identifiers[1:, 1:]
    indices = np.stack(
        (top_left, bottom_left, top_right, top_right, bottom_left, bottom_right),
        axis=-1,
    ).astype("<u4").ravel()

    folder = OUTPUT / "shared"
    folder.mkdir(parents=True, exist_ok=True)
    return {
        "positions": asset(folder, "positions", positions.tobytes(), "bin"),
        "st": asset(folder, "st", texture_coordinates.tobytes(), "bin"),
        "indices": asset(folder, "indices", indices.tobytes(), "bin"),
        "vertexCount": len(positions),
        "indexCount": len(indices),
        "originEcef": placement.origin_ecef.tolist(),
    }


def main():
    config = json.loads((ROOT / "config/noise/study_area.json").read_text())
    coordinates = json.loads((ROOT / "config/merwelab_coordinates.json").read_text())
    placement = Placement(coordinates["RD_origin"], GRID_DIRECTORY)
    horizontal = Transformer.from_pipeline(
        placement.horizontal_pipeline + "+step +proj=unitconvert +xy_in=rad +xy_out=deg"
    )

    bounds_rd = config[config["calculation_bounds_key"]]
    west, south, east, north = bounds_rd
    longitude, latitude = horizontal.transform(
        [west, west, east, east],
        [south, north, south, north],
    )
    bounds = [min(longitude), min(latitude), max(longitude), max(latitude)]
    geod = Geod(ellps="WGS84")
    middle_latitude = (bounds[1] + bounds[3]) / 2
    width = math.ceil(geod.inv(
        bounds[0],
        middle_latitude,
        bounds[2],
        middle_latitude,
    )[2] / SPACING_M)
    height = math.ceil(geod.inv(bounds[0], bounds[1], bounds[0], bounds[3])[2] / SPACING_M)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    scenarios = {}
    for scenario in SCENARIOS:
        scenarios[scenario] = prepare_scenario(
            scenario, placement, horizontal, bounds_rd, bounds, width, height
        )
        print(f"Prepared noise maps: {scenario}", flush=True)

    labels = ["<35"] + [f"{a}–{b}" for a, b in zip(LIMITS[:-1], LIMITS[1:])] + ["80+"]
    classes = []
    for index, (label, colour) in enumerate(zip(labels, COLOURS)):
        lower = None
        upper = None
        if index > 0:
            lower = LIMITS[index - 1]
        if index < len(LIMITS):
            upper = LIMITS[index]
        classes.append({"code": index + 1,
        "label": label,
        "lower": lower,
        "upper": upper,
        "colour": colour})

    manifest = {
        "version": 1,
        "encoding": "uint8-class-code",
        "noData": 0,
        "nominalSpacingM": SPACING_M,
        "samplingHeightM": config["receiver_height_m"],
        "classes": classes,
        "periods": list(PERIODS),
        "threshold": {"minimum": 35, "maximum": 80, "step": 5},
        "scenarios": scenarios,
        "mesh": prepare_mesh(bounds, width, height, placement, horizontal),
        "notes": [
            (
                'Colours represent exported NoiseModelling contour bands, not exact '
                'point levels.'
            ),
            (
                'Thresholds use the available 5 dB band boundaries without '
                'inventing within-band values.'
            ),
            (
                'Two-metre display rasterization does not increase acoustic '
                'resolution; missing coverage stays transparent.'
            ),
            (
                'Class-code GeoTIFFs are generated under outputs/data/noise/app in '
                'EPSG:28992; browser PNGs preserve those integer classes with '
                'nearest-neighbour reprojection.'
            ),
            (
                'One continuous approximately 4 m display mesh clears a local upper '
                'envelope of shared AHN and all three scenario ground rasters by '
                '1.5 m. This avoids clipping holes and overlaps with local site '
                'surfaces. Display heights do not change the exported acoustic '
                'results or receiver heights.'
            ),
            (
                'V1 receiver levels are explicitly untrusted and excluded from all '
                'preparation and browser assets.'
            ),
            (
                'Trusted receiver values retain LAEQ from their D/E/N/DEN export '
                'rows; DEN is the exported Lden indicator.'
            ),
        ],
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
