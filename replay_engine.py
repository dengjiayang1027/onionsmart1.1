"""Replay state and synthetic intraday path generation for 蔥明錢."""
from __future__ import annotations

import numpy as np
import pandas as pd


def daily_path(row: pd.Series, day_index: int) -> list[float]:
    """Create a plausible OHLC-only intraday path; this is not historical tick data."""
    # Alternate path order to avoid always biasing toward one sequence.
    first, second = (float(row.High), float(row.Low)) if day_index % 2 == 0 else (float(row.Low), float(row.High))
    return [float(row.Open), first, second, float(row.Close)]


def interpolate_bar(row: pd.Series, day_index: int, progress: float) -> dict:
    """Interpolate an evolving candle across Open -> extreme -> extreme -> Close."""
    p = float(np.clip(progress, 0.0, 1.0))
    path = daily_path(row, day_index)
    # Four fixed 2-second phases over an 8-second candle:
    # Open -> first extreme -> second extreme -> Close.
    segment = min(int(p * 4), 2)
    local = min(p * 4 - segment, 1.0)
    price = path[segment] + (path[segment + 1] - path[segment]) * local
    visited = path[:segment + 1] + [price]
    return {"Open": path[0], "High": max(visited), "Low": min(visited), "Close": price}


def decision_progresses(count: int) -> set[float]:
    """Fixed intraday-time checkpoints, independent of price extrema."""
    return {round(x, 2) for x in np.linspace(.25, .75, count)} if count else set()
