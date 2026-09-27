import pandas as pd
from data import Paths
from pathlib import Path

COLUMN_MAP = {
    "Zeit [s]" : "t",
    "Sensor 1 [mbar]" : "p_H",
    "Sensor 2 [mbar]" : "p_N",
}

FILES = {
    "baseline" : Paths.raw / "kmessung.csv",
    "klein" : Paths.raw / "messung_rohr_klein.csv",
    "mittel" : Paths.raw / "messung_rohr_mittel.csv",
    "groß" : Paths.raw / "messung_rohr_groß.csv",
}

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PLOTS_DIR = PROCESSED_DIR / "plots"
TABLES_DIR = PROCESSED_DIR / "tables"



def load_measurment(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = pd.rename(columns=COLUMN_MAP)

    df["delta_p"] = df["p_N"] - df["p_H"]
    df["p_mean"] = (df["p_N"] + df["p_H"]) / 2
    return df


def load_all_measurments() -> dict[str, pd.DataFrame]:
    return {key: load_measurment(path) for key, path in FILES.items()}