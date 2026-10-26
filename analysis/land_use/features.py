import numpy as np
from scipy.ndimage import uniform_filter


def make_features(state, n_classes):
    # one hot encode the class of the state
    state_class = np.eye(n_classes)[state]
    # distributions of classes around the cell
    around_classes = np.stack([uniform_filter(state_class[:, :, k], size=5) for k in range(n_classes)], axis=-1)
    # TODO: Add distance to road as a feature
    # TODO: Add distance to hospital as a feature
    # TODO: Add distance to recreation area as a feature
    # TODO: Come up with more features
    # merge
    return np.concatenate([state_class, around_classes], axis=-1) # output stape is 2 * n
