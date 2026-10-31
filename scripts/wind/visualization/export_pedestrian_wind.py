"""Export pedestrian wind over the detailed study area at 0.5 m and 1 m spacing."""

import json

import numpy as np
import pyvista as pv
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import Window

import settings
from common import TOP_GROUPS, point_fields, read_case, read_obj_groups
from coordinates import placement, to_rd


SCENARIOS = {"baseline": 500, "scenario_a": 800, "scenario_b": 800}
HEIGHT = 1.5
PIXEL_SIZES = (0.5, 1.0)
ROWS_PER_BATCH = 256
NODATA = -9999.0
OUTPUT = settings.ROOT / "outputs/data/wind/study_area"

# Use the detailed land, water and quay transitions. Exclude outer terrain.
GROUND_GROUPS = TOP_GROUPS | {"shore_or_seam_wall"}


def case_path(scenario):
    return settings.ROOT / "analysis/wind" / scenario / "wind_240"


def grid_bounds():
    """Cover the detailed ground in all scenarios with one shared extent."""
    outlines = []
    for scenario in SCENARIOS:
        ground = read_ground(scenario, GROUND_GROUPS)
        outlines.append(to_rd(ground.points))

    points = np.concatenate(outlines)
    step = max(PIXEL_SIZES)
    west = np.floor(points[:, 0].min() / step) * step
    east = np.ceil(points[:, 0].max() / step) * step
    south = np.floor(points[:, 1].min() / step) * step
    north = np.ceil(points[:, 1].max() / step) * step
    return west, south, east, north


def to_simulation(rd_points):
    """Undo the recorded RD translation and rotation."""
    data = placement()
    fx, fy, _ = data["flow_unit_vector_RD"]
    rotation = np.array([[fx, fy], [-fy, fx]])

    points = rd_points - np.asarray(data["RD_origin"])
    points[:, :2] = points[:, :2] @ rotation.T
    return points


def read_ground(scenario, groups):
    """Flatten the ground for height lookup, keeping its original heights."""
    path = case_path(scenario) / "constant/triSurface/terrain_hull.obj"
    surface = read_obj_groups(path, groups)
    faces = surface.faces.reshape(-1, 4)[:, 1:]
    triangles = surface.points[faces]

    # Vertical walls cannot define a ground height at a map position.
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    surface = surface.extract_cells(np.abs(normals[:, 2]) > 1e-10)
    surface = surface.extract_surface(algorithm="dataset_surface").clean()

    surface.point_data["ground_z"] = surface.points[:, 2].copy()
    surface.points[:, 2] = 0.0
    return surface


def sample_batch(flow, ground, rd_points):
    """Sample velocity 1.5 m above the modelled land or water surface."""
    points = to_simulation(rd_points)
    points[:, 2] = 0.0
    ground_samples = pv.PolyData(points).sample(ground, tolerance=1e-7)
    ground_z = np.asarray(ground_samples["ground_z"])
    on_ground = ground_samples["vtkValidPointMask"].astype(bool)
    candidates = np.flatnonzero(on_ground & np.isfinite(ground_z))

    values = np.full(len(points), NODATA, dtype=np.float32)
    if not candidates.size:
        return values

    points = points[candidates]
    points[:, 2] = ground_z[candidates] + HEIGHT
    samples = pv.PolyData(points).sample(flow)

    velocity = np.asarray(samples.point_data["U"])
    speed = np.linalg.norm(velocity, axis=1)
    valid = samples["vtkValidPointMask"].astype(bool) & np.isfinite(speed)
    values[candidates[valid]] = speed[valid]
    return values


