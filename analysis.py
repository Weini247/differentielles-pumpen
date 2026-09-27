import matplotlib.pyplot as plt
import pandas as pd

from data_io import load_all_measurments, PLOTS_DIR
from plots import plot_pump_curve

def main():
    measurements = load_all_measurments()
    for name, df in measurements.items():
        print(name, len(df), df["t"].iloc[-1],)
        fig = plot_pump_curve(df, title=name)

        fig.savefig(PLOTS_DIR / f"pump_curve_{name}.pdf", bbox_inces="tight")
        plt.close(fig)


if __name__ == "__main__":
    main()
