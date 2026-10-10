"""Official daily historical bars for Taiwan listed and OTC securities."""
from __future__ import annotations

import json
import time
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

TWSE_BASE = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
TWSE_LIST = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_LIST = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
TPEX_HISTORY = "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php"


def _get_json(url: str) -> dict | list:
    request = Request(url, headers={"User-Agent": "OnionSmartReplay/1.0", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"無法讀取交易所行情資料：{exc}") from exc


@st.cache_data(ttl=86400, show_spinner=False)
def listed_instruments() -> list[dict[str, str]]:
    """Return securities present in the TWSE's latest daily market feed."""
    payload = _get_json(TWSE_LIST)
    if not isinstance(payload, list):
        raise RuntimeError("證交所標的清單格式暫時無法辨識。")
    records = []
    for item in payload:
        code = str(item.get("Code", item.get("證券代號", ""))).strip()
        name = str(item.get("Name", item.get("證券名稱", ""))).strip()
        if code and name:
            records.append({"code": code, "name": name})
    if not records:
        raise RuntimeError("證交所目前未回傳可用的標的清單。")
    return records


@st.cache_data(ttl=86400, show_spinner=False)
def otc_instruments() -> list[dict[str, str]]:
    """Return numeric main-board securities from TPEx's latest daily feed."""
    payload = _get_json(TPEX_LIST)
    if not isinstance(payload, list):
        raise RuntimeError("櫃買中心標的清單格式暫時無法辨識。")
    records = []
    for item in payload:
        code = str(item.get("SecuritiesCompanyCode", item.get("Code", item.get("證券代號", "")))).strip()
        name = str(item.get("CompanyName", item.get("SecuritiesCompanyName", item.get("Name", item.get("證券名稱", ""))))).strip()
        # Keep ordinary numeric stock and ETF codes; the feed also contains warrants.
        if code.isdigit() and 4 <= len(code) <= 5 and name:
            records.append({"code": code, "name": name})
    if not records:
        raise RuntimeError("櫃買中心目前未回傳可用的上櫃標的清單。")
    return records


@st.cache_data(ttl=86400, show_spinner=False)
def _monthly_bars(symbol: str, month: str) -> list[list[str]]:
    params = urlencode({"date": month + "01", "response": "json", "stockNo": symbol})
    payload = _get_json(f"{TWSE_BASE}?{params}")
    if not isinstance(payload, dict):
        return []
    # TWSE reports an empty month using a human-readable stat and no data rows.
    return payload.get("data", []) or []


def _number(value: str) -> float:
    value = str(value).replace(",", "").strip()
    if not value or value in {"--", "---", "X0.00"}:
        return float("nan")
    return float(value)


def fetch_twse_daily(symbol: str, start: date, end: date) -> pd.DataFrame:
    """Fetch and normalize daily OHLCV bars in the inclusive date range."""
    if start > end:
        raise ValueError("開始日期不可晚於結束日期。")
    if (end.year - start.year) * 12 + end.month - start.month > 24:
        raise ValueError("單次最多查詢 25 個月，請縮小日期區間。")

    months = pd.period_range(start=start.strftime("%Y-%m"), end=end.strftime("%Y-%m"), freq="M")
    rows: list[list[str]] = []
    for offset, month in enumerate(months):
        if offset:
            time.sleep(0.15)
        rows.extend(_monthly_bars(str(symbol), month.strftime("%Y%m")))

    parsed = []
    for row in rows:
        if len(row) < 7:
            continue
        try:
            # TWSE date strings use the Republic of China calendar (e.g. 112/01/03).
            y, m, d = (int(part) for part in row[0].split("/"))
            parsed.append({
                "Date": date(y + 1911, m, d),
                "Volume": _number(row[1]),  # TWSE reports shares, not lots.
                "Open": _number(row[3]),
                "High": _number(row[4]),
                "Low": _number(row[5]),
                "Close": _number(row[6]),
            })
        except (ValueError, TypeError):
            continue

    bars = pd.DataFrame(parsed, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    if bars.empty:
        raise RuntimeError(f"證交所沒有回傳 {symbol} 在所選期間的日線資料。")
    bars["Date"] = pd.to_datetime(bars["Date"])
    bars = bars.dropna(subset=["Open", "High", "Low", "Close"])
    bars = bars[(bars["Date"].dt.date >= start) & (bars["Date"].dt.date <= end)]
    bars = bars.sort_values("Date").drop_duplicates("Date").reset_index(drop=True)
    if bars.empty:
        raise RuntimeError("所選區間沒有可用的 OHLC 日線資料。")
    return bars


@st.cache_data(ttl=86400, show_spinner=False)
def _tpex_monthly_bars(symbol: str, month: str) -> list[list[str]]:
    """Fetch one TPEx main-board security's daily rows for a ROC calendar month."""
    year, month_num = int(month[:4]), int(month[4:])
    roc_month = f"{year - 1911}/{month_num:02d}"
    params = urlencode({"d": roc_month, "stkno": symbol})
    payload = _get_json(f"{TPEX_HISTORY}?{params}")
    if not isinstance(payload, dict):
        return []
    return payload.get("aaData", payload.get("data", [])) or []


def fetch_tpex_daily(symbol: str, start: date, end: date) -> pd.DataFrame:
    """Fetch and normalize TPEx monthly daily OHLCV in the inclusive date range."""
    if start > end:
        raise ValueError("開始日期不可晚於結束日期。")
    if (end.year - start.year) * 12 + end.month - start.month > 24:
        raise ValueError("單次最多查詢 25 個月，請縮小日期區間。")

    months = pd.period_range(start=start.strftime("%Y-%m"), end=end.strftime("%Y-%m"), freq="M")
    rows: list[list[str]] = []
    for offset, month in enumerate(months):
        if offset:
            time.sleep(0.15)
        rows.extend(_tpex_monthly_bars(str(symbol), month.strftime("%Y%m")))

    parsed = []
    for row in rows:
        if len(row) < 8:
            continue
        try:
            # TPEx S43 fields: date, shares, amount, open, high, low, close, change, count.
            y, m, d = (int(part) for part in str(row[0]).split("/"))
            parsed.append({
                "Date": date(y + 1911, m, d),
                "Volume": _number(row[1]),
                "Open": _number(row[3]),
                "High": _number(row[4]),
                "Low": _number(row[5]),
                "Close": _number(row[6]),
            })
        except (ValueError, TypeError):
            continue

    bars = pd.DataFrame(parsed, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    if bars.empty:
        raise RuntimeError(f"櫃買中心沒有回傳 {symbol} 在所選期間的日線資料。")
    bars["Date"] = pd.to_datetime(bars["Date"])
    bars = bars.dropna(subset=["Open", "High", "Low", "Close"])
    bars = bars[(bars["Date"].dt.date >= start) & (bars["Date"].dt.date <= end)]
    bars = bars.sort_values("Date").drop_duplicates("Date").reset_index(drop=True)
    if bars.empty:
        raise RuntimeError("所選區間沒有可用的 OHLC 日線資料。")
    return bars
