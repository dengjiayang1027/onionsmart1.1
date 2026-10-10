"""Personal replay scorecard metrics and nine-class personality mapping."""
from __future__ import annotations

import numpy as np
import pandas as pd


METRICS = ("守", "效", "買", "賣", "盈", "穩")
NEUTRAL_SCORE = 3.0
MIN_BEHAVIOR_SAMPLES = 3

ROLE_BY_PAIR = {
    frozenset(("守", "效")): "魔劍士",
    frozenset(("守", "買")): "戰士",
    frozenset(("買", "穩")): "戰士",
    frozenset(("守", "賣")): "騎兵",
    frozenset(("賣", "盈")): "騎兵",
    frozenset(("守", "盈")): "重盾手",
    frozenset(("盈", "穩")): "重盾手",
    frozenset(("守", "穩")): "坦克",
    frozenset(("效", "穩")): "坦克",
    frozenset(("賣", "穩")): "坦克",
    frozenset(("效", "買")): "狙擊手",
    frozenset(("效", "賣")): "魔導士",
    frozenset(("效", "盈")): "鍊金術士",
    frozenset(("買", "盈")): "鍊金術士",
    frozenset(("買", "賣")): "遊俠",
}

ROLE_DESCRIPTIONS = {
    "魔劍士": "守住本金，兼顧交易效率。",
    "戰士": "穩健防守，耐心尋找買點。",
    "騎兵": "控制風險，掌握出場時機。",
    "重盾手": "降低回撤，守住獲利。",
    "坦克": "重視防守，維持沉穩節奏。",
    "狙擊手": "衡量風險，精準尋找買點。",
    "魔導士": "理性評估，掌握出場時機。",
    "鍊金術士": "提升風險效率，保留交易成果。",
    "遊俠": "靈活掌握進出場。",
}

ROLE_IMAGES = {
    "魔劍士": "S__11411467_0.jpg",
    "戰士": "S__11411466_0.jpg",
    "騎兵": "S__11411465_0.jpg",
    "重盾手": "S__11411464_0.jpg",
    "坦克": "S__11411463_0.jpg",
    "狙擊手": "S__11411462_0.jpg",
    "魔導士": "S__11411461_0.jpg",
    "鍊金術士": "S__11411460_0.jpg",
    "遊俠": "S__11411468_0.jpg",
}


def _bounded_score(value: float) -> float:
    return round(float(np.clip(value, 1.0, 5.0)), 1)


