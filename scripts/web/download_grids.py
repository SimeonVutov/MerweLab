from pathlib import Path
import shutil
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
GRID_DIRECTORY = ROOT / ".cache/web/proj"
GRID_NAMES = ("nl_nsgi_rdtrans2018.tif", "nl_nsgi_nlgeo2018.tif")


def main():
    GRID_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for name in GRID_NAMES:
        destination = GRID_DIRECTORY / name
        if destination.exists():
            print(f"Already present: {name}")
            continue
        temporary = destination.with_suffix(".download")
        try:
            with urllib.request.urlopen(f"https://cdn.proj.org/{name}", timeout=60) as response:
                with temporary.open("wb") as output:
                    shutil.copyfileobj(response, output)
            with temporary.open("rb") as source:
                if source.read(4) not in (b"II*\x00", b"MM\x00*"):
                    raise ValueError(f"Downloaded {name} is not a TIFF grid")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"Downloaded: {name}")


if __name__ == "__main__":
    main()
