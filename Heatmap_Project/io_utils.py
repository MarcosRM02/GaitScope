import json
from typing import List, Tuple

import pandas as pd


def read_points(path: str) -> List[Tuple[float, float]]:
    """Read points JSON file: array of {"x":..., "y":...}

    Returns list of (x,y) floats.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    pts = []
    for item in data:
        x = float(item.get("x", 0.0))
        y = float(item.get("y", 0.0))
        pts.append((x, y))
    return pts


def read_sequence(path: str) -> List[List[int]]:
    """Read a CSV-like sequence file using pandas and keep columns 0..31.

    Returns list of frames where each frame is a list of 32 integers (padded with zeros if needed).
    """
    expected_cols = 32
    # let pandas detect separator; engine='python' handles irregular files better
    df = pd.read_csv(path, header=None, sep=None, engine='python', comment='#', na_values=[''], keep_default_na=False)
    # keep only first expected_cols columns
    if df.shape[1] < expected_cols:
        # add missing columns filled with zeros
        for c in range(df.shape[1], expected_cols):
            df[c] = 0
    df2 = df.iloc[:, :expected_cols].fillna(0)
    # coerce to numeric then to int
    df2 = df2.apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
    return df2.values.tolist()
