from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


OKABE_ITO = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "reddish_purple": "#CC79A7",
}

RUN_COLORS = {
    "keine" : OKABE_ITO["black"],
    "gross" : OKABE_ITO["blue"],
    "mittel" : OKABE_ITO["orange"],
    "klein" : OKABE_ITO["bluish_green"],
}

RUN_LABELS ={
    "keine" : "ohne Pumpstrecke",
    "gross" : "große Pumpstrecke",
    "mittel" : "mittlere Pumpstrecke",
    "klein" : "kleine Pumpstrecke",
}

def _finish(fig, output_path = None):
    fig.tight_layout()
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
    return fig


def plot_pump_curve(measurements : dict[str, pd.DataFrame], output_path=None):
    fig, ax = plt.subplots()

    for k, df in measurements.items():
        color = RUN_COLORS.get(k, OKABE_ITO["black"])
        label = RUN_LABELS.get(k, k)

        

        ax.semilogy(df["t"], df["p_N"], color = color, linewidth =1.6, label=f"{label}: $p_N$")
        ax.semilogy(df["t"], df["p_H"], color = color, linewidth =1.6, linestyle = "--" , label=f"{label}: $p_H$")
        
    ax.set_xlabel("Zeit $t$ / s")
    ax.set_ylabel("Druck $p$ / mbar")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize = 8, ncol=2)
    return _finish(fig, output_path)

def plot_molecular_conductances(results : pd.DataFrame, output_path = None):
    fig, ax = plt.subplots(figsize=(6.5, 4.2))

    x = np.arange(len(results))
    width = 0.36
    ax.bar(x - width /2, results["L_theory"], width, color = OKABE_ITO["blue"], label="Theorie")
    ax.bar(x + width/2, results["L_exp"] , width, yerr=results["u_L_exp"], capsize = 4, color = OKABE_ITO["orange"], label="Experiment")

    ax.set_xticks(x, results["label"])
    ax.set_yscale("log")
    ax.set_ylabel("Leitwert $L$ / (L s$^{-1}$)")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()

    return _finish(fig, output_path)

def plot_laminar_pressure(data : pd.DataFrame, *, t, p_fit, output_path=None):
    fig, ax = plt.subplots(figsize=(7.0, 4.4))

    ax.plot(data["t"], data["p_N"], ".", markersize=4, color = OKABE_ITO["blue"], label = "Messung $p_N$")
    ax.plot(t, p_fit, linewidth=1.7, color = OKABE_ITO["vermillion"], label="Exponentialfit")
    ax.plot(data["t"], data["p_H"], linewidth=1.2, linestyle="--", color=OKABE_ITO["bluish_green"], label="$p_H$")
    ax.plot(data["t"], data["p_mean"], linewidth=1.2, linestyle=":", color=OKABE_ITO["black"], label=r"$\bar{p} = (p_N + p_H)/2$")

    ax.set_xlabel("Zeit $t$/s")
    ax.set_ylabel("Druck $p$ / mbar")
    ax.grid(True, alpha=0.25)
    ax.legend()

    return _finish(fig, output_path)

def plot_laminar_conducatance(t, L_exp, L_theory, output_path=None):
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    ax.plot(t, L_exp, linewidth=1.6, color = OKABE_ITO["orange"], label="$L_{exp}$")
    ax.plot(t, L_theory, linewidth=1.6, color = OKABE_ITO["blue"], label="$L_{lam}$")

    ax.set_xlabel("Zeit $t$ / s")
    ax.set_ylabel("Leitwert $L$ / (L s$^{-1}$)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    
    return _finish(fig, output_path)