def _integer(value, fallback=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def compute_scorecard(
    trades: pd.DataFrame,
    bars: pd.DataFrame,
    start_index: int,
    end_index: int,
    starting_cash: float = 100_000.0,
) -> dict:
    """Return 1–5 skill scores, samples, raw metrics, and the top-two role.

    Insufficient samples use a neutral 3/5 for the radar and are labeled in
    ``notes``. Buy/sell/retention/stability require three observations.
    """
    trade_rows = trades.to_dict("records") if not trades.empty else []
    bars = bars.reset_index(drop=True)
    n_bars = len(bars)
    if n_bars == 0:
        return {
            "scores": {metric: NEUTRAL_SCORE for metric in METRICS},
            "samples": {metric: 0 for metric in METRICS},
            "notes": {metric: "沒有可用行情資料，暫以中間分 3/5 顯示。" for metric in METRICS},
            "raw": {}, "role": None, "top_pair": [], "role_description": None,
            "role_image": None, "total_profit": 0.0, "win_rate": 0.0,
            "trade_count": 0, "valid_metric_count": 0, "max_drawdown": 0.0,
        }
    start = max(0, min(_integer(start_index), max(0, n_bars - 1)))
    end = max(start, min(_integer(end_index), max(0, n_bars - 1)))
    valid_rows = []
    for trade in trade_rows:
        entry_i = _integer(trade.get("Replay 時點"), -1)
        exit_i = _integer(trade.get("出場Replay時點"), entry_i)
        side_text = str(trade.get("方向", "BUY")).upper()
        side = -1 if side_text in ("SELL", "SHORT", "空") else 1
        entry = float(trade.get("進場", 0) or 0)
        exit_price = float(trade.get("出場", 0) or 0)
        pnl = float(trade.get("損益", 0) or 0)
        if entry_i < 0 or exit_i < 0 or entry <= 0:
            continue
        valid_rows.append({
            "entry_i": entry_i,
            "exit_i": exit_i,
            "side": side,
            "entry": entry,
            "exit": exit_price,
            "pnl": pnl,
            "r": float(trade.get("R", 0) or 0),
            "qty": max(1, _integer(trade.get("數量"), 1)),
        })

    samples = {metric: 0 for metric in METRICS}
    scores = {metric: NEUTRAL_SCORE for metric in METRICS}
    notes = {metric: "資料不足，暫以中間分 3/5 顯示。" for metric in METRICS}
    raw = {}

    if valid_rows:
        samples["守"] = len(valid_rows)
        samples["效"] = len(valid_rows)
        pnl_by_exit = {}
        for item in valid_rows:
            if start <= item["exit_i"] <= end:
                pnl_by_exit[item["exit_i"]] = pnl_by_exit.get(item["exit_i"], 0.0) + item["pnl"]

        equity = float(starting_cash)
        peak = equity
        max_drawdown = 0.0
        for index in range(start, end + 1):
            equity += pnl_by_exit.get(index, 0.0)
            peak = max(peak, equity)
            if peak > 0:
                max_drawdown = max(max_drawdown, (peak - equity) / peak)
        raw["最大回撤率"] = max_drawdown
        scores["守"] = _bounded_score(5.0 - 4.0 * min(max_drawdown / 0.30, 1.0))
        notes["守"] = f"最大資產回撤 {max_drawdown:.1%}；回撤越小，分數越高。"

        gains = sum(max(item["pnl"], 0.0) for item in valid_rows)
        losses = sum(abs(min(item["pnl"], 0.0)) for item in valid_rows)
        profit_factor = gains / losses if losses else (2.0 if gains > 0 else 0.0)
        raw["獲利因子"] = profit_factor
        scores["效"] = _bounded_score(1.0 + 2.0 * min(profit_factor, 2.0))
        notes["效"] = f"獲利因子 {profit_factor:.2f}；總獲利相對總虧損越高，分數越高。"

        buy_outcomes = []
        sell_outcomes = []
        retention = []
        r_values = []
        for item in valid_rows:
            entry_i, exit_i, side = item["entry_i"], item["exit_i"], item["side"]
            if 0 <= entry_i + 1 <= end and entry_i + 1 < n_bars:
                next_close = float(bars.iloc[entry_i + 1]["Close"])
                buy_outcomes.append((next_close - item["entry"]) * side >= 0)
            if 0 <= exit_i + 1 <= end and exit_i + 1 < n_bars:
                next_close = float(bars.iloc[exit_i + 1]["Close"])
                sell_outcomes.append((next_close - item["exit"]) * side <= 0)

            if 0 <= entry_i <= exit_i < n_bars:
                window = bars.iloc[entry_i:exit_i + 1]
                if side == 1:
                    favorable_move = max(0.0, float(window["High"].max()) - item["entry"])
                else:
                    favorable_move = max(0.0, item["entry"] - float(window["Low"].min()))
                realized_move = (item["exit"] - item["entry"]) * side
                if favorable_move > 0:
                    retention.append(float(np.clip(realized_move / favorable_move, 0.0, 1.0)))
            r_values.append(item["r"])

        samples["買"] = len(buy_outcomes)
        if len(buy_outcomes) >= MIN_BEHAVIOR_SAMPLES:
            rate = float(np.mean(buy_outcomes))
            raw["進場後有利頻率"] = rate
            scores["買"] = _bounded_score(1.0 + 4.0 * rate)
            notes["買"] = f"進場後下一根 K 棒走勢有利的比例 {rate:.0%}。"
        else:
            notes["買"] = f"有效樣本 {len(buy_outcomes)}/{MIN_BEHAVIOR_SAMPLES}，不足時以 3/5 顯示。"

        samples["賣"] = len(sell_outcomes)
        if len(sell_outcomes) >= MIN_BEHAVIOR_SAMPLES:
            rate = float(np.mean(sell_outcomes))
            raw["出場後未延續有利走勢頻率"] = rate
            scores["賣"] = _bounded_score(1.0 + 4.0 * rate)
            notes["賣"] = f"出場後行情未繼續朝持倉有利方向走的比例 {rate:.0%}。"
        else:
            notes["賣"] = f"有效樣本 {len(sell_outcomes)}/{MIN_BEHAVIOR_SAMPLES}，不足時以 3/5 顯示。"

        samples["盈"] = len(retention)
        if len(retention) >= MIN_BEHAVIOR_SAMPLES:
            mean_capture = float(np.mean(retention))
            raw["平均獲利保留率"] = mean_capture
            scores["盈"] = _bounded_score(1.0 + 4.0 * mean_capture)
            notes["盈"] = f"平均保留持倉期間最大浮盈的比例 {mean_capture:.0%}。"
        else:
            notes["盈"] = f"有效樣本 {len(retention)}/{MIN_BEHAVIOR_SAMPLES}，不足時以 3/5 顯示。"

        samples["穩"] = len(r_values)
        if len(r_values) >= MIN_BEHAVIOR_SAMPLES:
            r_mean = float(np.mean(r_values))
            r_std = float(np.std(r_values))
            raw["R 標準差"] = r_std
            stability = 5.0 - 4.0 * min(r_std / 2.0, 1.0)
            if r_mean <= 0:
                stability = min(stability, 2.5)
            scores["穩"] = _bounded_score(stability)
            notes["穩"] = f"交易 R 值波動 {r_std:.2f}；表現越穩定且平均為正，分數越高。"
        else:
            notes["穩"] = f"有效樣本 {len(r_values)}/{MIN_BEHAVIOR_SAMPLES}，不足時以 3/5 顯示。"

    eligible = [metric for metric in METRICS if samples[metric] > 0]
    role = None
    top_pair = []
    if len(eligible) >= 2:
        rank = {metric: idx for idx, metric in enumerate(METRICS)}
        ranked = sorted(eligible, key=lambda metric: (-scores[metric], rank[metric]))
        top_pair = ranked[:2]
        role = ROLE_BY_PAIR.get(frozenset(top_pair))

    equity_values = [float(starting_cash)]
    running = float(starting_cash)
    for item in sorted(valid_rows, key=lambda x: x["exit_i"]):
        running += item["pnl"]
        equity_values.append(running)
    total_profit = sum(item["pnl"] for item in valid_rows)
    win_rate = float(np.mean([item["pnl"] > 0 for item in valid_rows])) if valid_rows else 0.0

    return {
        "scores": scores,
        "samples": samples,
        "notes": notes,
        "raw": raw,
        "role": role,
        "top_pair": top_pair,
        "role_description": ROLE_DESCRIPTIONS.get(role),
        "role_image": ROLE_IMAGES.get(role),
        "total_profit": total_profit,
        "win_rate": win_rate,
        "trade_count": len(valid_rows),
        "valid_metric_count": len(eligible),
        "max_drawdown": float(raw.get("最大回撤率", 0.0)),
    }
