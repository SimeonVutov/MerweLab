"""Generate the existing classified map using repository-relative paths."""

from data_loading import load_raster, simplify_raster, save_raster
from config import LAND_USE_PATH, SIMPLIFIED_MAP_PATH


def main():
    original_raster = load_raster(LAND_USE_PATH)
    simplified_raster = simplify_raster(original_raster)

    save_raster(SIMPLIFIED_MAP_PATH, simplified_raster, LAND_USE_PATH)


if __name__ == '__main__':
    main()
