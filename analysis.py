from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from data import CONSTANTS, PATHS, PUMP_SECTIONS
from data_io import load_all_measurments
from physics import (
    converter,
    knudsen_pressure,
    conductance,
    throughput,
    effective_pumping_speed,
    exponential_pressure,
    exponential_pressure_derivative,
    particle_number_derivative,
    conductance_uncert,
    ratio_uncert,
    molecular_conductance_ratio,
    molecular_ratio_geom_uncert,
)
from plots import (
    plot_pump_curve,
    plot_molecular_conductances,
    plot_laminar_pressure,
    plot_laminar_conducatance,
)


# =============================================================================
# Lokale Versuchskonfiguration
# =============================================================================

S_ABS = 67.0
INTAKE_LENGTH = 0.415
INTAKE_DIAMETER = 34.8e-3
APERTURE_DIAMETER = 1.0e-3

V_N = 0.146
U_V_N = 0.010

REL_PRESSURE_UNCERT = 0.30
LAST_SECONDS = 30.0


# data.py nutzt "medium", der Rest des Codes "mittel".
SECTIONS = {
    "gross": PUMP_SECTIONS["gross"],
    "mittel": PUMP_SECTIONS["medium"],
    "klein": PUMP_SECTIONS["klein"],
}

# PATHS.processed ist in data.py korrekt.
PLOTS = PATHS.processed / "plots"
TABLES = PATHS.processed / "tables"


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def create_output_dirs():
    PLOTS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)


