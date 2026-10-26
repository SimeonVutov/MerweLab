import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import classification_report

from agent import predict_map


def plot_rewards(mean_rewards):
    plt.plot(mean_rewards)
    plt.title("Mean reward per episode")
    plt.xlabel("Episodes")
    plt.ylabel("Mean reward")
    plt.show()

def plot_real_and_predicted(real, predicted):
    classes = np.arange(1, 8)
    fig, ax = plt.subplots(1, 2, figsize=(13,5))
    ax[0].imshow(real)
    ax[0].axis('off')
    ax[0].set_title("Real")
    im1 = ax[1].imshow(predicted)
    ax[1].axis('off')
    ax[1].set_title("Predicted")

    cbar = fig.colorbar(
        im1, ax=ax, ticks=classes,
        boundaries=np.arange(0.5, 8, 1),
        fraction=0.046, pad=0.04
    )
    cbar.set_label("Class")

    plt.show()


def evaluate(model, start, target, classes, allowed):
    predicted = predict_map(model, start, allowed, len(classes))

    really_changed = start != target
    print("real changes:     ", really_changed.sum())
    print("predicted changes:", (predicted != start).sum())
    print("right on changed cells:", (predicted[really_changed] == target[really_changed]).mean())

    true_codes = classes[target]
    predicted_codes = classes[predicted]
    print(classification_report(true_codes.ravel(), predicted_codes.ravel(), zero_division=0))