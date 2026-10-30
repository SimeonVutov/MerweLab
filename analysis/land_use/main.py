"""Train the land-use model on the start map, predict a new map and save it."""
import numpy as np
import tensorflow as tf

from agent import build_model, predict_map
from config import (
    LAND_USE_PATH, PREDICTED_MAP_PATH, MODEL_PATH,
    ModelConfig, TrainingConfig, SIMPLIFIED_LABELS,
)
from data_loading import load_raster, simplify_raster, find_allowed_transitions, save_raster
from environment import LandUseEnv
from evaluation import plot_rewards, plot_map
from features import make_features
from training import train


def main():
    tf.keras.utils.set_random_seed(42)

    # load data
    start = simplify_raster(load_raster(LAND_USE_PATH))
    classes = np.array(SIMPLIFIED_LABELS)
    n_classes = len(classes)
    plot_map(start, classes, title="Start map")

    allowed = find_allowed_transitions(classes)
    features = make_features(start, n_classes)

    # build environment and model
    env = LandUseEnv(start, n_classes)
    model_config = ModelConfig()
    model = build_model(features.shape[-1], n_classes, model_config)

    # train
    mean_rewards = train(env, model, features, allowed, model_config, TrainingConfig())
    plot_rewards(mean_rewards)

    # predict (hard rules are enforced inside predict_map)
    predicted_map = predict_map(model, start, allowed, n_classes)
    plot_map(predicted_map, classes, title="Predicted map")

    # quick check: shares of the usable area and public-facility blocks
    _, _, _, _, info = env.step(predicted_map)
    print(f"green {info['green_share']:.1%} | residential {info['residential_share']:.1%} | "
          f"facility clusters {info['facility_clusters']} | lonely facility cells {info['lonely_facility_cells']}")

    save_raster(PREDICTED_MAP_PATH, predicted_map, LAND_USE_PATH)
    model.save(MODEL_PATH)


if __name__ == "__main__":
    main()