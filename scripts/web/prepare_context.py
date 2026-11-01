import hashlib
import json
from pathlib import Path
import re

import numpy as np
from pyproj import Transformer

from coordinates import Placement
from download_grids import GRID_DIRECTORY, ROOT


def main():
    source = ROOT / "data/processed/noise/baseline/buildings.geojson"
    data = json.loads(source.read_text())
    buildings = json.loads((ROOT / "data/web/buildings/manifest.json").read_text())
    excluded = {bag for group in ("shared", "baseline") for asset in buildings["models"][group] for bag in asset["bag_ids"]}
    bounds = json.loads((ROOT / "data/web/terrain/manifest.json").read_text())["coreBounds"]
    placement = Placement(buildings["placement"]["origin_rd"], GRID_DIRECTORY)
    geographic = Transformer.from_crs(4978, 4979, always_xy=True)
    output = ROOT / "data/web/context"
    output.mkdir(parents=True, exist_ok=True)
    tiles = {}
    skipped = 0
    for feature in data["features"]:
        properties = feature["properties"]
        if properties.get("SOURCE") != "3DBAG":
            continue
        bag = re.search(r"\d{16}", properties.get("BAG_ID", ""))
        if not bag or bag.group() in excluded:
            continue
        base, roof = properties.get("GROUND_Z"), properties.get("ROOF_Z")
        if base is None or roof is None or not np.isfinite([base, roof]).all() or roof <= base:
            skipped += 1
            continue
        rings = feature["geometry"]["coordinates"]
        center = np.mean(np.asarray(rings[0])[:, :2], axis=0)
        lon, lat, base_h = geographic.transform(*placement.transformer.transform(*center, base, errcheck=True))
        if not (bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]):
            continue
        roof_h = geographic.transform(*placement.transformer.transform(*center, roof, errcheck=True))[2]
        converted = []
        for ring in rings:
            points = np.asarray(ring)
            x, y, _ = geographic.transform(*placement.transformer.transform(points[:, 0], points[:, 1], np.full(len(points), base), errcheck=True))
            converted.append(np.column_stack((x, y)).tolist())
        tile = (int(center[0] // 500), int(center[1] // 500))
        tiles.setdefault(tile, []).append({
            "type": "Feature", "id": f"context-{properties['PK']}",
            "properties": {"bag_id": bag.group(), "base_ellipsoid_m": base_h, "roof_ellipsoid_m": roof_h, "height_m": roof - base},
            "geometry": {"type": "Polygon", "coordinates": converted},
        })
    assets = []
    for tile, features in sorted(tiles.items()):
        content = json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")).encode()
        digest = hashlib.sha256(content).hexdigest()
        filename = f"context-{tile[0]}-{tile[1]}-{digest[:12]}.geojson"
        (output / filename).write_bytes(content)
        positions = np.concatenate([np.asarray(ring) for f in features for ring in f["geometry"]["coordinates"]])
        assets.append({"url": f"/web/context/{filename}", "bounds": [*positions.min(axis=0), *positions.max(axis=0)], "features": len(features)})
    manifest = {
        "version": 1, "tiles": assets, "features": sum(a["features"] for a in assets),
        "source": source.relative_to(ROOT).as_posix(), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "excluded_bag_ids": sorted(excluded), "skipped_invalid_heights": skipped,
        "representation": "Simplified footprint extrusions using existing 3DBAG ground and roof attributes; not original LoD2.2 roofs",
        "height_reference": "WGS84 ellipsoid", "bounds": bounds,
    }
    temporary = output / "manifest.json.tmp"
    temporary.write_text(json.dumps(manifest, indent=2) + "\n")
    temporary.replace(output / "manifest.json")
    print(f"Prepared {manifest['features']} context parts in {len(assets)} tiles")


if __name__ == "__main__":
    main()
