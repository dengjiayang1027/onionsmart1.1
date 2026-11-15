"""Preload a frozen, common 24-session question before starting the clock."""
from datetime import date, timedelta
import random
import hashlib
import json

POOL = [('2330', '台積電'), ('2317', '鴻海'), ('2454', '聯發科'),
        ('2303', '聯電'), ('2603', '長榮'), ('2881', '富邦金')]


def prepare():
    from market_data import fetch_twse_daily
    rng = random.SystemRandom()
    symbol, name = rng.choice(POOL)
    # A curated pool, not a real-time popularity ranking. Avoid the 2025 ETF split.
    year, month = rng.randint(2019, 2024), rng.randint(1, 9)
    start = date(year, month, 1)
    end = start + timedelta(days=90)
    stock = fetch_twse_daily(symbol, start, end)
    benchmark = fetch_twse_daily('0050', start, end)
    common = sorted(set(stock.Date) & set(benchmark.Date))
    if len(common) < 24:
        raise ValueError('行情不足二十四個共同交易日，請重新抽題')
    offset = rng.randint(0, len(common) - 24)
    dates = common[offset:offset + 24]
    def rows(frame):
        frame = frame.set_index('Date').loc[dates].reset_index()
        frame['Date'] = frame['Date'].dt.strftime('%Y-%m-%d')
        return frame.to_dict('records')
    bars, index_bars = rows(stock), rows(benchmark)
    encoded = json.dumps([bars, index_bars], sort_keys=True).encode()
    return dict(symbol=symbol, name=name, bars=bars, benchmark=index_bars,
                source='證交所日線｜未還原權息', fingerprint=hashlib.sha256(encoded).hexdigest())
