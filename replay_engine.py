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
    # Three equal segments occupy the full 8 seconds.
    segment = min(int(p * 3), 2)
    local = min(p * 3 - segment, 1.0)
    price = path[segment] + (path[segment + 1] - path[segment]) * local
    visited = path[:segment + 1] + [price]
    return {"Open": path[0], "High": max(visited), "Low": min(visited), "Close": price}


def decision_progresses(count: int) -> set[float]:
    """Fixed intraday-time checkpoints, independent of price extrema."""
    if count == 1:
        return {0.5}
    return {round(x, 4) for x in np.linspace(.18, .82, count)} if count else set()


def replay_finished(state, length):
    return state.i >= length - 1 and (
        state.mode == "Manual Replay" or state.progress >= 1.0
    )


def advance_clock(state, now, length):
    """Advance only active market time; decision and editing time never accumulates."""
    if not state.running or getattr(state, "editing_trade", False):
        state.last_tick = now
        return
    if state.pause_until:
        state.last_tick = now
        if now < state.pause_until:
            return
        state.pause_until = 0.0
        state.pause_reason = ""
        return
    elapsed = max(0.0, now - state.last_tick)
    state.last_tick = now
    target = min(1.0, state.progress + elapsed / state.dynamic_seconds)
    checkpoints = sorted(decision_progresses(state.decision_count))
    crossed = next((p for p in checkpoints if state.progress < p <= target), None)
    if crossed is not None:
        state.progress = crossed
        state.pause_until = now + state.decision_seconds
        state.pause_reason = "決策時間"
        return
    state.progress = target
    if target >= 1.0:
        if state.i < length - 1:
            state.i += 1
            state.progress = 0.0
        else:
            state.running = False
