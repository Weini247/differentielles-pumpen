import numpy as np
import pandas as pd 
from dataclasses import dataclass
from pathlib import Path



@dataclass(frozen=True)
class PumpStreckenGeometrie:
    name : str
    diameter : float
    length : float
    diam_uncert : float
    length_uncert : float

CALIPER_UNCERT = 0.05e-3


@dataclass(frozen=True)
class physicalconstants:
    k_B : float = 1.380649e-23 
    temp: float = 293.15
    particle_diameter : float = 378e-12
    mean_thermal_speed : float = 463.0
    viscosity : float = 1.81e-5

    @property
    def collision(self) -> float:
        return np.pi * self.particle_diameter**2

CONSTANTS = physicalconstants()


PUMP_SECTIONS = {
    "gross" : PumpStreckenGeometrie(name="großes Durchlassrohr", diameter=2.9e-3, length=50e-3, diam_uncert=CALIPER_UNCERT, length_uncert=CALIPER_UNCERT),
    "medium" : PumpStreckenGeometrie(name="mittleres Durchlassrohr", diameter=2.0e-3, length=50e-3, diam_uncert=CALIPER_UNCERT, length_uncert=CALIPER_UNCERT),
    "klein" : PumpStreckenGeometrie(name="kleines Durchlassrohr", diameter=0.6e-3, length=20e-3, diam_uncert=CALIPER_UNCERT, length_uncert=CALIPER_UNCERT),
}

@dataclass(frozen=True)
class ProjectPaths:
    root : Path
    raw : Path
    processed : Path
    plots : Path
    tables : Path

ROOT = Path(__file__).resolve().parent

PATHS = ProjectPaths(root = ROOT, 
                     raw = ROOT / "data"/ "raw", 
                     processed = ROOT / "data" / "processed", 
                     plots = ROOT / "processed" / "plots", 
                     tables = ROOT / "processed" / "tables")
