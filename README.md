# Differentielles Pumpen – Auswertung

Fortgeschrittenen-Praktikum, HHU Düsseldorf.

## Ausführen
    pip install -r requirements.txt
    python analysis.py

Rohdaten in "data/raw/", Ausgabe nach "data/processed/{tables,plots}/".

## Dateien
- "data.py": Konstanten, Pumpstrecken-Geometrie, Pfade
- "data_io.py": Einlesen, Sensorzuordnung (Sensor 1 = p_N, Sensor 2 = p_H)
- "physics.py": Formeln
- "analysis.py": Aufgaben 3–8, Orchestrator
- "plots.py": Abbildungen