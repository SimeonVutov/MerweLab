"""All plotting code"""

import matplotlib.pyplot as plt
import pandas as pd


def _finish_plot(title, x_label, y_label, legend = False):
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    if legend:
        plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_series(x, y, x_label, y_label, title):
    """Plot simple series."""
    plt.figure(figsize=(15, 5))
    plt.plot(x, y)
    _finish_plot(title, x_label, y_label)


def plot_training_history(history) -> None:
    """Plot training and validation loss."""
    plt.figure(figsize=(10, 5))
    plt.plot(history.history["loss"], label="Training loss")
    plt.plot(history.history["val_loss"], label="Validation loss")
    _finish_plot("LSTM Training History", "Epoch", "MSE loss", legend=True)


def plot_forecast(comparison, max_comparison = None):
    """Plot actual versus predicted temperature on the test set."""
    if max_comparison is None:
        max_comparison = len(comparison["timestamp"])
    plt.figure(figsize=(15, 6))
    plt.plot(
        comparison["timestamp"][:max_comparison],
        comparison["actual_temperature"][:max_comparison],
        label="Actual temperature",
    )
    plt.plot(
        comparison["timestamp"][:max_comparison],
        comparison["predicted_temperature"][:max_comparison],
        label="Predicted temperature",
        alpha=0.8,
    )
    _finish_plot(
        "Actual vs. Predicted Future Air Temperature",
        "Time",
        "Air temperature",
        legend=True,
    )