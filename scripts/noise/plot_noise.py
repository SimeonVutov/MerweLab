from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm
from matplotlib.patches import Patch


# Configuration
scenario = "baseline"
results_folder = Path("outputs/data/noise") / scenario
figure_folder = Path("outputs/figures/noise") / scenario
scenario_folder = Path("data/processed/noise") / scenario
roads_file = Path("data/processed/noise/roads/roads.geojson")

views = {
    "overview": ("Assessment overview", [86845.25, 435300, 89624.75, 437263.5]),
    "detailed": ("Detailed study area", [87350, 435300, 89120, 436860]),
    "peninsula": ("Peninsula", [87950, 436120, 88350, 436550]),
}
period_titles = {
    "D": "Day (07–19)",
    "E": "Evening (19–23)",
    "N": "Night (23–07)",
    "DEN": "Day–evening–night (Lden)",
}
class_limits = [35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 200]
colour_map = "viridis"
receiver_height = 1.5
figure_size = (13, 11)
image_dpi = 200
file_formats = ["png", "pdf"]


# Read the heatmap and geographical context.
noise_map = gpd.read_file(results_folder / "noise_map.geojson")
buildings = gpd.read_file(scenario_folder / "buildings.geojson").to_crs(noise_map.crs)
roads = gpd.read_file(roads_file).to_crs(noise_map.crs)
water = gpd.read_file(
    scenario_folder / "ground.gpkg", layer="ground",
    where="BASIS = 'water'", bbox=tuple(views["overview"][1]),
).to_crs(noise_map.crs)
figure_folder.mkdir(parents=True, exist_ok=True)

class_ids = np.arange(len(class_limits))
class_labels = [f"<{class_limits[0]}"] + [
    f"{lower}–{upper}" for lower, upper in zip(class_limits[:-1], class_limits[1:])
]
colours = plt.get_cmap(colour_map, len(class_ids))
class_edges = np.append(class_ids - 0.5, class_ids[-1] + 0.5)
colour_norm = BoundaryNorm(class_edges, colours.N)


# Use the same noise bands at all three scales, without extrapolating results.
for view_name, (view_title, bounds) in views.items():
    xmin, ymin, xmax, ymax = bounds
    local_buildings = buildings.cx[xmin:xmax, ymin:ymax]
    local_roads = roads.cx[xmin:xmax, ymin:ymax]
    local_water = water.cx[xmin:xmax, ymin:ymax]
    fig, axes = plt.subplots(2, 2, figsize=figure_size, layout="constrained")

    for ax, (period, title) in zip(axes.flat, period_titles.items()):
        ax.set_facecolor("#f4f1eb")
        if not local_water.empty:
            local_water.plot(ax=ax, facecolor="#d7eaf0", edgecolor="none")

        levels = noise_map[noise_map["PERIOD"] == period].cx[xmin:xmax, ymin:ymax]
        if not levels.empty:
            levels.plot(
                ax=ax, column="ISOLVL", cmap=colours, norm=colour_norm,
                edgecolor="none",
            )
        if not local_roads.empty:
            local_roads.plot(ax=ax, color="#555555", linewidth=0.4)
        if not local_buildings.empty:
            local_buildings.plot(
                ax=ax, facecolor="#cccccc", edgecolor="#777777", linewidth=0.2,
            )

        ax.set(
            title=title, xlabel="RD easting (m)", ylabel="RD northing (m)",
            xlim=(xmin, xmax), ylim=(ymin, ymax), aspect="equal",
        )
        ax.ticklabel_format(style="plain", useOffset=False)
        ax.tick_params(axis="x", labelrotation=30)

    colour_scale = plt.cm.ScalarMappable(norm=colour_norm, cmap=colours)
    colour_bar = fig.colorbar(colour_scale, ax=axes, ticks=class_ids, shrink=0.8)
    colour_bar.ax.set_yticklabels(class_labels)
    colour_bar.set_label("A-weighted sound level (dB); Lden includes period penalties")
    fig.suptitle(
        f"{scenario} — {view_title}\nRoad-traffic noise at {receiver_height:g} m above ground"
    )
    fig.legend(
        handles=[
            Patch(facecolor="#cccccc", label="Buildings"),
            Patch(facecolor="#d7eaf0", label="Water outside noise coverage"),
            Patch(facecolor="#f4f1eb", label="Land outside noise coverage"),
        ],
        loc="outside lower center", ncol=3,
    )
    for extension in file_formats:
        fig.savefig(figure_folder / f"noise_{view_name}.{extension}", dpi=image_dpi)
    plt.close(fig)

print(f"Saved heatmaps to {figure_folder}")
