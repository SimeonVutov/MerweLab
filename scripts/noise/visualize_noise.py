"""Plot exported NoiseModelling contours without changing simulation results."""

import argparse
import json
import re
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import shapely

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


# Settings
CLASS_LIMITS = [35, 40, 45, 50, 55, 60, 65, 70, 75, 80]
REPORT_THRESHOLDS = [45, 55, 65, 75]
DEFAULT_PERIOD = "DEN"
DEFAULT_VIEW = "study_area"
PENINSULA_BOUNDS = [87950, 436120, 88350, 436550]
SURFACE_GRID_SIZE = 200
IMAGE_DPI = 180
CAMERA_ELEVATION = 40
CAMERA_AZIMUTH = -65
VERTICAL_EXAGGERATION = 1
COLOUR_MAP = "viridis"
LAND_COLOUR = "#f4f1eb"
WATER_COLOUR = "#d7eaf0"
BUILDING_COLOUR = "#cccccc"
HIGHLIGHT_COLOUR = "#e27b36"
PERIOD_TITLES = {
    "D": "Day (07–19)",
    "E": "Evening (19–23)",
    "N": "Night (23–07)",
    "DEN": "Day–evening–night (Lden)",
}
VIEW_TITLES = {
    "overview": "Assessment overview",
    "study_area": "Study area",
    "peninsula": "Peninsula",
}
SCENARIO_TITLES = {
    "baseline": "Baseline",
    "scenario_a": "V1",
    "scenario_b": "V2",
}
CLASS_LABELS = (
    [f"<{CLASS_LIMITS[0]}"]
    + [f"{a}–{b}" for a, b in zip(CLASS_LIMITS[:-1], CLASS_LIMITS[1:])]
    + [f"{CLASS_LIMITS[-1]}+"]
)
COLOURS = plt.get_cmap(COLOUR_MAP, len(CLASS_LABELS))
NORM = BoundaryNorm(np.arange(len(CLASS_LABELS) + 1) - 0.5, COLOURS.N)


def contour_class(label):
    numbers = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", str(label))]
    if len(numbers) == 1:
        if numbers[0] == CLASS_LIMITS[-1] and "+" in str(label):
            return len(CLASS_LIMITS)
        if numbers[0] == CLASS_LIMITS[0] and any(c in str(label) for c in "<−-"):
            return 0
    if len(numbers) == 2:
        if numbers[1] == CLASS_LIMITS[0] and numbers[0] < numbers[1]:
            return 0
        for index, pair in enumerate(zip(CLASS_LIMITS[:-1], CLASS_LIMITS[1:]), 1):
            if np.allclose(numbers, pair):
                return index
        if numbers[0] == CLASS_LIMITS[-1] and numbers[1] == 200:
            return len(CLASS_LIMITS)
    raise ValueError(f"Unsupported contour interval: {label!r}. Check CLASS_LIMITS.")


def read_layer(path, **options):
    data = gpd.read_file(path, **options)
    if data.crs is None or data.crs.to_epsg() != 28992:
        raise ValueError(f"Expected EPSG:28992: {path}")
    data.geometry = shapely.force_2d(data.geometry.array)
    return data


def read_contours(path):
    data = read_layer(path)
    if not {"PERIOD", "ISOLABEL"}.issubset(data.columns):
        raise ValueError("Export CONTOURING_NOISE_MAP with PERIOD and ISOLABEL.")
    data["PERIOD"] = data["PERIOD"].astype(str).str.strip().str.upper()
    if set(data["PERIOD"]) != set(PERIOD_TITLES):
        raise ValueError("The contour export must contain D, E, N and DEN.")
    mapping = {label: contour_class(label) for label in data["ISOLABEL"].unique()}
    data["noise_class"] = data["ISOLABEL"].map(mapping)
    return data


def draw_context(ax, water, roads, buildings, bounds):
    ax.set_facecolor(LAND_COLOUR)
    if not water.empty:
        water.plot(ax=ax, color=WATER_COLOUR, edgecolor="none", zorder=0)
    if not roads.empty:
        roads.plot(ax=ax, color="#666666", linewidth=0.3, zorder=3)
    if not buildings.empty:
        buildings.plot(ax=ax, color=BUILDING_COLOUR, edgecolor="#777777",
                       linewidth=0.3, zorder=4)
    xmin, ymin, xmax, ymax = bounds
    ax.set(xlim=(xmin, xmax), ylim=(ymin, ymax), aspect="equal",
           xlabel="RD easting (m)", ylabel="RD northing (m)")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.tick_params(axis="x", labelrotation=25)


