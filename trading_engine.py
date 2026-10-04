"""Shared manual/auto-ready position and trade record operations."""
from datetime import datetime


def open_position(state, side, reasons, symbol="2330 台積電", mode="Manual"):
    if state.pos:
        close_position(state, "Reverse", reasons)
    row = state.current_bar
    state.pos = side
    state.entry = float(row["Close"])
    state.entry_time = row["Date"]
    state.entry_replay = state.i
    state.entry_qty = int(state.qty)
    state.entry_sl = float(state.sl_pct or 0)
    state.entry_tp = float(state.tp_pct or 0)
    state.trade_mode = mode


def close_position(state, exit_type="Manual", reasons=None):
    if not state.pos:
        return
    row = state.current_bar
    px = float(row["Close"])
    pnl_pct = ((px - state.entry) / state.entry) * state.pos * 100
    qty = int(state.entry_qty)
    state.trades.append({
        "#": len(state.trades) + 1, "日期": str(state.entry_time.date()),
        "Replay 時點": int(state.entry_replay), "股票": "2330 台積電",
        "方向": "BUY" if state.pos == 1 else "SELL", "進場": round(state.entry, 2),
        "出場": round(px, 2), "數量": qty, "部位": "多" if state.pos == 1 else "空",
        "SL %": state.entry_sl, "TP %": state.entry_tp,
        "損益": round(pnl_pct / 100 * state.entry * qty, 0), "R": round(pnl_pct / 3.0, 2),
        "觸發規則": "、".join(reasons or []), "持有日數": int(state.i - state.entry_replay),
        "交易模式": state.trade_mode, "出場原因": exit_type,
    })
    state.pos, state.entry, state.entry_time = 0, None, None
    state.entry_qty = 0

