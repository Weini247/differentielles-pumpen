import matplotlib.pyplot as plt
import pandas as pd

def plot_pump_curve(df : pd.DataFrame, title:str):
    fig, ax = plt.sublots()
    ax.semilogy(df["t"], df["p_N"], label="Nebenkammer")
    ax.semilogy(df["t"], df["p_H"], label="Hauptkammer")
    ax.set_xlabel("Zeit / s")
    ax.set_ylabel("Druck / mbar")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    ax.tight_layout()
    return fig
