

"""
    Merge ./data/*.city.json into ./merged.city.json 
    then convert to ./merged.city.gml using citygml-tools.

    Dependencies:
        - cjio              (install with pip: "python -m pip install cjio")
        - ctiygml-tools     (if not included: https://github.com/citygml4j/citygml-tools/releases/tag/v2.5.0)
        - JAVA SE           (install from: https://www.oracle.com/java/technologies/downloads/#jdk27-windows)


    Run:     python merge.py
"""

import json
from pathlib import Path
import os
import subprocess
import shutil
from cjio import cityjson


files = sorted(path for path in Path("./data").glob("*.city.json") if path.is_file())
if not files:
    raise FileNotFoundError("No .city.json files found in ./data")

merged = None
for path in files:
    print(f"Reading {path.name}", flush=True)
    with path.open("r", encoding="utf-8-sig") as stream:
        tile = cityjson.reader(stream)

    if merged is None:
        merged = tile
    else:
        merged.merge([tile])  # Updates the model in place.
    del tile

with open("./to_remove.txt", encoding="utf-8-sig") as file:
    remove_identificaties = {
        line.strip() for line in file if line.strip() and line[0] != '#'
    }

print(f"Removing buildings with IDs: {remove_identificaties}")

remove_ids = [
    object_id
    for object_id, obj in merged.j["CityObjects"].items()
    if (
        obj.get("attributes", {}).get("identificatie") in remove_identificaties
        or object_id in remove_identificaties
    )
]

merged = merged.get_subset_ids(remove_ids, exclude=True)
merged.filter_lod("2.2")

print(f"Removed {len(remove_ids)} buildings.")

merged.update_bbox()


output = Path("./merged.city.json")
with output.open("w", encoding="utf-8") as stream:
    json.dump(merged.j, stream, ensure_ascii=False, separators=(",", ":"))

print(f"Merged {len(files)} files into {output.resolve()}")


tool_dir = Path("./citygml-tools-2.5.0")
launcher = "citygml-tools.bat" if os.name == "nt" else "citygml-tools"
tool = (tool_dir / launcher).resolve()


# Ensure Java is available on PATH before running citygml-tools.
if shutil.which("java") is None:
    raise RuntimeError(
        "Java was not found on PATH. "
        "Install Java 17 or newer and add its bin directory to PATH, "
        "then restart your terminal or IDE."
    )

# Convert to CityGML 2.0
subprocess.run(
    [
        str(tool),
        "from-cityjson",
        "--citygml-version", "2.0",
        str(output),
    ],
    check=True,
)


gml_output = output.with_suffix(".gml")
print(f"Created: {gml_output}")