def draw_noise(ax, contours):
    if not contours.empty:
        contours.plot(ax=ax, column="noise_class", cmap=COLOURS, norm=NORM,
                      edgecolor="none", linewidth=0, zorder=2)


def add_colour_bar(fig, axes):
    bar = fig.colorbar(plt.cm.ScalarMappable(norm=NORM, cmap=COLOURS),
                       ax=axes, ticks=range(len(CLASS_LABELS)), shrink=0.8)
    bar.ax.set_yticklabels(CLASS_LABELS)
    bar.set_label("A-weighted level (dB); Lden includes evening/night penalties")


def save_figure(fig, folder, name):
    fig.savefig(folder / f"{name}.png", dpi=IMAGE_DPI)
    plt.close(fig)


def report_figures(contours, water, roads, buildings, bounds, folder, title, period):
    for name, periods, shape in [
        ("noise_bands", list(PERIOD_TITLES), (2, 2)),
        ("day_night", ["D", "N"], (1, 2)),
    ]:
        fig, axes = plt.subplots(*shape, figsize=(12, 5 * shape[0]), layout="constrained")
        for ax, code in zip(axes.flat, periods):
            draw_context(ax, water, roads, buildings, bounds)
            draw_noise(ax, contours[contours["PERIOD"] == code])
            ax.set_title(PERIOD_TITLES[code])
        add_colour_bar(fig, axes)
        fig.suptitle(title)
        save_figure(fig, folder, name)

    selected = contours[contours["PERIOD"] == period]
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), layout="constrained")
    for ax, threshold in zip(axes.flat, REPORT_THRESHOLDS):
        draw_context(ax, water, roads, buildings, bounds)
        cutoff = CLASS_LIMITS.index(threshold) + 1
        highlighted = selected[selected["noise_class"] >= cutoff]
        if not highlighted.empty:
            highlighted.plot(ax=ax, color=HIGHLIGHT_COLOUR, edgecolor="none", zorder=2)
        ax.set_title(f"{PERIOD_TITLES[period]} ≥ {threshold} dB")
    fig.suptitle(f"{title}\nSelected thresholds within calculated contour coverage")
    save_figure(fig, folder, "thresholds")


def building_mesh(buildings, origin):
    vertices, triangles = [], []
    if "HEIGHT" not in buildings:
        raise ValueError("The 3D view needs building HEIGHT values in metres.")
    for _, row in buildings.iterrows():
        height = float(row.HEIGHT)
        if not np.isfinite(height) or height <= 0:
            raise ValueError("Building HEIGHT values must be positive and finite.")
        for polygon in shapely.get_parts(row.geometry):
            if polygon.geom_type != "Polygon":
                continue
            faces = []
            for roof in shapely.get_parts(shapely.constrained_delaunay_triangles(polygon)):
                xy = np.asarray(roof.exterior.coords)[:3, :2] - origin
                faces.append(np.column_stack([xy, np.full(3, height)]))
            for ring in [polygon.exterior, *polygon.interiors]:
                xy = np.asarray(ring.coords)[:, :2] - origin
                for a, b in zip(xy[:-1], xy[1:]):
                    faces.append(np.array([[*a, 0], [*b, 0], [*b, height], [*a, height]]))
            for face in faces:
                start = len(vertices)
                vertices.extend(face.tolist())
                triangles.append([start, start + 1, start + 2])
                if len(face) == 4:
                    triangles.append([start, start + 2, start + 3])
    return np.asarray(vertices).reshape(-1, 3), np.asarray(triangles).reshape(-1, 3)