def export_raster(flow, ground, bounds, scenario, time, pixel_size):
    """Write a few rows at a time to keep export memory manageable."""
    west, south, east, north = bounds
    width = int(round((east - west) / pixel_size))
    height = int(round((north - south) / pixel_size))
    transform = from_origin(west, north, pixel_size, pixel_size)
    folder = OUTPUT / f"grid_{pixel_size:g}m"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"wind_{scenario}_1p5m.tif"

    x = west + (np.arange(width) + 0.5) * pixel_size
    valid_count = 0
    minimum, maximum = np.inf, -np.inf
    print(f"Exporting {scenario}: {pixel_size:g} m grid, {width:,} × {height:,} pixels", flush=True)

    with rasterio.open(
        path, "w", driver="GTiff", height=height, width=width, count=1,
        dtype="float32", crs="EPSG:28992", transform=transform, nodata=NODATA,
        compress="deflate", predictor=3, tiled=True, BIGTIFF="IF_SAFER",
    ) as raster:
        for first_row in range(0, height, ROWS_PER_BATCH):
            rows = min(ROWS_PER_BATCH, height - first_row)
            y = north - (first_row + np.arange(rows) + 0.5) * pixel_size
            xx, yy = np.meshgrid(x, y)
            points = np.column_stack((xx.ravel(), yy.ravel(), np.zeros(xx.size)))

            values = sample_batch(flow, ground, points).reshape(rows, width)
            raster.write(values, 1, window=Window(0, first_row, width, rows))
            valid = values != NODATA
            valid_count += int(valid.sum())
            if valid.any():
                minimum = min(minimum, float(values[valid].min()))
                maximum = max(maximum, float(values[valid].max()))
            print(f"  Rows {first_row + rows:,} / {height:,}", flush=True)

        raster.set_band_description(1, "Wind speed |U| [m/s]")
        raster.update_tags(
            scenario=scenario, iteration=f"{time:g}", height_above_ground_m=HEIGHT,
            pixel_size_m=pixel_size, speed_units="m/s",
            speed_definition="sqrt(Ux**2 + Uy**2 + Uz**2)",
            wind_from_true_degrees=placement()["wind_from_true_degrees"],
            inlet_reference_speed_m_s=16, inlet_reference_height_m=60,
            sampling="Velocity interpolated to mesh points; each grid sampled directly",
            coverage="Detailed study area: land, water and quay transitions; outer terrain excluded",
            missing_values="Buildings, outside detailed ground or no valid flow sample",
            limitation="Finer pixels do not improve the underlying CFD accuracy",
            assessment="One steady wind condition; not annual comfort or gust speed",
        )

    if not valid_count:
        path.unlink()
        raise ValueError(f"No valid samples for {scenario}. Check the ground and coordinates.")
    print(f"Saved {path}\nValid pixels: {valid_count:,}; speed: {minimum:.2f}–{maximum:.2f} m/s", flush=True)


def save_coverage():
    """Save each scenario's detailed-ground boundary for QGIS."""
    features = []
    for scenario in SCENARIOS:
        ground = read_ground(scenario, GROUND_GROUPS)
        edges = ground.extract_feature_edges(
            boundary_edges=True, feature_edges=False,
            non_manifold_edges=False, manifold_edges=False,
        )
        points = to_rd(edges.points)[:, :2]
        segments = points[edges.lines.reshape(-1, 3)[:, 1:]].tolist()
        features.append({
            "type": "Feature", "properties": {"scenario": scenario, "area": "detailed_ground_boundary"},
            "geometry": {"type": "MultiLineString", "coordinates": segments},
        })

    # These coordinates are RD metres. Select EPSG:28992 if QGIS asks.
    collection = {
        "type": "FeatureCollection", "name": "Wind export coverage",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}},
        "features": features,
    }
    path = OUTPUT / "export_coverage.geojson"
    path.write_text(json.dumps(collection, indent=2) + "\n")
    print("Saved", path, flush=True)


def main():
    if PIXEL_SIZES != (0.5, 1.0) or HEIGHT != 1.5:
        raise ValueError("This export uses 0.5 m and 1 m grids at 1.5 m above ground.")

    bounds = grid_bounds()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    save_coverage()

    for scenario, time in SCENARIOS.items():
        settings.SCENARIO = scenario
        settings.TIME = time
        settings.CASE = case_path(scenario)
        mesh, saved_time = read_case(["U"])
        flow = point_fields(mesh)
        del mesh

        ground = read_ground(scenario, GROUND_GROUPS)
        for pixel_size in PIXEL_SIZES:
            export_raster(flow, ground, bounds, scenario, saved_time, pixel_size)
        del flow, ground


if __name__ == "__main__":
    main()
