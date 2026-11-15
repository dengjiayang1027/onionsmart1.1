"""Synthetic test fixtures; never used by the application."""
import random

def question():
    def synthetic(base, seed):
        rng = random.Random(seed)
        rows = []
        for i in range(24):
            opening = base
            close = opening * (1 + rng.uniform(-.025, .027))
            rows.append(dict(Date=f'示範第{i + 1}日', Open=opening,
                             High=max(opening, close) * 1.008,
                             Low=min(opening, close) * .992, Close=close, Volume=0))
            base = close
        return rows
    return dict(symbol='DEMO', name='合成示範（非台股歷史）', bars=synthetic(100, 12),
                benchmark=synthetic(80, 20), source='合成示範', fingerprint='demo-v1')
