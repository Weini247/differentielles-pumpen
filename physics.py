from __future__ import annotations
import numpy as np


def converter(value : float, case : str):
    if case == "liter_to_m3":
        return np.asarray(value) * 1e-3
    elif case == "m3_to_liter":
        return np.asarray(value) / 1e-3
    elif case == "mbar_to_pa":
        return np.asarray(value) * 100.0
    elif case == "pa_to_mbar":
        return np.asarray(value) / 100.0
    else:
        raise ValueError(f"{case} case ist nicht definiert")


#========================================================================================
def collision_cross_section(particle_diameter : float) -> float:
    return float(np.pi * particle_diameter**2)

def mean_free_path(p_pa, *, k_B : float, temperatur_K : float, particle_diameter : float):
    sigma = collision_cross_section(particle_diameter)
    return k_B * temperatur_K / (np.sqrt(2.0) * np.asarray(p_pa) * sigma)

def knudsen_number(p_pa, diameter : float, *, k_B : float, temperatur_K : float, particle_diameter : float):
    return mean_free_path(p_pa, k_B=k_B, temperatur_K=temperatur_K, particle_diameter=particle_diameter) / diameter

def knudsen_pressure(K : float, diameter : float, k_B : float, temperatur : float, particle_diameter : float) -> float:
    sigma = collision_cross_section(particle_diameter)
    return float(k_B * temperatur / (np.sqrt(2.0) * sigma * diameter * K ))

def knudsen_classification(K : float) -> str:
    if K < 0.01:
        return "Kontinuum"
    if K <= 0.5:
        return "Übergang"
    return "Molekular"


#========================================================================================
def conductance(*, case :str, diameter=None, length=None,mean_thermal_speed=None, p1 = None, p2 = None, viscosity = None, throughput = None, p_upstream = None, p_downstream = None):
    if case == "molecular_tube":
        L = mean_thermal_speed * np.pi * diameter**3 / (12.0 * length)
        return float(converter(value=L, case="m3_to_liter"))
    elif case == "molecular_opening":
        area = np.pi * diameter**2 / 4.0
        L = 0.25 * mean_thermal_speed * area
        return float(converter(L, "m3_to_liter"))
    elif case == "laminar_tube":
        p_sum = converter(p1, "mbar_to_pa") + converter(p2, "mbar_to_pa")
        L = np.pi * diameter**4 * p_sum / (256.0 * viscosity * length)
        return converter(L, "m3_to_liter")
    elif case == "throughput":
        p_upstream = np.asarray(p_upstream, dtype=float)
        p_downstream = np.asarray(p_downstream, dtype=float)
        gap = p_upstream - p_downstream
        scale = np.maximum(np.abs(p_upstream), np.abs(p_downstream))
        if np.any(~np.isfinite(gap) | (gap <= np.finfo(float).eps * scale)):
            raise ValueError("Leitwert erfordert p_upstream > p_downstream mit auflösbarer Druckdifferenz.")
        return np.asarray(throughput) / gap
    else: 
        raise ValueError(f"{case} case nicht definiert")

def throughput(*, case :str, pressure = None, pumping_speed = None, volume = None, pressure_deriv = None):
    if case == "pumping":
        return np.asarray(pressure) * pumping_speed
    if case == "decay":
        return -volume * np.asarray(pressure_deriv)
    raise ValueError(f"{case} case nicht def")

def effective_pumping_speed(absolute_pumping_speed, *conductance : float) -> float:
    start = 1.0 / absolute_pumping_speed
    for L in conductance:
        start += 1.0/L
    
    return 1.0 / start


#========================================================================================
def exponential_pressure(t, offset, amplitude, decay, t0 : float = 0.0):
    t = np.asarray(t)
    return offset + amplitude * np.exp(-decay * (t - t0))

def exponential_pressure_derivative(t, amplitude, decay, t0 : float = 0.0):
    t = np.asarray(t)
    return -amplitude * decay * np.exp(-decay * (t-t0))

def particle_number_derivative(volume, dp_dt, *, k_B : float, temperatur : float):
    V = converter(volume, "liter_to_m3")
    dp_dt = converter(dp_dt, "mbar_to_pa")
    return V * dp_dt / (k_B * temperatur)


#========================================================================================
def conductance_uncert(p_N :float , p_H :float , effective_pumping_speed :float , *, rel_pressure_uncert :float = .30, pumping_speed_uncert :float = .00)  -> float:
    p_N = float(p_N)
    p_H = float(p_H)
    S = float(effective_pumping_speed)
    dp = p_N - p_H

    if not np.isfinite(dp) or dp <= np.finfo(float).eps * max(abs(p_N), abs(p_H)):
        raise ValueError("Unsicherheitsrechnung erfordert p_N > p_H mit auflösbarer Druckdifferenz.")

    u_p_N = rel_pressure_uncert * p_N
    u_p_H = rel_pressure_uncert * p_H
    u_S = pumping_speed_uncert

    dL_dp_H = S * p_N / dp**2
    dL_dp_N = -S * p_H / dp**2
    dL_dS = p_H / dp

    return float(np.sqrt((dL_dp_H * u_p_H) ** 2 + (dL_dp_N * u_p_N) ** 2 + (dL_dS * u_S) ** 2))

def ratio_uncert(value1 : float, uncert1 : float, value2 : float, uncert2 : float) -> float:
    ratio = value1 / value2
    rel = np.sqrt((uncert1 / value1) ** 2 + (uncert2 / value2) **2)
    return float(ratio * rel)

def geometry_rel_uncert(diameter: float, diam_uncert : float, length : float, length_uncert : float, diameter_power : float) -> float:
    return float(np.sqrt((diameter_power * diam_uncert / diameter) ** 2 + (length_uncert / length) **2))
