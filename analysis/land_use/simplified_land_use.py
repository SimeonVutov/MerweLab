from pathlib import Path

from data_loading import (load_raster, simplify_raster, save_raster)
from config import (LAND_USE_PATH, SIMPLIFIED_LABELS)
from evaluation import plot_map

original_raster = load_raster(LAND_USE_PATH)
simplified_raster = simplify_raster(original_raster)
save_raster(Path("../../data/land_use/simplified_land_use.tif"), simplified_raster, LAND_USE_PATH)
# simplified_raster = load_raster(Path("../../data/land_use/simplified_land_use.tif"))
# plot_map(simplified_raster, SIMPLIFIED_LABELS)