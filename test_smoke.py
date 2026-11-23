import numpy as np
import pandas as pd
import pytest

import analysis
import physics
from data_io import FILENAMES, load_measurment
from export_results import main as export_results


@pytest.mark.parametrize(("body", "error"), [
    ("0,1,1\n0,2,1\n", "streng ansteigen"),
    ("0,2,1\n1,NaN,1\n", "endlich"),
    ("0,2,0\n", "positiv"),
    ("0,2,1,extra,5\n", "Anzahl der Felder"),
    ("", "Keine Messwerte"),
])
def test_invalid_measurement(tmp_path, body, error):
    path = tmp_path / "measurement.csv"
    path.write_text("Zeit [s],Sensor 1 [mbar],Sensor 2 [mbar]\n" + body, encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        load_measurment(path)


def test_reader_reports_missing_file_and_header(tmp_path):
    path = tmp_path / "measurement.csv"
    with pytest.raises(FileNotFoundError, match="Messdatei fehlt"):
        load_measurment(path)
    path.write_text("Zeit [s],Druck\n0,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Fehlende Spalten"):
        load_measurment(path)


def test_conductance_formulas():
    assert physics.effective_pumping_speed(12, 6, 12) == pytest.approx(3)
    assert physics.conductance(case="molecular_opening", diameter=0.001,
                               mean_thermal_speed=400) == pytest.approx(np.pi * 0.025)
    assert physics.conductance(case="throughput", throughput=6, p_upstream=5,
                               p_downstream=3) == pytest.approx(3)
    # Hagen–Poiseuille in SI, mit der mittleren Druckhöhe in Pa.
    diameter, length, viscosity, mean_pa = 0.0006, 0.02, 1.81e-5, 500
    expected = 1000 * np.pi * (diameter / 2)**4 * mean_pa / (8 * viscosity * length)
    assert physics.conductance(case="laminar_tube", diameter=diameter, length=length,
                               viscosity=viscosity, p1=7, p2=3) == pytest.approx(expected)
    with pytest.raises(ValueError, match="Druckdifferenz"):
        physics.conductance(case="throughput", throughput=6, p_upstream=[5, 3],
                            p_downstream=[3, 3])


def synthetic_decay():
    t = np.linspace(0, 90, 181)
    up = 3.0 + 7.9 * np.exp(-0.04 * t)
    down = up * 0.5
    return pd.DataFrame({"t": t, "p_N": up, "p_H": down, "p_mean": (up + down) / 2})


def test_fit_and_local_mass_balance():
    measurements = synthetic_decay()
    output, fit = analysis.laminar_analysis(measurements)
    assert fit["decay"] == pytest.approx(0.04)
    assert fit["offset"] == pytest.approx(3)
    assert output["L_exp"].iloc[0] == pytest.approx(
        analysis.V_N * 0.04 * 7.9 / (10.9 * 0.5))
    with pytest.raises(ValueError, match="mindestens vier"):
        analysis.laminar_analysis(measurements, p_min=20, p_max=30)
    with pytest.raises(ValueError, match="größer"):
        analysis.laminar_analysis(measurements.assign(p_H=measurements.p_N))


def test_end_to_end_public_export(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    t = np.linspace(0, 90, 181)
    decay = synthetic_decay()
    for filename in FILENAMES.values():
        decay[["t", "p_N", "p_H"]].set_axis([
            "Zeit [s]", "Sensor 1 [mbar]", "Sensor 2 [mbar]",
        ], axis=1).assign(**{"": ""}).to_csv(raw_dir / filename, index=False)
    output = tmp_path / "results"
    export_results(["--raw-dir", str(raw_dir), "--output-dir", str(output)])
    assert {path.name for path in output.iterdir()} == {
        "pumping_speed.csv", "molecular_conductance.csv", "molecular_ratio.csv",
        "pressure_decay_fit.csv", "conductance_by_pressure.csv",
        "molecular_conductance.svg", "conductance_by_pressure.svg",
    }
    bins = pd.read_csv(output / "conductance_by_pressure.csv")
    assert (bins["n"] >= 5).all()
    assert (bins["pressure_high_mbar"] - bins["pressure_low_mbar"] == 1).all()
    assert {"t", "p_N", "p_H"}.isdisjoint(bins.columns)
    before = {f.name: f.read_bytes() for f in output.glob("*.svg")}
    export_results(["--figures-only", "--output-dir", str(output)])
    assert {f.name: f.read_bytes() for f in output.glob("*.svg")} == before