def noise_3d(contours, buildings, bounds, folder, title, period, receiver_height):
    xmin, ymin, xmax, ymax = bounds
    selected = contours[contours["PERIOD"] == period]
    x = np.linspace(xmin, xmax, SURFACE_GRID_SIZE)
    y = np.linspace(ymin, ymax, SURFACE_GRID_SIZE)
    x_grid, y_grid = np.meshgrid(x, y)
    classes = np.full(x_grid.size, np.nan)
    points = shapely.points(np.column_stack([x_grid.ravel(), y_grid.ravel()]))
    point_ids, polygon_ids = shapely.STRtree(selected.geometry.array).query(points, predicate="covered_by")
    classes[point_ids] = selected["noise_class"].to_numpy()[polygon_ids]
    classes = classes.reshape(x_grid.shape)
    z = np.where(np.isfinite(classes), receiver_height, np.nan)

    # The display grid samples existing bands; it adds no acoustic detail.
    fig = plt.figure(figsize=(13, 9), layout="constrained")
    ax = fig.add_subplot(projection="3d", computed_zorder=False)
    face_colours = COLOURS(NORM(np.nan_to_num(classes, nan=0)))
    ax.plot_surface(x_grid - xmin, y_grid - ymin, z, facecolors=face_colours,
                    rstride=1, cstride=1, shade=False, linewidth=0,
                    antialiased=False, zorder=1)

    vertices, triangles = building_mesh(buildings, np.array([xmin, ymin]))
    if len(vertices):
        faces = vertices[triangles]
        ax.add_collection3d(Poly3DCollection(
            faces, facecolors=BUILDING_COLOUR, edgecolors="#888888", linewidths=0.15, zorder=2
        ))
    maximum_height = max(25, vertices[:, 2].max() if len(vertices) else 25)
    ax.set(xlim=(0, xmax - xmin), ylim=(0, ymax - ymin), zlim=(0, maximum_height),
           xlabel="Local east (m)", ylabel="Local north (m)",
           zlabel="Relative height (m)")
    ax.set_box_aspect((xmax - xmin, ymax - ymin, maximum_height * VERTICAL_EXAGGERATION))
    ax.set_zticks([0, maximum_height])
    ax.view_init(elev=CAMERA_ELEVATION, azim=CAMERA_AZIMUTH)
    ax.set_title(f"{title}\n{PERIOD_TITLES[period]} — 3D noise overlay")
    add_colour_bar(fig, ax)
    fig.text(0.02, 0.01, f"Flat-ground context; vertical scale ×{VERTICAL_EXAGGERATION:g}. Colour shows pedestrian noise bands.",
             fontsize=9)
    save_figure(fig, folder, "noise_3d")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=SCENARIO_TITLES)
    parser.add_argument("--view", choices=VIEW_TITLES, default=DEFAULT_VIEW,
                        help="Scope used for all four PNG previews.")
    parser.add_argument("--period", choices=PERIOD_TITLES, default=DEFAULT_PERIOD)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    config = json.loads((root / "config/noise/study_area.json").read_text())
    bounds_by_view = {
        "overview": config["overview_bounds"],
        "study_area": config.get("study_area_bounds", config.get("detailed_bounds")),
        "peninsula": config.get("peninsula_bounds", PENINSULA_BOUNDS),
    }
    if len(REPORT_THRESHOLDS) != 4 or any(t not in CLASS_LIMITS for t in REPORT_THRESHOLDS):
        raise ValueError("Choose four REPORT_THRESHOLDS from CLASS_LIMITS.")
    receiver_height = config["receiver_height_m"]
    scenario_folder = root / "data/processed/noise" / args.scenario
    contours = read_contours(root / "outputs/data/noise" / args.scenario / "noise_map.geojson")
    output = root / "outputs/figures/noise" / args.scenario
    bounds = bounds_by_view[args.view]
    if bounds is None:
        raise ValueError("Set study_area_bounds in config/noise/study_area.json.")
    extent = shapely.box(*bounds)
    clipped = gpd.clip(contours, extent)
    if clipped.empty:
        raise ValueError("No exported noise contours cover the selected view.")
    buildings = gpd.clip(read_layer(scenario_folder / "buildings.geojson", bbox=tuple(bounds)), extent)
    roads = gpd.clip(read_layer(root / "data/processed/noise/roads/roads.geojson", bbox=tuple(bounds)), extent)
    water = gpd.clip(read_layer(scenario_folder / "ground.gpkg", layer="ground",
                               where="BASIS = 'water'", bbox=tuple(bounds)), extent)
    folder = output / args.view
    folder.mkdir(parents=True, exist_ok=True)
    title = (f"{SCENARIO_TITLES[args.scenario]} — {VIEW_TITLES[args.view]}\n"
             f"Road-traffic noise at {receiver_height:g} m above ground")
    report_figures(clipped, water, roads, buildings, bounds, folder, title, args.period)
    noise_3d(clipped, buildings, bounds, folder, title, args.period, receiver_height)
    print(f"Saved four PNG previews: {folder}")


if __name__ == "__main__":
    main()
