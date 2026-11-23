"""Erzeuge ausschließlich die für das Repository vorgesehenen Ergebnisdateien."""

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis import calculate_results
from data import CONSTANTS, PATHS, PUMP_SECTIONS
from data_io import load_all_measurments
from physics import conductance
from time_plots import (
    decay_summary,
    overview_summary,
    pressure_fit_figure,
    pump_curves_figure,
    time_conductance_figure,
)

MIN_BIN_COUNT = 5


def pressure_bins(laminar: pd.DataFrame) -> pd.DataFrame:
    """Feste 1-mbar-Intervalle. Jeder veröffentlichte Wert fasst mehrere Messpunkte zusammen."""
    rows = []
    for lower, group in laminar.groupby(np.floor(laminar["p_mean"]).astype(int), sort=True):
        if len(group) < MIN_BIN_COUNT:
            continue
        q25, median, q75 = group["L_exp"].quantile([0.25, 0.5, 0.75])
        rows.append({
            "pressure_low_mbar": lower,
            "pressure_high_mbar": lower + 1,
            "mean_pressure_mbar": group["p_mean"].mean(),
            "n": len(group),
            "conductance_median_l_s": median,
            "conductance_q25_l_s": q25,
            "conductance_q75_l_s": q75,
        })
    if not rows:
        raise ValueError("Keine 1-mbar-Intervalle mit mindestens fünf Messpunkten.")
    return pd.DataFrame(rows)


def public_tables(results: dict[str, pd.DataFrame], measurements: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    molecular = results["molecular_results_07b"].loc[:, [
        "label", "K_N_tube", "L_exp", "u_L_exp", "L_theory", "u_L_theory",
    ]].set_axis([
        "tube", "knudsen_upstream", "measured_l_s", "measured_u_l_s",
        "model_l_s", "geometry_u_l_s",
    ], axis=1)
    speed = results["effective_pumping_speed_05"].set_axis([
        "nominal_pump_l_s", "intake_l_s", "aperture_l_s", "effective_l_s",
    ], axis=1)
    ratio = results["conductance_ratio_07c"].loc[:, [
        "R_exp", "u_R_exp", "R_theory", "u_R_theory",
    ]].set_axis(["measured_ratio", "measured_u", "model_ratio", "model_u"], axis=1)
    fit = results["laminar_fit_08"].loc[:, [
        "p_min", "p_max", "n_points", "offset", "amplitude", "decay", "u_decay", "rms_residual",
        "K_mean_min", "K_mean_max",
    ]].set_axis([
        "upstream_pressure_min_mbar", "upstream_pressure_max_mbar", "n", "offset_mbar", "amplitude_mbar",
        "decay_s_inv", "decay_fit_u_s_inv", "pressure_residual_rms_mbar",
        "knudsen_mean_min", "knudsen_mean_max",
    ], axis=1)
    return {
        "pumping_speed": speed,
        "molecular_conductance": molecular,
        "molecular_ratio": ratio,
        "pressure_decay_fit": fit,
        "conductance_by_pressure": pressure_bins(results["laminar_results_08"]),
        "pump_curves_by_time": overview_summary(measurements),
        "small_tube_by_time": decay_summary(results["laminar_results_08"]),
    }


def molecular_figure(table: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7.3, 3.6), layout="constrained")
    y = np.arange(len(table))
    ax.errorbar(table["measured_l_s"], y - 0.13, xerr=table["measured_u_l_s"],
                fmt="o", color="#00638a", capsize=4, label="Messung · Druckmodell")
    ax.errorbar(table["model_l_s"], y + 0.13, xerr=table["geometry_u_l_s"],
                fmt="D", color="#a34d16", capsize=4, label="Theorie · Geometrie")
    ax.set_xscale("log")
    ax.set_yticks(y, table["tube"])
    ax.invert_yaxis()
    ax.set_xlabel("Leitwert (L/s)")
    ax.set_title("Molekularer Leitwert der drei Pumpstrecken", loc="left", fontweight="bold")
    ax.grid(axis="x", which="both", alpha=0.20)
    ax.legend(loc="lower right", frameon=False)
    return fig


def pressure_figure(table: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7.3, 3.6), layout="constrained")
    section = PUMP_SECTIONS["klein"]
    pressure = np.linspace(table["pressure_low_mbar"].min(), table["pressure_high_mbar"].max(), 100)
    model = conductance(case="laminar_tube", diameter=section.diameter,
                        length=section.length, p1=pressure, p2=pressure,
                        viscosity=CONSTANTS.viscosity)
    ax.plot(pressure, model, color="#a34d16", label="Laminarer Kontinuumsgrenzfall")
    median = table["conductance_median_l_s"]
    ax.errorbar(table["mean_pressure_mbar"], median,
                yerr=[median - table["conductance_q25_l_s"],
                      table["conductance_q75_l_s"] - median],
                fmt="o", color="#00638a", capsize=4, label="Intervallmedian und Quartile")
    ax.set_xlabel("Mittlerer Kammerdruck (mbar)")
    ax.set_ylabel("Leitwert (L/s)")
    ax.set_title("Druckabhängiger Leitwert des kleinen Rohrs", loc="left", fontweight="bold")
    ax.grid(alpha=0.20)
    ax.legend(loc="upper left", frameon=False)
    return fig


def write_figures(output_dir: Path) -> None:
    molecular = pd.read_csv(output_dir / "molecular_conductance.csv")
    pressure = pd.read_csv(output_dir / "conductance_by_pressure.csv")
    curves = pd.read_csv(output_dir / "pump_curves_by_time.csv")
    small_tube = pd.read_csv(output_dir / "small_tube_by_time.csv")
    fit = pd.read_csv(output_dir / "pressure_decay_fit.csv").iloc[0]
    with mpl.rc_context({"svg.hashsalt": "differentielles-pumpen", "svg.fonttype": "path"}):
        for name, figure, args in [
            ("molecular_conductance.svg", molecular_figure, (molecular,)),
            ("conductance_by_pressure.svg", pressure_figure, (pressure,)),
            ("pump_curves_by_time.svg", pump_curves_figure, (curves,)),
            ("pressure_decay_fit.svg", pressure_fit_figure, (small_tube, fit)),
            ("conductance_by_time.svg", time_conductance_figure, (small_tube,)),
        ]:
            fig = figure(*args)
            try:
                fig.savefig(output_dir / name, metadata={"Date": None})
            finally:
                plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=PATHS.raw)
    parser.add_argument("--output-dir", type=Path, default=PATHS.root / "results")
    parser.add_argument("--figures-only", action="store_true",
                        help="Abbildungen aus vorhandenen kompakten Ergebnistabellen erzeugen.")
    args = parser.parse_args(argv)

    if not args.figures_only and args.output_dir.resolve().is_relative_to(args.raw_dir.resolve()):
        parser.error("Der Ausgabeordner darf nicht innerhalb der Rohdaten liegen.")
    try:
        if not args.figures_only:
            measurements = load_all_measurments(args.raw_dir)
            tables = public_tables(calculate_results(measurements), measurements)
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for name, table in tables.items():
                table.to_csv(args.output_dir / f"{name}.csv", index=False,
                             float_format="%.8g", lineterminator="\n")
        write_figures(args.output_dir)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Ergebnisexport fehlgeschlagen: {exc}\n")
    print(f"Öffentliche Ergebnisdateien: {args.output_dir}")


if __name__ == "__main__":
    main()
