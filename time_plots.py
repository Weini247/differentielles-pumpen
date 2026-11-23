"""Zeitdiagramme aus Intervallstatistiken ohne Einzelmesswerte."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from physics import exponential_pressure
from plots import OKABE_ITO, RUN_LABELS

TIME_BIN_S = 10
MIN_BIN_COUNT = 5

COLORS = {
    "p_N": OKABE_ITO["blue"],
    "p_H": OKABE_ITO["bluish_green"],
    "p_mean": "#555555",
}


def _time_medians(frame: pd.DataFrame, columns: list[str], *, origin: float) -> pd.DataFrame:
    start = np.floor((frame["t"] - origin) / TIME_BIN_S).astype(int) * TIME_BIN_S
    groups = frame.groupby(start.rename("bin_start_s"), sort=True)
    medians = groups[columns].median().add_suffix("_median")
    medians.insert(0, "n", groups.size())
    return medians[medians["n"] >= MIN_BIN_COUNT].reset_index()


def overview_summary(measurements: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return pd.concat([
        _time_medians(frame, ["p_N", "p_H"], origin=0).assign(run=run)
        for run, frame in measurements.items()
    ], ignore_index=True)


def decay_summary(laminar: pd.DataFrame) -> pd.DataFrame:
    summary = _time_medians(
        laminar, ["p_N", "p_H", "p_mean", "L_exp", "L_theory"], origin=laminar["t"].iloc[0],
    )
    if summary.empty:
        raise ValueError("Das Fitfenster enthält kein 10-s-Intervall mit fünf Messpunkten.")
    return summary


def _centers(table: pd.DataFrame):
    return table["bin_start_s"] + TIME_BIN_S / 2


def pump_curves_figure(table: pd.DataFrame):
    fig, axs = plt.subplots(2, 2, figsize=(8.4, 5.9), sharex=True, sharey=True,
                            layout="constrained")
    fig.suptitle("Druckverläufe der vier Pumpversuche", x=0.04, ha="left", fontweight="bold")
    for ax, (run, title) in zip(axs.flat, RUN_LABELS.items()):
        series = table[table["run"] == run]
        for channel, label in [("p_N", "Nebenkammer"), ("p_H", "Hauptkammer")]:
            ax.semilogy(_centers(series), series[f"{channel}_median"], color=COLORS[channel],
                        label=label, linewidth=1.5)
        ax.set_title(title[0].upper() + title[1:], loc="left", fontsize=10)
        ax.grid(alpha=0.2)
    axs[0, 0].legend(loc="upper right", frameon=False, fontsize=8)
    for ax in axs[:, 0]:
        ax.set_ylabel("Druck (mbar)")
    for ax in axs[-1, :]:
        ax.set_xlabel("Zeit (s)")
    return fig


def pressure_fit_figure(table: pd.DataFrame, fit: pd.Series):
    fig, ax = plt.subplots(figsize=(7.3, 3.9), layout="constrained")
    centers = _centers(table)
    for channel, label, marker in [
        ("p_N", "Nebenkammer", "o"),
        ("p_H", "Hauptkammer", "D"),
        ("p_mean", "Mittlerer Druck", "s"),
    ]:
        ax.plot(centers, table[f"{channel}_median"], linestyle="none", marker=marker,
                markersize=5, color=COLORS[channel], label=label)
    times = np.linspace(0, table["bin_start_s"].max() + TIME_BIN_S, 200)
    ax.plot(times, exponential_pressure(times, fit["offset_mbar"], fit["amplitude_mbar"],
                                        fit["decay_s_inv"]),
            color=OKABE_ITO["vermillion"], label="Exponentialfit der Nebenkammer")
    ax.set_title("Druckabfall beim kleinen Rohr", loc="left", fontweight="bold")
    ax.set_xlabel("Zeit seit Beginn des Fitfensters (s)")
    ax.set_ylabel("Druck (mbar)")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    return fig


def time_conductance_figure(table: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7.3, 3.9), layout="constrained")
    ax.plot(_centers(table), table["L_exp_median"], "o-", color=OKABE_ITO["blue"],
            label="Aus Druckabfall abgeleiteter Leitwert")
    ax.plot(_centers(table), table["L_theory_median"], "D--", color=OKABE_ITO["vermillion"],
            label="Laminarer Kontinuumsgrenzfall")
    ax.set_title("Zeitlicher Verlauf des Leitwerts beim kleinen Rohr", loc="left", fontweight="bold")
    ax.set_xlabel("Zeit seit Beginn des Fitfensters (s)")
    ax.set_ylabel("Leitwert (L/s)")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, fontsize=8)
    return fig

