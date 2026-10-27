"""Read the saved results and draw the maps."""

from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.tri import Triangulation
import numpy as np
import pyvista as pv

import settings
from coordinates import display_mesh, to_cfd, to_display, wind_bearing

BUILDINGS = (
    "yellow_buildings_lod12",
    "red_buildings_lod12",
    "additional_buildings_lod22_review",
    "peninsula_buildings",
)
BUILDING_PATCHES = {
    "contextYellow",
    "contextRed",
    "contextAdditional",
    "peninsulaBuildings",
}
PENINSULA_GROUPS = {
    "peninsula_ground",
    "peninsula_paved",
    "peninsula_green",
    "existing_platform_rim",
}
LAND_GROUPS = PENINSULA_GROUPS | {"context_land"}
TOP_GROUPS = LAND_GROUPS | {"water"}


def mesh_blocks(block, name=""):
    """Collect the mesh parts and their names."""
    blocks = []
    if isinstance(block, pv.MultiBlock):
        for index in range(block.n_blocks):
            child = block[index]
            child_name = block.get_block_name(index)
            blocks.extend(mesh_blocks(child, child_name))
    elif block is not None and block.n_cells:
        blocks.append((name, block))

    return blocks


def combine_meshes(blocks):
    blocks = list(blocks)

    if not blocks:
        raise ValueError("No matching mesh blocks were found.")
    if len(blocks) == 1:
        return blocks[0]

    return pv.MultiBlock(blocks).combine(merge_points=True)


def read_case(fields, buildings_only=False):
    """Read the requested fields at the selected iteration. Keep all cells."""
    if not (settings.CASE / "system/controlDict").is_file():
        raise FileNotFoundError(f"OpenFOAM case not found: {settings.CASE}")

    marker = settings.CASE / "visualization.foam"
    marker.touch(exist_ok=True)
    reader = pv.POpenFOAMReader(marker)
    reader.case_type = settings.CASE_TYPE
    reader.cell_to_point_creation = False

    reader.disable_all_cell_arrays()
    for field in fields:
        if field not in reader.cell_array_names:
            raise ValueError(f"Field {field} is missing from the case.")
        reader.enable_cell_array(field)

    reader.disable_all_patch_arrays()
    wanted = BUILDING_PATCHES if buildings_only else {"internalMesh"}
    for patch in reader.patch_array_names:
        name = patch.split("/")[-1]
        if name in wanted:
            reader.enable_patch_array(patch)

    times = [float(t) for t in reader.time_values if float(t) > 0]
    time = settings.TIME
    if time is None:
        time = max(times) if times else None
    if time is None or float(time) not in times:
        raise ValueError(f"Choose a saved positive iteration. Available: {times}")
    reader.set_active_time_value(float(time))

    blocks = []
    for name, block in mesh_blocks(reader.read()):
        if buildings_only or name == "internalMesh":
            blocks.append(block)
    mesh = combine_meshes(blocks)
    for field in fields:
        if field not in mesh.cell_data:
            raise ValueError(f"No cell field {field} at iteration {time}.")

    print(
        f"Read {settings.SCENARIO}, iteration {time:g}: {mesh.n_cells:,} cells",
        flush=True,
    )
    print(
        f"Display: {settings.ORIENTATION}; wind FROM {wind_bearing():g}° true.",
        flush=True,
    )
    return mesh, float(time)


def point_fields(mesh):
    """Average cell values at mesh points. Keep the cell values as well."""
    return mesh.cell_data_to_point_data(pass_cell_data=True)


def read_obj_groups(path, groups):
    """Read the selected groups from an OBJ file."""
    points, faces = [], []
    group = ""

    with Path(path).open() as source:
        for line in source:
            words = line.split()
            if not words:
                continue

            if words[0] == "v":
                points.append([float(value) for value in words[1:4]])
            elif words[0] == "g":
                group = " ".join(words[1:])
            elif words[0] == "f" and group in groups:
                indices = [int(word.split("/")[0]) for word in words[1:]]
                indices = [i - 1 if i > 0 else len(points) + i for i in indices]
                faces.extend([len(indices), *indices])

    if not faces:
        raise ValueError(f"No selected terrain groups in {path}")

    surface = pv.PolyData(np.asarray(points), np.asarray(faces))
    return surface.clean().triangulate()


# Read these surfaces once and reuse them for the other views.
@lru_cache(maxsize=None)
def terrain_surface():
    return read_obj_groups(
        settings.CASE / "constant/triSurface/terrain_hull.obj", TOP_GROUPS
    )


