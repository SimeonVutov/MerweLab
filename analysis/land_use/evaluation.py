"""Plots and metrics."""
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report

from agent import predict_map
from config import CLASS_NAMES


def plot_rewards(mean_rewards):
    plt.plot(mean_rewards)
    plt.title("Mean reward per episode")
    plt.xlabel("Episodes")
    plt.ylabel("Mean reward")
    plt.show()


def plot_map(state, classes, title="Map"):
    n_classes = len(classes)
    # one fixed colour per class; vmin/vmax put each class value in the middle of its colour
    cmap = plt.get_cmap("tab10", n_classes)
    plt.figure(figsize=(8, 7), constrained_layout=True)
    im = plt.imshow(state, cmap=cmap, vmin=-0.5, vmax=n_classes - 0.5, interpolation="nearest")
    plt.axis("off")
    plt.title(title)
    cbar = plt.colorbar(im, ticks=range(n_classes), fraction=0.046, pad=0.04)
    cbar.ax.set_yticklabels(CLASS_NAMES[:n_classes])
    cbar.set_label("Class")
    plt.show()


def plot_real_and_predicted(real, predicted):
    """Side by side comparison, same colours as plot_map."""
    n_classes = len(CLASS_NAMES)
    cmap = plt.get_cmap("tab10", n_classes)
    fig, ax = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for axis, data, title in zip(ax, (real, predicted), ("Real", "Predicted")):
        im = axis.imshow(data, cmap=cmap, vmin=-0.5, vmax=n_classes - 0.5, interpolation="nearest")
        axis.axis("off")
        axis.set_title(title)
    cbar = fig.colorbar(im, ax=ax, ticks=range(n_classes), fraction=0.046, pad=0.04)
    cbar.ax.set_yticklabels(CLASS_NAMES)
    cbar.set_label("Class")
    plt.show()


def evaluate(model, start, target, classes, allowed):
    """Compare a prediction from `start` with a real later map `target`."""
    predicted = predict_map(model, start, allowed, len(classes))

    really_changed = start != target
    print("real changes:     ", really_changed.sum())
    print("predicted changes:", (predicted != start).sum())
    print("right on changed cells:", (predicted[really_changed] == target[really_changed]).mean())

    true_codes = classes[target]
    predicted_codes = classes[predicted]
    print(classification_report(true_codes.ravel(), predicted_codes.ravel(), zero_division=0))