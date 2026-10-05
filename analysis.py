from __future__ import annotations
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from data import CONSTANTS, PATHS, PUMP_SECTIONS
from data_io import load_all_measurments
import physics as physics
import plots as plots

S_ABS = 67 #Anleitung
INTAKE_LENGTH = 0.415 #laborbuch
INTAKE_DIAMETER = 34.8e-3 #rekonsturktion aus cf rohrgeometrie einfluss auf s_eff < 0.2%
APERTURE_DIAMETER = 1.0e-3 #laborbuch

V_N = 0.146 #Rekonstruktion: CF-Nippel Nebenkammer + Innenvolumen PKR 360 (Herstellerangabe), nicht direkt geme
U_V_N = 0.010


REL_PRESSURE_UNCERT = 0.30 #aufgabe 7c
LAST_SECONDS = 30.0 #auswertauswahl


LAMINAR_P_MIN = 5.0 #aufgabe 8a
LAMINAR_P_MAX = 11.0 #aufgabe 8a

TUBES = ("gross", "mittel", "klein")

def write_table(df : pd.DataFrame, filename : str):
    PATHS.tables.mkdir(parents=True, exist_ok=True)
    df.to_csv(PATHS.tables / filename, index = False)

def last_time_window(df : pd.DataFrame, seconds : float = LAST_SECONDS) -> pd.DataFrame:
    t_end = float(df["t"].iloc[-1])
    return df[df["t"] >= t_end - seconds]
def knudsen(p_mbar, diameter : float):
    return physics.knudsen_number(physics.converter(p_mbar, "mbar_to_pa"), diameter, k_B=CONSTANTS.k_B, temperatur_K = CONSTANTS.temp, particle_diameter = CONSTANTS.particle_diameter)

def rel_geom(key : str, diameter_power : float) -> float:
    s = PUMP_SECTIONS[key]
    return physics.geometry_rel_uncert(s.diameter, s.diam_uncert, s.length, s.length_uncert, diameter_power)


#aufgabe 3
def flow_regions() -> pd.DataFrame:
    rows = []
    for key in TUBES:
        s = PUMP_SECTIONS[key]
        p_cont, p_mol = (physics.knudsen_pressure(K, s.diameter, CONSTANTS.k_B, CONSTANTS.temp, CONSTANTS.particle_diameter) for K in (0.01, 0.5))
        rows.append({"key" : key, "label" : plots.RUN_LABELS[key], "diameter_mm" : s.diameter * 1e3, "length_mm" : s.length * 1e3, "continuum_above_mbar" : float(physics.converter(p_cont, "pa_to_mbar")), "molecular_below_mbar" : float(physics.converter(p_mol, "pa_to_mbar")), })
    return pd.DataFrame(rows)

#aufgabe 4
def theoretical_conductances() -> pd.DataFrame:
    rows = []
    for key in TUBES:
        s = PUMP_SECTIONS[key]
        L_mol = physics.conductance(case = "molecular_tube", diameter = s.diameter, length = s.length, mean_thermal_speed = CONSTANTS.mean_thermal_speed)
        C_lam = float(physics.conductance(case="laminar_tube", diameter=s.diameter, length=s.length, p1=1.0, p2=0.0, viscosity=CONSTANTS.viscosity))
        rows.append({
            "key" : key, 
            "label" : plots.RUN_LABELS[key],
            "diameter_mm" : s.diameter * 1e3,
            "length_mm" : s.length * 1e3,
            "L_theory" : L_mol,
            "u_L_theory" : L_mol * rel_geom(key, 3.0),
            "C_lam" : C_lam,
            "u_C_lam" : C_lam * rel_geom(key, 4.0),
        })
    return pd.DataFrame(rows)

#aufgabe 5
def calc_effective_pumping_speed() -> dict[str, float]:
    L_A = physics.conductance(case = "molecular_tube", diameter=INTAKE_DIAMETER, length = INTAKE_LENGTH, mean_thermal_speed = CONSTANTS.mean_thermal_speed)
    L_B = physics.conductance(case="molecular_opening", diameter=APERTURE_DIAMETER, mean_thermal_speed=CONSTANTS.mean_thermal_speed)

    return {"S_abs" : S_ABS, "L_A" : L_A, "L_B" : L_B, "S_eff" : physics.effective_pumping_speed(S_ABS, L_A, L_B),}