@lru_cache(maxsize=None)
def land_surface():
    return read_obj_groups(
        settings.CASE / "constant/triSurface/terrain_hull.obj", LAND_GROUPS
    )


@lru_cache(maxsize=None)
def baseline_peninsula_surface():
    return read_obj_groups(settings.PENINSULA_SURFACE, PENINSULA_GROUPS)


@lru_cache(maxsize=None)
def water_surface():
    return read_obj_groups(
        settings.CASE / "constant/triSurface/terrain_hull.obj", {"water"}
    )


@lru_cache(maxsize=None)
def building_surfaces():
    folder = settings.CASE / "constant/triSurface"
    buildings = []
    for name in BUILDINGS:
        buildings.append(pv.read(folder / f"{name}.obj"))

    mesh = combine_meshes(buildings)
    surface = mesh.extract_surface(algorithm="dataset_surface")
    return surface.triangulate()


def view_bounds(view):
    """Find the area used by the 3D view and its starting points."""
    if view == "overview":
        return np.array(terrain_surface().bounds)

    if view == "peninsula":
        bounds = np.array(baseline_peninsula_surface().bounds)
        bounds[:4] += np.array([-1, 1, -1, 1]) * settings.PENINSULA_MARGIN
        return bounds

    raise ValueError(f"Unknown view: {view}")


def map_bounds(view):
    """Find the map limits after rotating the ground outline."""
    source = terrain_surface() if view == "overview" else baseline_peninsula_surface()
    xy = to_display(source.points)[:, :2]
    margin = settings.PENINSULA_MARGIN if view == "peninsula" else 10.0

    return np.array(
        [
            xy[:, 0].min() - margin,
            xy[:, 0].max() + margin,
            xy[:, 1].min() - margin,
            xy[:, 1].max() + margin,
        ]
    )


@lru_cache(maxsize=None)
def flattened_terrain():
    surface = terrain_surface().copy()
    surface.point_data["ground_z"] = surface.points[:, 2].copy()
    surface.points[:, 2] = 0

    return surface


def ground_heights(points):
    """Find the ground height at each point and mark points outside the ground."""
    xy = np.array(points, copy=True)
    xy[:, 2] = 0
    samples = pv.PolyData(xy).sample(flattened_terrain(), tolerance=1e-7)
    return np.asarray(samples["ground_z"]), samples["vtkValidPointMask"].astype(bool)


def height_surface(flow):
    """Cut the mesh at the selected height above the ground."""
    bounds = np.array(terrain_surface().bounds)
    bounds[4:6] += settings.HEIGHT
    bounds[4] -= 1e-4
    bounds[5] += 1e-4

    # Keep the whole cells that cross the selected height range.
    slab = flow.clip_box(bounds, invert=False, crinkle=True)
    print(
        f"Cutting height surface through {slab.n_cells:,} native cells...", flush=True
    )

    heights, valid = ground_heights(slab.points)
    slab.point_data["height_above_ground"] = slab.points[:, 2] - heights
    slab.point_data["inside_footprint"] = valid.astype(np.uint8)

    # Keep only cells covered by the original ground model.
    covered = slab.threshold(
        0.5, scalars="inside_footprint", preference="point", all_scalars=True
    )

    surface = covered.contour([settings.HEIGHT], scalars="height_above_ground")
    if not surface.n_cells:
        raise ValueError("No height surface: check the terrain and HEIGHT.")
    print(f"Native map surface: {surface.n_cells:,} triangles", flush=True)
    return surface.triangulate()


def sample_map(flow, view, spacing=None):
    """Sample wind on a grid for the arrows and 2D streamlines."""
    bounds = map_bounds(view)
    step = settings.FLOW_SPACING[view] if spacing is None else spacing
    nx = int(np.ceil(np.ptp(bounds[:2]) / step)) + 1
    ny = int(np.ceil(np.ptp(bounds[2:]) / step)) + 1
    x = np.linspace(bounds[0], bounds[1], nx)
    y = np.linspace(bounds[2], bounds[3], ny)

    xx, yy = np.meshgrid(x, y)
    map_points = np.column_stack((xx.ravel(), yy.ravel(), np.zeros(xx.size)))
    points = to_cfd(map_points)
    heights, on_ground = ground_heights(points)
    points[:, 2] = heights + settings.HEIGHT

    samples = pv.PolyData(points).sample(flow)
    in_air = samples["vtkValidPointMask"].astype(bool)
    valid = (on_ground & in_air).reshape(xx.shape)
    velocity = to_display(samples.point_data["U"])
    velocity = velocity.reshape(ny, nx, 3)
    return x, y, velocity, valid


