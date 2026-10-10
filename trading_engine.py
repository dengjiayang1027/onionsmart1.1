"""Shared manual/auto-ready position and trade record operations."""
def market_label(state):
    return f"{getattr(state, 'market_symbol', '2330')} {getattr(state, 'market_name', '台積電')}"


def log_order(state, action, reasons=None):
    """Record each submitted trading-panel action at the current replay price/time."""
    row = state.current_bar
    state.order_events.append({
        "日期": str(row["Date"].date()), "Replay 時點": int(state.i),
        "股票": market_label(state), "操作": action,
        "價格": round(float(row["Close"]), 2), "數量": int(state.qty),
        "部位": "多" if state.pos == 1 else ("空" if state.pos == -1 else "空手"),
        "SL %": float(getattr(state, "sl_pct", 0) or 0),
        "TP %": float(getattr(state, "tp_pct", 0) or 0),
        "交易理由": "、".join(reasons or []), "交易模式": "Manual",
    })


def open_position(state, side, reasons, symbol=None, mode="Manual"):
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
    state.entry_symbol = symbol or market_label(state)
    state.entry_reasons = list(reasons or [])
    log_order(state, "BUY 做多" if side == 1 else "SELL 做空", reasons)


def close_position(state, exit_type="Manual", reasons=None):
    if not state.pos:
        return
    row = state.current_bar
    px = float(row["Close"])
    pnl_pct = ((px - state.entry) / state.entry) * state.pos * 100
    qty = int(state.entry_qty)
    state.trades.append({
        "#": len(state.trades) + 1, "日期": str(state.entry_time.date()),
        "Replay 時點": int(state.entry_replay), "股票": getattr(state, "entry_symbol", market_label(state)),
        "出場日期": str(row["Date"].date()), "出場Replay時點": int(state.i),
        "方向": "BUY" if state.pos == 1 else "SELL", "進場": round(state.entry, 2),
        "出場": round(px, 2), "數量": qty, "部位": "多" if state.pos == 1 else "空",
        "SL %": state.entry_sl, "TP %": state.entry_tp,
        "損益": round(pnl_pct / 100 * state.entry * qty, 0), "R": round(pnl_pct / 3.0, 2),
        "觸發規則": "、".join(reasons or []), "持有日數": int(state.i - state.entry_replay),
        "交易模式": state.trade_mode, "出場原因": exit_type,
        "進場理由": "、".join(getattr(state, "entry_reasons", [])),
    })
    log_order(state, "平倉", reasons)
    state.pos, state.entry, state.entry_time = 0, None, None
    state.entry_qty = 0