#aufgabe 7
def end_pressures(measurments : dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for key, df in measurments.items():
        w = last_time_window(df)
        p_N = float(w["p_N"].mean())
        p_H = float(w["p_H"].mean())

        rows.append({
            "key" : key,
            "label" : plots.RUN_LABELS[key],
            "n_points" : len(w),
            "t_start": float(w["t"].iloc[0]),
            "t_end" : float(w["t"].iloc[-1]),
            "p_N" : p_N,
            "u_p_N" : REL_PRESSURE_UNCERT * p_N,
            "p_H" : p_H,
            "u_p_H" : REL_PRESSURE_UNCERT * p_H,
            "K_N_tube" : float(knudsen(p_N, PUMP_SECTIONS[key].diameter)) if key in PUMP_SECTIONS else np.nan,
        })
    return pd.DataFrame(rows)

#aufgabe 7b
def molecular_results(end : pd.DataFrame, theory : pd.DataFrame, S_eff : float) -> pd.DataFrame:
    df = end.loc[end["key"].isin(TUBES), ["key", "label", "p_N", "p_H", "K_N_tube"]].copy()
    df = df.merge(theory[["key", "L_theory", "u_L_theory"]], on="key")

    df["delta_p"] = df["p_N"] - df["p_H"]
    df["q_pV"] = physics.throughput(case="pumping", pressure=df["p_H"], pumping_speed=S_eff)
    df["L_exp"] = physics.conductance(case = "throughput", throughput=df["q_pV"], p_upstream=df["p_N"], p_downstream=df["p_H"])
    df["u_L_exp"] = [physics.conductance_uncert(p_N = p_N, p_H = p_H, effective_pumping_speed = S_eff, rel_pressure_uncert = REL_PRESSURE_UNCERT) for p_N, p_H in zip(df["p_N"], df["p_H"])]
    df["L_exp_over_L_theory"] = df["L_exp"] / df["L_theory"]

    return df[["key", "label", "p_N", "p_H", "delta_p", "K_N_tube", "q_pV", "L_theory", "u_L_theory", "L_exp", "u_L_exp", "L_exp_over_L_theory"]]

def conductance_ratio_results(results : pd.DataFrame) -> dict[str, float]:
    r = results.set_index("key")
    g, m = r.loc["gross"], r.loc["mittel"]
    R_exp = g["L_exp"] / m["L_exp"]
    u_R_exp = physics.ratio_uncert(g["L_exp"], g["u_L_exp"], m["L_exp"], m["u_L_exp"])
    R_theory = g["L_theory"] / m["L_theory"]
    u_R_theory = physics.ratio_uncert(g["L_theory"], g["u_L_theory"], m["L_theory"], m["u_L_theory"])

    return {
        "R_exp" : float(R_exp),
        "u_R_exp" : u_R_exp,
        "R_theory" : float(R_theory),
        "u_R_theory" : u_R_theory,
        "deviation_sigma" : float(abs(R_exp - R_theory) / np.hypot(u_R_exp, u_R_theory))
    }

#aufgabe 8
def laminar_analysis(df : pd.DataFrame, p_min :float = LAMINAR_P_MIN, p_max : float = LAMINAR_P_MAX):
    section = PUMP_SECTIONS["klein"]

    mask = (df["p_N"] >= p_min) & (df["p_N"] <= p_max)

    idx = np.flatnonzero(mask.to_numpy())
    data = df.loc[mask, ["t", "p_N", "p_H", "p_mean"]].sort_values("t")

    t = data["t"].to_numpy(dtype=float)
    p_N = data["p_N"].to_numpy(dtype=float)
    p_H = data["p_H"].to_numpy(dtype = float)

    offset_0 = max(0.0, 0.8 * p_N[-1])
    t0 = float(t[0])
    x = t - t0

    p0 = (offset_0, max(p_N[0] - offset_0, 1e-12), 1.0 / max(float(x[-1]), 1.0))

    popt, pcov = curve_fit(lambda x_, C, A, b: physics.exponential_pressure(x_, C, A, b), x, p_N, p0=p0, bounds=((0.0, 0.0, 0.0), (np.inf, np.inf,np.inf)), maxfev=20000)

    offset, amplitude, decay = map(float, popt)
    u_offset, u_amplitude, u_decay = map(float, np.sqrt(np.diag(pcov)))

    p_fit = physics.exponential_pressure(x, offset, amplitude, decay)
    dp_dt = physics.exponential_pressure_derivative(x, amplitude, decay)
    q_pV = physics.throughput(case="decay", volume=V_N, pressure_deriv=dp_dt)
    L_exp = physics.conductance(case="throughput", throughput=q_pV, p_upstream=p_N, p_downstream=p_H)
    L_lam = physics.conductance(case="laminar_tube", diameter=section.diameter, length=section.length, p1=p_N, p2=p_H, viscosity=CONSTANTS.viscosity)

    data["K_mean"] = knudsen(data["p_mean"].to_numpy(), section.diameter)
    data["p_fit"] = p_fit
    data["dp_dt"] = dp_dt
    data["dN_dt"] = physics.particle_number_derivative(V_N, dp_dt, k_B=CONSTANTS.k_B, temperatur=CONSTANTS.temp)
    data["q_pV"] = q_pV
    data["L_exp"] = L_exp
    data["u_L_exp_VN"] = L_exp * U_V_N / V_N
    data["L_theory"] = L_lam
    data["u_L_lam_geom"] = L_lam * rel_geom("klein", 4.0)
    data["L_exp_over_L_theory"] = L_exp / L_lam

    fit_result = {
        "p_min" : p_min,
        "p_max" : p_max,
        "n_points" : len(data),
        "t0" : t0,
        "t_end" : float(t[-1]),
        "offset" : offset,
        "u_offset" : u_offset,
        "amplitude" : amplitude,
        "u_amplitude" : u_amplitude,
        "decay" : decay,
        "u_decay" : u_decay,
        "rms_residual" : float(np.sqrt(np.mean((p_N - p_fit) ** 2))),
        "V_N_A_b_mbarL_per_s" : V_N * amplitude * decay,
        "dN_dt_prefactor_per_s" : -float(data["dN_dt"].iloc[0]),
        "K_mean_min" : float(data["K_mean"].min()),
        "K_mean_max" : float(data["K_mean"].max()),
    }
    return data, fit_result

def main():
    measurements = load_all_measurments()
    write_table(flow_regions(), "flow_regimes_03.csv")
    write_table(theoretical_conductances(), "theoretical_conductances_04.csv")
    write_table(pd.DataFrame([calc_effective_pumping_speed()]), "effective_pumping_speed_05.csv")
    plt.close(plots.plot_pump_curve(measurements, PATHS.plots / "pump_curves_06.pdf"))
    write_table(end_pressures(measurements), "end_pressures_07a.csv")
    molecular = molecular_results(end_pressures(measurements), theoretical_conductances(), calc_effective_pumping_speed()["S_eff"])

    
    write_table(molecular, "molecular_results_07b.csv")
    plt.close(plots.plot_molecular_conductances(molecular, PATHS.plots/ "molecular_conductances_07b.pdf"))

    write_table(pd.DataFrame([conductance_ratio_results(molecular)]), "conductance_ratio_07c.csv")

    laminar, fit = laminar_analysis(measurements["klein"])
    write_table(laminar, "laminar_results_08.csv")
    write_table(pd.DataFrame([fit]), "laminar_fit_08.csv")

    plt.close(plots.plot_laminar_pressure(laminar, t = laminar["t"], p_fit = laminar["p_fit"], output_path = PATHS.plots / "laminar_pressure_fit_08.pdf"))
    plt.close(plots.plot_laminar_conducatance(laminar["t"], laminar["L_exp"], laminar["L_theory"], output_path  = PATHS.plots / "laminar_conductance_08.pdf"))

    
    print(f"Tabellen : {PATHS.tables}")
    print(f"Plots : {PATHS.plots}")


if __name__ == "__main__":
    main()
