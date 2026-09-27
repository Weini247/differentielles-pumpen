from data_io import FILES, load_measurment

def test_raw_files_exist():
    for path in FILES.values():
        assert(path.exists(), f"Datei fehlt {path}")

def test_measurments_can_be_loaded():
    for path in FILES.values():
        df = load_measurment(path)

        assert len(df) > 0
        assert "t" in df.columns
        assert "p_N" in df.columns
        assert "p_H" in df.columns

def test_pressure_values_are_pos():
    for path in FILES.values():
        df = load_measurment(path)
        assert (df["p_H"] > 0).all()
        assert (df["p_N"] > 0).all()