def normalize_measurement_keys(
    measurements: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """
    Vereinheitlicht ausschließlich die Dictionary-Keys aus data_io.py.

    data_io.py liefert aktuell:
        baseline, groß, mittel, klein

    analysis.py und plots.py verwenden:
        keine, gross, mittel, klein
    """
    required = {"baseline", "groß", "mittel", "klein"}
    missing = required - set(measurements)

    if missing:
        raise KeyError(
            "Fehlende Messreihen in data_io.FILES: "
            f"{sorted(missing)}. Vorhanden: {sorted(measurements)}"
        )

    return {
        "keine": measurements["baseline"],
        "gross": measurements["groß"],
        "mittel": measurements["mittel"],
        "klein": measurements["klein"],
    }


def last_time_window(
    df: pd.DataFrame,
    seconds: float = LAST_SECONDS,
) -> pd.DataFrame:
    t_end = float(df["t"].iloc[-1])
    return df[df["t"] >= t_end - seconds].copy()


# =============================================================================
# Strömungsbereiche
# =============================================================================

def flow_regions() -> pd.DataFrame:
    rows = []

    for key, section in SECTIONS.items():
        p_cont_pa = knudsen_pressure(
            K=0.01,
            diameter=section.diameter,
            k_B=CONSTANTS.k_B,
            temperatur=CONSTANTS.temp,
            particle_diameter=CONSTANTS.particle_diameter,
        )

        p_mol_pa = knudsen_pressure(
            K=0.5,
            diameter=section.diameter,
            k_B=CONSTANTS.k_B,
            temperatur=CONSTANTS.temp,
            particle_diameter=CONSTANTS.particle_diameter,
        )

        rows.append(
            {
                "key": key,
                "label": section.name,
                "diameter_mm": section.diameter * 1e3,
                "length_mm": section.length * 1e3,
                "continuum_above_mbar": float(
                    converter(p_cont_pa, "pa_to_mbar")
                ),
                "molecular_below_mbar": float(
                    converter(p_mol_pa, "pa_to_mbar")
                ),
            }
        )

    return pd.DataFrame(rows)


# =============================================================================
# Theoretische molekulare Leitwerte
# =============================================================================

def theoretical_conductances() -> pd.DataFrame:
    rows = []

    for key, section in SECTIONS.items():
        L_theory = conductance(
            case="molecular_tube",
            diameter=section.diameter,
            length=section.length,
            mean_thermal_speed=CONSTANTS.mean_thermal_speed,
        )

        rows.append(
            {
                "key": key,
                "label": section.name,
                "L_theory": L_theory,
            }
        )

    return pd.DataFrame(rows)


# =============================================================================
# Effektives Saugvermögen
# =============================================================================

def calculate_effective_pumping_speed() -> dict[str, float]:
    L_A = conductance(
        case="molecular_tube",
        diameter=INTAKE_DIAMETER,
        length=INTAKE_LENGTH,
        mean_thermal_speed=CONSTANTS.mean_thermal_speed,
    )

    L_B = conductance(
        case="molecular_opening",
        diameter=APERTURE_DIAMETER,
        mean_thermal_speed=CONSTANTS.mean_thermal_speed,
    )

    S_eff = effective_pumping_speed(
        S_ABS,
        L_A,
        L_B,
    )

    return {
        "S_abs": S_ABS,
        "L_A": L_A,
        "L_B": L_B,
        "S_eff": S_eff,
    }


# =============================================================================
# Experimentelle molekulare Leitwerte
# =============================================================================

def molecular_results(
    measurements: dict[str, pd.DataFrame],
    theory: pd.DataFrame,
    S_eff: float,
) -> pd.DataFrame:
    theory_dict = theory.set_index("key")["L_theory"].to_dict()
    rows = []

    for key in ("gross", "mittel"):
        df_end = last_time_window(measurements[key])

        p_N = float(df_end["p_N"].mean())
        p_H = float(df_end["p_H"].mean())

        q_pV = throughput(
            case="pumping",
            pressure=p_H,
            pumping_speed=S_eff,
        )

        L_exp = conductance(
            case="throughput",
            throughput=q_pV,
            p_upstream=p_N,
            p_downstream=p_H,
        )

        u_L_exp = conductance_uncert(
            p_N=p_N,
            p_H=p_H,
            effective_pumping_speed=S_eff,
            rel_pressure_uncert=REL_PRESSURE_UNCERT,
        )

        rows.append(
            {
                "key": key,
                "label": SECTIONS[key].name,
                "p_N": p_N,
                "p_H": p_H,
                "delta_p": p_N - p_H,
                "q_pV": float(q_pV),
                "L_theory": theory_dict[key],
                "L_exp": float(L_exp),
                "u_L_exp": u_L_exp,
            }
        )

    return pd.DataFrame(rows)


# =============================================================================
# Leitwertverhältnis groß / mittel
# =============================================================================

def conductance_ratio_results(
    results: pd.DataFrame,
) -> dict[str, float]:
    indexed = results.set_index("key")

    L_gross = float(indexed.loc["gross", "L_exp"])
    u_L_gross = float(indexed.loc["gross", "u_L_exp"])

    L_mittel = float(indexed.loc["mittel", "L_exp"])
    u_L_mittel = float(indexed.loc["mittel", "u_L_exp"])

    R_exp = L_gross / L_mittel

    u_R_exp = ratio_uncert(
        L_gross,
        u_L_gross,
        L_mittel,
        u_L_mittel,
    )

    gross = SECTIONS["gross"]
    mittel = SECTIONS["mittel"]

    R_theory = molecular_conductance_ratio(
        gross.diameter,
        gross.length,
        mittel.diameter,
        mittel.length,
    )

    u_R_theory = molecular_ratio_geom_uncert(
        gross.diameter,
        gross.diam_uncert,
        gross.length,
        gross.length_uncert,
        mittel.diameter,
        mittel.diam_uncert,
        mittel.length,
        mittel.length_uncert,
    )

    return {
        "R_exp": R_exp,
        "u_R_exp": u_R_exp,
        "R_theory": R_theory,
        "u_R_theory": u_R_theory,
    }


# =============================================================================
# Laminarer Bereich der kleinen Pumpstrecke
# =============================================================================

def laminar_analysis(
    df: pd.DataFrame,
    p_min: float = 5.0,
    p_max: float = 11.0,
):
    section = SECTIONS["klein"]

    mask = (
        (df["p_N"] >= p_min)
        & (df["p_N"] <= p_max)
    )

    data = (
        df.loc[mask, ["t", "p_N", "p_H"]]
        .copy()
        .sort_values("t")
    )

    if len(data) < 5:
        raise ValueError(
            f"Zu wenige Messpunkte im Bereich {p_min:g} bis {p_max:g} mbar "
            f"(gefunden: {len(data)})."
        )

    t = data["t"].to_numpy(dtype=float)
    p_N = data["p_N"].to_numpy(dtype=float)
    p_H = data["p_H"].to_numpy(dtype=float)

    p_mean = (p_N + p_H) / 2.0

    t0 = float(t[0])
    x = t - t0

    offset_0 = max(0.0, 0.8 * p_N[-1])
    amplitude_0 = max(p_N[0] - offset_0, 1e-12)
    duration = max(float(x[-1] - x[0]), 1.0)
    decay_0 = 1.0 / duration

    def fit_function(x_value, offset, amplitude, decay):
        return exponential_pressure(
            x_value,
            offset,
            amplitude,
            decay,
            0.0,
        )

    popt, pcov = curve_fit(
        fit_function,
        x,
        p_N,
        p0=(offset_0, amplitude_0, decay_0),
        bounds=(
            (0.0, 0.0, 0.0),
            (np.inf, np.inf, np.inf),
        ),
        maxfev=20000,
    )

    offset, amplitude, decay = map(float, popt)

    p_fit = exponential_pressure(
        x,
        offset,
        amplitude,
        decay,
        0.0,
    )

    dp_dt = exponential_pressure_derivative(
        x,
        amplitude,
        decay,
        0.0,
    )

    dN_dt = particle_number_derivative(
        V_N,
        dp_dt,
        k_B=CONSTANTS.k_B,
        temperatur=CONSTANTS.temp,
    )

    q_pV = throughput(
        case="decay",
        volume=V_N,
        pressure_deriv=dp_dt,
    )

    L_exp = conductance(
        case="throughput",
        throughput=q_pV,
        p_upstream=p_N,
        p_downstream=p_H,
    )

    L_theory = conductance(
        case="laminar_tube",
        diameter=section.diameter,
        length=section.length,
        p1=p_N,
        p2=p_H,
        viscosity=CONSTANTS.viscosity,
    )

    data["p_mean"] = p_mean
    data["p_fit"] = p_fit
    data["dp_dt"] = dp_dt
    data["dN_dt"] = dN_dt
    data["q_pV"] = q_pV
    data["L_exp"] = L_exp
    data["L_theory"] = L_theory

    parameter_uncert = np.sqrt(np.diag(pcov))

    fit_results = {
        "t0": t0,
        "offset": offset,
        "u_offset": float(parameter_uncert[0]),
        "amplitude": amplitude,
        "u_amplitude": float(parameter_uncert[1]),
        "decay": decay,
        "u_decay": float(parameter_uncert[2]),
    }

    return data, fit_results


# =============================================================================
# Main
# =============================================================================

def main():
    create_output_dirs()

    # data_io.py hat eigene historische Key-Namen; hier einmal normalisieren.
    measurements_raw = load_all_measurments()
    measurements = normalize_measurement_keys(measurements_raw)

    # Strömungsbereiche
    regimes = flow_regions()
    regimes.to_csv(
        TABLES / "flow_regimes.csv",
        index=False,
    )

    # Theoretische molekulare Leitwerte
    theory = theoretical_conductances()
    theory.to_csv(
        TABLES / "theoretical_conductances.csv",
        index=False,
    )

    # Effektives Saugvermögen
    pumping = calculate_effective_pumping_speed()
    pd.DataFrame([pumping]).to_csv(
        TABLES / "effective_pumping_speed.csv",
        index=False,
    )

    # Pumpkurven
    fig = plot_pump_curve(
        measurements,
        PLOTS / "pump_curves.pdf",
    )
    plt.close(fig)

    # Experimentelle molekulare Leitwerte
    molecular = molecular_results(
        measurements,
        theory,
        pumping["S_eff"],
    )
    molecular.to_csv(
        TABLES / "molecular_results.csv",
        index=False,
    )

    fig = plot_molecular_conductances(
        molecular,
        PLOTS / "molecular_conductances.pdf",
    )
    plt.close(fig)

    # Verhältnis groß / mittel
    ratio = conductance_ratio_results(molecular)
    pd.DataFrame([ratio]).to_csv(
        TABLES / "conductance_ratio.csv",
        index=False,
    )

    # Laminarer Bereich
    laminar, fit = laminar_analysis(
        measurements["klein"],
        p_min=5.0,
        p_max=11.0,
    )

    laminar.to_csv(
        TABLES / "laminar_results.csv",
        index=False,
    )

    pd.DataFrame([fit]).to_csv(
        TABLES / "laminar_fit.csv",
        index=False,
    )

    fig = plot_laminar_pressure(
        laminar,
        t=laminar["t"],
        p_fit=laminar["p_fit"],
        output_path=PLOTS / "laminar_pressure_fit.pdf",
    )
    plt.close(fig)

    fig = plot_laminar_conducatance(
        laminar["t"],
        laminar["L_exp"],
        laminar["L_theory"],
        output_path=PLOTS / "laminar_conductance.pdf",
    )
    plt.close(fig)

    print()
    print("Differentielles Pumpen")
    print("=======================")
    print(f"L_A   = {pumping['L_A']:.5g} L/s")
    print(f"L_B   = {pumping['L_B']:.5g} L/s")
    print(f"S_eff = {pumping['S_eff']:.5g} L/s")
    print()
    print(
        f"R_exp = {ratio['R_exp']:.4g} "
        f"+/- {ratio['u_R_exp']:.2g}"
    )
    print(
        f"R_theory = {ratio['R_theory']:.4g} "
        f"+/- {ratio['u_R_theory']:.2g}"
    )
    print()
    print(
        f"Decay-Konstante = {fit['decay']:.5g} "
        f"+/- {fit['u_decay']:.2g} 1/s"
    )
    print()
    print(f"Tabellen: {TABLES}")
    print(f"Plots:    {PLOTS}")


if __name__ == "__main__":
    main()