"""Prepare the supplied CBS export for the browser using only the standard library."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/cbs/cbs_output"
OUTPUT = ROOT / "data/web/cbs/data.json"


def geometry_points(coordinates):
    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError("Empty CBS coordinates")

    if isinstance(coordinates[0], (int, float)):
        if len(coordinates) < 2 or not all(math.isfinite(value) for value in coordinates):
            raise ValueError("Invalid CBS coordinate")
        yield coordinates[:2]
        return

    for child in coordinates:
        yield from geometry_points(child)


def missing_to_none(value):
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError("CBS values must be finite")
        if value < 0:
            return None

    return value


def main():
    geometry_path = SOURCE / "buurten.geojson"
    summary_path = SOURCE / "summary_table.csv"
    neighbourhoods = json.loads(geometry_path.read_text())
    crs_name = neighbourhoods.get("crs", {}).get("properties", {}).get("name")
    if crs_name != "urn:ogc:def:crs:OGC:1.3:CRS84":
        raise ValueError("Expected longitude/latitude CBS polygons")

    features = neighbourhoods.get("features", [])
    if neighbourhoods.get("type") != "FeatureCollection" or not features:
        raise ValueError("Expected CBS neighbourhood features")

    codes = set()
    vertices = []
    for feature in features:
        properties = feature["properties"]
        code = properties["buurtcode"]
        if not isinstance(code, str) or code in codes:
            raise ValueError("Expected unique CBS neighbourhood codes")
        if feature["geometry"]["type"] not in ("Polygon", "MultiPolygon"):
            raise ValueError("Expected polygon neighbourhoods")

        codes.add(code)
        feature["id"] = code
        feature["properties"] = {
            key: missing_to_none(value) for key, value in properties.items()
        }
        vertices.extend(geometry_points(feature["geometry"]["coordinates"]))

    bounds = [
        min(point[0] for point in vertices),
        min(point[1] for point in vertices),
        max(point[0] for point in vertices),
        max(point[1] for point in vertices),
    ]
    if not (-180 <= bounds[0] < bounds[2] <= 180 and -90 <= bounds[1] < bounds[3] <= 90):
        raise ValueError("CBS coordinates are outside geographic bounds")

    with summary_path.open(newline="") as stream:
        summary = list(csv.DictReader(stream))

    for row in summary:
        for key, value in row.items():
            if key == "variable":
                continue

            if not value:
                row[key] = None
                continue

            row[key] = missing_to_none(float(value))

    sources = []
    for path in (geometry_path, summary_path):
        sources.append({
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })

    prepared = {
        "version": 1,
        "neighbourhoods": neighbourhoods,
        "summary": summary,
        "bounds": bounds,
        "sources": sources,
        "reference_year": None,
        "notes": [
            "Neighbourhood context shared by all design scenarios.",
            "Reference year and regional summary aggregation method are not supplied.",
            "Negative missing-value codes are null; actual zeros are preserved.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(prepared, allow_nan=False) + "\n")
    print(f"Prepared {len(features)} CBS neighbourhoods and {len(summary)} comparison indicators")


if __name__ == "__main__":
    main()
