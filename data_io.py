import pandas as pd
from data import PATHS
from pathlib import Path

COLUMN_MAP = {
    "Zeit [s]" : "t",
    "Sensor 1 [mbar]" : "p_N",
    "Sensor 2 [mbar]" : "p_H",
}

FILES = {
    "keine" : PATHS.raw / "kmessung.csv",
    "gross" : PATHS.raw / "rohrgr.csv",
    "mittel" : PATHS.raw / "messung_rohr_mittel.csv",
    "klein" : PATHS.raw / "messung_rohr_klein.csv",
}





def load_measurment(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    

    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    df = df.rename(columns=COLUMN_MAP)

    df["delta_p"] = df["p_N"] - df["p_H"]
    df["p_mean"] = (df["p_N"] + df["p_H"]) / 2
    return df


def load_all_measurments() -> dict[str, pd.DataFrame]:
    return {key: load_measurment(path) for key, path in FILES.items()}