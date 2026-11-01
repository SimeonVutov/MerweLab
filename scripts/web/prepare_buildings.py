import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np
import pyproj

from coordinates import Placement
from download_grids import GRID_DIRECTORY, GRID_NAMES, ROOT


SOURCES = {
    "shared": ["yellow_buildings_lod12.obj", "red_buildings_lod12.obj", "additional_buildings_lod22_review.obj"],
    "baseline": ["baseline/buildings_existing.obj"],
    "scenario_a": ["scenario_a/buildings_v1.obj"],
    "scenario_b": ["scenario_b/buildings_v2.obj"],
}
OUTPUT = ROOT / "data/web/buildings"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_obj(source, destination, placement):
    lines = source.read_text().splitlines()
    points = np.array([list(map(float, line.split()[1:4])) for line in lines if line.startswith("v ")])
    local = placement.to_local(points)
    round_trip_error = float(np.max(np.linalg.norm(placement.to_rd(local) - points, axis=1)))
    float_error = float(np.max(np.linalg.norm(local.astype(np.float32).astype(np.float64) - local, axis=1)))
    if round_trip_error > 0.01 or float_error > 0.001:
        raise ValueError(f"Coordinate validation failed for {source.name}")

    converted = []
    vertex = 0
    for line in lines:
        if line.startswith("v "):
            converted.append("v " + " ".join(f"{value:.9f}" for value in local[vertex]))
            vertex += 1
        elif line.startswith("vn "):
            continue
        elif line.startswith("f "):
            # Recompute normals after the nonlinear RD/NAP transformation.
            converted.append("f " + " ".join("/".join(part.split("/")[:2]).rstrip("/") for part in line.split()[1:]))
        else:
            converted.append(line)
    destination.write_text("\n".join(converted) + "\n")
    material = source.with_suffix(".mtl")
    shutil.copyfile(material, destination.with_suffix(".mtl"))
    return {
        "source": source.relative_to(ROOT).as_posix(),
        "source_sha256": digest(source),
        "material_sha256": digest(material),
        "source_vertices": len(points),
        "source_faces": sum(line.startswith("f ") for line in lines),
        "source_objects": sum(line.startswith("o ") for line in lines),
        "bag_ids": sorted(set(re.findall(r"BAG_(\d{16})", "\n".join(lines)))),
        "bounds_rd": [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
        "bounds_enu": [local.min(axis=0).tolist(), local.max(axis=0).tolist()],
        "round_trip_error_m": round_trip_error,
        "float32_error_m": float_error,
    }


def prepare_models(sources, output):
    if not shutil.which("blender"):
        raise RuntimeError("Blender must be installed to triangulate and export the source meshes")
    config_path = ROOT / "config/merwelab_coordinates.json"
    config = json.loads(config_path.read_text())
    placement = Placement(config["RD_origin"], GRID_DIRECTORY)
    known = {item["path"]: item for item in config["items"]}
    output.mkdir(parents=True, exist_ok=True)
    models = {}
    with tempfile.TemporaryDirectory(prefix="merwelab-buildings-") as temporary:
        staging = Path(temporary)
        tasks = []
        for group, filenames in sources.items():
            models[group] = []
            for relative in filenames:
                source = ROOT / "data/scenarios" / relative
                prepared = staging / source.name
                report = prepare_obj(source, prepared, placement)
                report["coordinate_config_hash_matches"] = report["source_sha256"] == known[report["source"]]["sha256"]
                report["id"] = source.stem
                tasks.append({"input": str(prepared), "output": str(prepared.with_suffix(".glb"))})
                models[group].append(report)

        all_ids = [bag for group in ("shared", "baseline") for model in models[group] for bag in model["bag_ids"]]
        if len(set(all_ids)) != len(all_ids):
            raise ValueError("Duplicate BAG identities across shared and Current models")

        task_file = staging / "tasks.json"
        task_file.write_text(json.dumps(tasks))
        subprocess.run([
            "blender", "--background", "--threads", "2", "--factory-startup", "--python-exit-code", "1",
            "--python", str(Path(__file__).with_name("export_glb_blender.py")), "--", str(task_file),
        ], check=True)

        for assets in models.values():
            for report in assets:
                binary = staging / f"{report['id']}.glb"
                report["glb_sha256"] = digest(binary)
                name = f"{report['id']}-{report['glb_sha256'][:12]}.glb"
                report["url"] = f"/web/{output.name}/{name}"
                report["bytes"] = binary.stat().st_size
                shutil.copyfile(binary, output / name)

    manifest = {
        "version": 1,
        "placement": {
            "origin_rd": placement.origin_rd.tolist(),
            "origin_ecef_m": placement.origin_ecef.tolist(),
            "origin_lon_lat_height": list(placement.origin_geographic),
            "local_frame": "ENU",
            "source_crs": "EPSG:7415",
            "render_crs": "EPSG:4978",
            "method": "RD inverse projection, RDNAPTRANS2018 horizontal grid, inverse NLGEO2018 vertical shift, WGS84 ECEF, common true ENU",
            "grids": [{"name": name, "sha256": digest(GRID_DIRECTORY / name), "source": f"https://cdn.proj.org/{name}"} for name in GRID_NAMES],
            "pyproj_version": pyproj.__version__,
            "coordinate_config_sha256": digest(config_path),
            "assumptions": [
                "Supplied design heights are assumed to use NAP, as recorded in the coordinate configuration.",
                "ETRS89 is treated as WGS84 for display, following the selected PROJ operation; this is not an epoch-aware survey transformation.",
                "The imagery lies on the Cesium ellipsoid until terrain is integrated; do not lower models to that surface.",
                "Additional context includes the available 13 reviewed LoD2.2 parts, not the full requested selection.",
            ],
        },
        "models": models,
    }
    temporary_manifest = output / "manifest.json.tmp"
    temporary_manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    temporary_manifest.replace(output / "manifest.json")
    print(f"Prepared {sum(map(len, models.values()))} assets in {output.relative_to(ROOT)}")
    print(f"Common origin lon/lat/ellipsoid height: {placement.origin_geographic}")


if __name__ == "__main__":
    prepare_models(SOURCES, OUTPUT)