def add_map_guides(ax):
    """Add the north arrow and wind direction to the map."""
    rotation = np.deg2rad((wind_bearing() + 180) % 360)
    true_flow = np.array([np.sin(rotation), np.cos(rotation), 0.0])
    north = np.array([0.0, 1.0, 0.0])

    if settings.ORIENTATION == "cfd":
        angle = rotation
        matrix = np.array(
            [[np.sin(angle), -np.cos(angle)], [np.cos(angle), np.sin(angle)]]
        )
        north[:2] = north[:2] @ matrix
        true_flow = np.array([1.0, 0.0, 0.0])

    for anchor, vector, label in (
        ((0.91, 0.87), north, "N"),
        ((0.08, 0.87), true_flow, f"FROM {wind_bearing():g}°"),
    ):
        spans = np.array([np.ptp(ax.get_xlim()), np.ptp(ax.get_ylim())])
        # Keep the arrow direction correct when the map width and height differ.
        tip = np.array(anchor) + 0.07 * spans.min() * vector[:2] / spans

        ax.annotate(
            "",
            xy=tip,
            xytext=anchor,
            xycoords="axes fraction",
            arrowprops={"arrowstyle": "-|>", "color": "#172632", "lw": 1.8},
            zorder=12,
        )
        ax.text(
            anchor[0],
            anchor[1] - 0.035,
            label,
            transform=ax.transAxes,
            ha="center",
            fontsize=9,
            zorder=12,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 2},
        )


def create_map(view):
    fig, ax = plt.subplots(figsize=settings.FIGURE_SIZE, layout="constrained")
    bounds = map_bounds(view)
    labels = ("True east from site origin [m]", "True north from site origin [m]")
    if settings.ORIENTATION == "cfd":
        labels = ("Downwind CFD X [m]", "Crosswind CFD Y [m]")

    ax.set_xlim(bounds[:2])
    ax.set_ylim(bounds[2:])
    ax.set_aspect("equal")
    ax.set_xlabel(labels[0])
    ax.set_ylabel(labels[1])
    ax.set_facecolor("#ecf0f2")

    buildings = display_mesh(building_surfaces())
    faces = buildings.faces.reshape(-1, 4)[:, 1:]
    triangles = buildings.points[faces]
    normals = np.cross(
        triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    )
    # Show the roofs in the top view.
    roofs = normals[:, 2] > 1e-8
    ax.add_collection(
        PolyCollection(
            triangles[roofs, :, :2],
            facecolor="#394854",
            edgecolor="none",
            antialiased=False,
            zorder=5,
        )
    )

    outline = display_mesh(land_surface()).extract_feature_edges(
        boundary_edges=True,
        feature_edges=False,
        non_manifold_edges=False,
        manifold_edges=False,
    )
    segments = outline.points[outline.lines.reshape(-1, 3)[:, 1:]][:, :, :2]
    ax.add_collection(
        LineCollection(segments, colors="#465a64", linewidths=0.45, zorder=4)
    )

    add_map_guides(ax)
    return fig, ax


def draw_surface(
    ax, surface, field, colors, limits, interpolate=None, coordinates=None
):
    """Draw the mesh triangles with smooth colours or the saved cell values."""
    interpolate = settings.INTERPOLATE if interpolate is None else interpolate
    points = to_display(surface.points)[:, :2] if coordinates is None else coordinates
    faces = surface.faces.reshape(-1, 4)[:, 1:]
    triangles = points[faces]

    edge_a = triangles[:, 1] - triangles[:, 0]
    edge_b = triangles[:, 2] - triangles[:, 0]
    area = edge_a[:, 0] * edge_b[:, 1] - edge_a[:, 1] * edge_b[:, 0]
    keep = np.abs(area) > 1e-10
    faces = faces[keep].copy()

    # Put the triangle corners in the same order for Matplotlib.
    reverse = area[keep] < 0
    faces[reverse] = faces[reverse][:, [0, 2, 1]]
    triangulation = Triangulation(points[:, 0], points[:, 1], faces)

    data = surface.point_data[field] if interpolate else surface.cell_data[field][keep]
    if field == "U":
        data = np.linalg.norm(data, axis=1)

    if interpolate:
        image = ax.tripcolor(
            triangulation, data, shading="gouraud",
            cmap=colors, vmin=limits[0], vmax=limits[1], rasterized=True,
        )
    else:
        image = ax.tripcolor(
            triangulation, facecolors=data, shading="flat",
            cmap=colors, vmin=limits[0], vmax=limits[1], rasterized=True,
        )

    if settings.SHOW_CELL_EDGES:
        ax.triplot(triangulation, color="#172632", linewidth=0.15, alpha=0.3)

    print(
        f"{field} displayed range: {np.nanmin(data):.4g} to {np.nanmax(data):.4g}; colour limits {limits}",
        flush=True,
    )
    return image


