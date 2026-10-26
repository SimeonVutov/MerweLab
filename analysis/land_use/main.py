import numpy as np

from features import make_features
from data_loading import load_raster, find_allowed_transitions,simplify_raster
from config import (
    TARGET_LAND_USE_2010_PATH,
    LAND_USE_2010_PATH,
    LAND_USE_2015_PATH,
    ModelConfig,
    TrainingConfig,
    ALL_LABELS,
    SIMPLIFIED_LABELS
)
from agent import (
    build_model,
    predict_map
)
from training import train
from environment import LandUseEnv
from evaluation import plot_rewards, evaluate, plot_real_and_predicted
def main():
    # load data
    train_land_use_2010 = load_raster(LAND_USE_2010_PATH)
    train_land_use_2015 = load_raster(LAND_USE_2015_PATH)

    simplified_2010 = simplify_raster(train_land_use_2010)
    simplified_2015 = simplify_raster(train_land_use_2015)

    classes = np.array(SIMPLIFIED_LABELS)
    n_classes = len(classes)

    start = np.searchsorted(classes, simplified_2010)
    target = np.searchsorted(classes, simplified_2015)

    allowed = find_allowed_transitions(simplified_2010, simplified_2015, classes)
    features = make_features(start, n_classes)

    # build environment
    env = LandUseEnv(start, target, n_classes)
    model_config = ModelConfig()
    model = build_model(features.shape[-1], n_classes, model_config)

    # train model
    train_config = TrainingConfig()
    mean_rewards = train(env, model, features, allowed, model_config, train_config)
    plot_rewards(mean_rewards)

    evaluate(model, start, target, classes, allowed)

    final_2010 = load_raster(TARGET_LAND_USE_2010_PATH)
    simplified_2010 = simplify_raster(final_2010)
    final_start = np.searchsorted(classes, simplified_2010)
    new_map = predict_map(model, final_start, allowed, n_classes)
    plot_real_and_predicted(simplified_2010, classes[new_map])

if __name__ == '__main__':
    main()