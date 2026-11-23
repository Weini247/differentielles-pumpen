import csv
from pathlib import Path

import numpy as np
import pandas as pd

from data import PATHS

COLUMN_MAP = {
    "Zeit [s]": "t",
    "Sensor 1 [mbar]": "p_N",
    "Sensor 2 [mbar]": "p_H",
}

FILENAMES = {
    "keine": "kmessung.csv",
    "gross": "rohrgr.csv",
    "mittel": "messung_rohr_mittel.csv",
    "klein": "messung_rohr_klein.csv",
}


def load_measurment(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Messdatei fehlt: {path}")
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source, strict=True)
            header = [field.strip() for field in next(reader, [])]
            missing = set(COLUMN_MAP) - set(header)
            if missing:
                raise ValueError(f"{path.name}: Fehlende Spalten: {', '.join(sorted(missing))}.")
            if any(header.count(column) != 1 for column in COLUMN_MAP):
                raise ValueError(f"{path.name}: Mehrdeutige Spaltennamen.")
            positions = [header.index(column) for column in COLUMN_MAP]
            rows = []
            for row in reader:
                if not row or (len(row) == 1 and not row[0].strip()):
                    continue
                if len(row) != len(header):
                    raise ValueError(f"{path.name}, Zeile {reader.line_num}: Anzahl der Felder passt nicht zum CSV-Kopf.")
                try:
                    rows.append([float(row[position]) for position in positions])
                except ValueError as exc:
                    raise ValueError(f"{path.name}, Zeile {reader.line_num}: Zeit und Druck müssen numerisch sein.") from exc
    except (csv.Error, UnicodeError) as exc:
        raise ValueError(f"{path.name}: CSV konnte nicht gelesen werden ({exc}).") from exc

    if not rows:
        raise ValueError(f"{path.name}: Keine Messwerte vorhanden.")
    df = pd.DataFrame(rows, columns=list(COLUMN_MAP.values()))
    if not np.isfinite(df.to_numpy()).all():
        raise ValueError(f"{path.name}: Zeit und Druck müssen endlich sein.")
    if (np.diff(df["t"]) <= 0).any():
        raise ValueError(f"{path.name}: Zeitstempel müssen streng ansteigen.")
    if (df[["p_N", "p_H"]] <= 0).to_numpy().any():
        raise ValueError(f"{path.name}: Druckwerte müssen positiv sein.")

    df["delta_p"] = df["p_N"] - df["p_H"]
    df["p_mean"] = (df["p_N"] + df["p_H"]) / 2
    return df


def load_all_measurments(raw_dir: Path = PATHS.raw) -> dict[str, pd.DataFrame]:
    return {
        name: load_measurment(Path(raw_dir) / filename)
        for name, filename in FILENAMES.items()
    }