def add_colorbar(fig, ax, image, label, fraction=0.035):
    fig.colorbar(
        image, ax=ax, label=label, fraction=fraction, pad=0.025, extend="both"
    )


def output_path(name, view, time):
    folder = settings.OUTPUT / f"iteration_{time:g}" / "north_up_native"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{name}_{view}.png"


def save_figure(fig, name, view, time, note=""):
    status = "Preliminary | " if settings.PRELIMINARY else ""
    fig.suptitle(
        f"{status}{settings.SCENARIO} | {name.replace('_', ' ')} | {view} | iteration {time:g}",
        fontsize=13,
    )
    if note:
        fig.supxlabel(note, fontsize=9)

    path = output_path(name, view, time)
    fig.savefig(path, dpi=settings.DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved", path, flush=True)


def draw_scalar_maps(field, name, colors, limits, label):
    mesh, time = read_case([field])
    flow = point_fields(mesh)
    surface = height_surface(flow)

    for view in settings.VIEWS:
        fig, ax = create_map(view)
        image = draw_surface(ax, surface, field, colors, limits)
        add_colorbar(fig, ax, image, label)

        method = (
            "vertex-interpolated" if settings.INTERPOLATE else "original cell values"
        )
        save_figure(
            fig,
            name,
            view,
            time,
            f"{settings.HEIGHT:g} m above source ground/water | native cells, {method}",
        )


def scene_bounds(view):
    xy_bounds = view_bounds(view)[:4].tolist()
    return xy_bounds + list(settings.SCENE_Z_RANGE)


def create_scene(view, show_buildings=True):
    plot = pv.Plotter(off_screen=settings.OFF_SCREEN, window_size=settings.IMAGE_SIZE)
    plot.set_background("white")
    plot.enable_anti_aliasing("ssaa")
    bounds = scene_bounds(view)

    plot.add_mesh(
        display_mesh(water_surface().clip_box(bounds, invert=False)),
        color="#c8dce5",
        show_scalar_bar=False,
    )
    plot.add_mesh(
        display_mesh(land_surface().clip_box(bounds, invert=False)),
        color="#d9d8cb",
        show_scalar_bar=False,
    )

    if show_buildings:
        plot.add_mesh(
            display_mesh(building_surfaces().clip_box(bounds, invert=False)),
            color="#b1bec8",
            show_scalar_bar=False,
        )

    plot.add_axes(xlabel="East", ylabel="North", zlabel="Up")
    return plot


def set_camera(plot, view):
    bounds = map_bounds(view)
    centre = np.array([(bounds[0] + bounds[1]) / 2, (bounds[2] + bounds[3]) / 2, 10.0])
    elevation = np.deg2rad(settings.CAMERA_ELEVATION)
    bearing = np.deg2rad(settings.CAMERA_BEARING)
    distance = max(np.ptp(bounds[:2]), np.ptp(bounds[2:])) * 2

    offset = distance * np.array(
        [
            np.sin(bearing) * np.cos(elevation),
            np.cos(bearing) * np.cos(elevation),
            np.sin(elevation),
        ]
    )

    plot.camera_position = [centre + offset, centre, (0, 0, 1)]
    plot.enable_parallel_projection()

    # Fit the selected area inside the image.
    width, depth = np.ptp(bounds[:2]), np.ptp(bounds[2:])
    projected_height = depth * np.sin(elevation) + np.ptp(
        settings.SCENE_Z_RANGE
    ) * np.cos(elevation)
    aspect = settings.IMAGE_SIZE[0] / settings.IMAGE_SIZE[1]

    plot.camera.parallel_scale = max(projected_height, width / aspect) * 0.55
    plot.reset_camera_clipping_range()


def save_scene(plot, name, view, time):
    set_camera(plot, view)
    status = "Preliminary | " if settings.PRELIMINARY else ""

    plot.add_text(
        f"{status}{settings.SCENARIO} | {name} | {view} | iteration {time:g}",
        position="upper_left",
        font_size=14,
        color="#253b4c",
    )
    plot.add_text(
        f"True-north display | wind FROM {wind_bearing():g}° → TO {(wind_bearing()+180)%360:g}°",
        position="lower_left",
        font_size=11,
        color="#253b4c",
    )

    path = output_path(name, view, time)
    plot.show(screenshot=str(path), auto_close=True)
    print("Saved", path, flush=True)
