# Merge 3DBAG CityJSON tiles and export CityGML

This optional tool merges downloaded 3DBAG CityJSON tiles, removes selected
buildings, retains LoD2.2 geometry, and converts the result to CityGML 2.0 for
Cesium ion. It is separate from the web application's local GLB pipeline;
starting the app does not require this conversion or a Cesium ion upload.

## Setup

From the repository root:

```bash
cd tools/3dbag_to_gml
python -m venv .venv
```

Activate the environment on Linux/macOS:

```bash
source .venv/bin/activate
```

Or in Windows Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

Then install the Python dependency:

```bash
python -m pip install cjio
```

The script expects Java 17 or newer and the complete citygml-tools 2.5.0 package.
Check Java with:

```bash
java -version
```

If the tool package is absent, obtain [citygml-tools 2.5.0](https://github.com/citygml4j/citygml-tools/releases/tag/v2.5.0)
and extract it beside `merge.py`. The expected launcher is:

- Windows: `citygml-tools-2.5.0/citygml-tools.bat`
- Linux/macOS: `citygml-tools-2.5.0/citygml-tools`

On Linux/macOS, make the launcher executable if necessary:

```bash
chmod +x citygml-tools-2.5.0/citygml-tools
```

## Prepare inputs

1. Download the required tiles in CityJSON format from [3DBAG](https://3dbag.nl/en/download).
2. Extract them and place `*.city.json` files directly in this tool's `data/` folder.
3. Edit `to_remove.txt` beside `merge.py`: one building identifier per line.
   It accepts matching CityObject IDs or the `identificatie` attribute, including
   the `NL.IMBAG.Pand.` prefix when present. Empty lines and lines starting with
   `#` are ignored. Keep the file empty if no buildings should be removed.

## Run

Run from **`tools/3dbag_to_gml`**, with the environment active:

```bash
python merge.py
```

The script deliberately resolves `./data`, `to_remove.txt`, the converter, and
its outputs from the current working directory. Running it from the repository
root without changing directory will use the wrong locations.

It writes or replaces:

```text
merged.city.json
merged.city.gml
```

It does not modify the source tiles. It filters to LoD2.2, so inspect the output
before using it if your tiles contain different levels of detail. Confirm the
intended buildings were removed, then upload `merged.city.gml` to Cesium ion
using its CityGML import flow if that is your intended destination.

For assets used by the current local application, see the
[web-preparation guide](../../scripts/web/README.md) instead.
