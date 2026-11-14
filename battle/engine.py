"""Server-authoritative experimental long-only ledger and replay clock.

Daily OHLC paths are synthetic. No fees, dividends, leverage or short selling.
"""
import math
import uuid

CASH = 1_000_000.0
BARS = 24
SECONDS = 8.0
OPTIONS = 3
PAUSE_SECONDS = 10.0
DEADLINE = 240.0


def new_player(name, bot=False):
    return dict(name=name, bot=bot, cash=CASH, shares=0, cost=0.0,
                orders=[], fills=[], realized=[], pauses=[], processed=0.0,
                peak=CASH, drawdown=0.0, finished=False, equity=CASH,
                seen=[], ack=None, error="", investments=[])


def active_seconds(player, start, now):
    elapsed = max(0.0, now - start)
    paused = sum(max(0.0, min(now, end) - begin) for begin, end in player['pauses'])
    return min(BARS * SECONDS, max(0.0, elapsed - paused))


def price_at(bars, elapsed):
    index = min(len(bars) - 1, int(max(0, elapsed) / SECONDS))
    progress = min(1.0, max(0.0, (elapsed - index * SECONDS) / SECONDS))
    row = bars[index]
    path = ([row['Open'], row['High'], row['Low'], row['Close']] if index % 2 == 0
            else [row['Open'], row['Low'], row['High'], row['Close']])
    segment = min(2, int(progress * 3))
    local = min(1.0, progress * 3 - segment)
    price = path[segment] + (path[segment + 1] - path[segment]) * local
    visited = path[:segment + 1] + [price]
    return index, progress, price, dict(Open=path[0], High=max(visited),
                                       Low=min(visited), Close=price)


def _mark(player, price):
    player['equity'] = player['cash'] + player['shares'] * price
    player['peak'] = max(player['peak'], player['equity'])
    player['drawdown'] = max(player['drawdown'], 1 - player['equity'] / player['peak'])


def _fill(player, order, price, elapsed, reason='成交'):
    quantity = order['quantity']
    value = price * quantity
    if order['side'] == 'buy':
        if value > player['cash'] + 1e-7:
            return False
        player['cost'] = (player['cost'] * player['shares'] + value) / (player['shares'] + quantity)
        player['shares'] += quantity
        player['cash'] -= value
    else:
        if quantity > player['shares']:
            return False
        pnl = (price - player['cost']) * quantity
        player['realized'].append(pnl)
        player['cash'] += value
        player['shares'] -= quantity
        if not player['shares']:
            player['cost'] = 0.0
    player['fills'].append(dict(side=order['side'], quantity=quantity, price=price,
                                value=value, elapsed=elapsed, reason=reason,
                                order_id=order.get('id', ''), type=order['type']))
    _mark(player, price)
    return True


def _limits(player, first, last, begin, end):
    """Fill at first touch, in path order, including favorable opening gaps."""
    hits = []
    for order in player['orders']:
        limit = order['limit']
        if ((order['side'] == 'buy' and first <= limit) or
                (order['side'] == 'sell' and first >= limit)):
            fraction, price = 0.0, first
        elif ((order['side'] == 'buy' and last <= limit < first) or
              (order['side'] == 'sell' and last >= limit > first)):
            fraction, price = (limit - first) / (last - first), limit
        else:
            continue
        hits.append((fraction, order, price))
    for fraction, order, price in sorted(hits, key=lambda item: item[0]):
        _mark(player, price)
        _fill(player, order, price, begin + fraction * (end - begin), '限價觸及')
        player['orders'].remove(order)


def advance(player, bars, start, now):
    if player['finished']:
        return
    if now < start:
        return
    target = active_seconds(player, start, now)
    if now >= start + DEADLINE:
        target = BARS * SECONDS
    previous = player['processed']
    # Replay all crossed OHLC segments, never just the latest polling price.
    # Include each new day's open separately so a daily gap is not interpolated.
    points = [previous, target]
    for index in range(len(bars)):
        for part in (0, 1, 2, 3):
            value = index * SECONDS + part * SECONDS / 3
            if previous < value < target:
                points.append(value)
    points = sorted(set(points))
    for left, right in zip(points, points[1:]):
        index, _, first, _ = price_at(bars, left)
        boundary = (index + 1) * SECONDS
        last = bars[index]['Close'] if abs(right - boundary) < 1e-7 else price_at(bars, right)[2]
        _mark(player, first)
        _limits(player, first, last, left, right)
        _mark(player, last)
        if right < BARS * SECONDS and abs(right % SECONDS) < 1e-7:
            opening = price_at(bars, right)[2]
            _limits(player, opening, opening, right, right)
            _mark(player, opening)
    player['processed'] = target
    price = price_at(bars, target)[2]
    _mark(player, price)
    if target >= BARS * SECONDS:
        player['orders'] = []
        if player['shares']:
            _fill(player, dict(side='sell', quantity=player['shares'], type='market'),
                  bars[-1]['Close'], target, '區間結束')
        player['finished'] = True


def advance_bot(player, bars, start, now):
    if player['finished'] or now < start:
        return
    target = min(BARS * SECONDS, max(0.0, now - start))
    for index in (0, 5, 10, 15, 20):
        if index not in player['investments'] and target >= index * SECONDS:
            advance(player, bars, start, start + index * SECONDS)
            opening = bars[index]['Open']
            quantity = int((CASH / 5) / opening)
            if quantity:
                _fill(player, dict(side='buy', quantity=quantity, type='market'),
                      opening, index * SECONDS, '0050 每五交易日等額投入')
            player['investments'].append(index)
    advance(player, bars, start, now)


def event(player, bars, start, now, data):
    """Idempotent actions; a retry never creates a second order or pause."""
    if not isinstance(data, dict):
        player['error'] = '無效操作資料'
        return
    identifier = str(data.get('id', ''))[:100]
    if not identifier or identifier in player['seen']:
        return
    player['seen'] = (player['seen'] + [identifier])[-512:]
    player['ack'], player['error'] = identifier, ''
    advance(player, bars, start, now)
    try:
        if player['finished'] or now < start:
            raise ValueError('尚未開始或已結束')
        action = data.get('action')
        if action == 'option':
            if any(begin <= now < end for begin, end in player['pauses']):
                raise ValueError('已在 Option 暫停中')
            if len(player['pauses']) >= OPTIONS:
                raise ValueError('本場三次 Option 已用完')
            player['pauses'].append([now, now + PAUSE_SECONDS])
            return
        if action == 'cancel':
            player['orders'] = [o for o in player['orders'] if o['id'] != data.get('order_id')]
            return
        if action != 'order':
            raise ValueError('無效操作')
        quantity = data.get('quantity')
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 100_000_000:
            raise ValueError('股數必須是正整數')
        side, kind = data.get('side'), data.get('type')
        if side not in ('buy', 'sell') or kind not in ('market', 'limit'):
            raise ValueError('訂單方向或類型錯誤')
        price = price_at(bars, player['processed'])[2]
        limit = float(data.get('limit', 0)) if kind == 'limit' else price
        if not math.isfinite(limit) or limit <= 0:
            raise ValueError('限價必須大於零')
        reserved_cash = sum(o['quantity'] * o['limit'] for o in player['orders'] if o['side'] == 'buy')
        reserved_shares = sum(o['quantity'] for o in player['orders'] if o['side'] == 'sell')
        check_price = min(price, limit) if side == 'buy' and kind == 'limit' else limit
        if side == 'buy' and quantity * check_price > player['cash'] - reserved_cash + 1e-7:
            raise ValueError('可用現金不足；待成交買單已預留資金')
        if side == 'sell' and quantity > player['shares'] - reserved_shares:
            raise ValueError('可賣股數不足；不支援放空')
        if len(player['orders']) >= 20:
            raise ValueError('待成交訂單最多二十筆')
        order = dict(id=identifier, side=side, type=kind, quantity=quantity, limit=limit)
        marketable = kind == 'market' or (side == 'buy' and price <= limit) or (side == 'sell' and price >= limit)
        if marketable:
            if not _fill(player, order, price, player['processed']):
                raise ValueError('資金或持股不足')
        else:
            if side == 'buy' and quantity * limit > player['cash'] - reserved_cash + 1e-7:
                raise ValueError('限價買單預留資金不足')
            player['orders'].append(order)
    except (ValueError, TypeError, OverflowError) as exc:
        player['error'] = str(exc)


def summary(player):
    gains = sum(max(0, value) for value in player['realized'])
    losses = sum(-min(0, value) for value in player['realized'])
    samples = len(player['realized'])
    return dict(name=player['name'], equity=round(player['equity'], 2),
                profit=round(player['equity'] - CASH, 2),
                return_pct=round((player['equity'] / CASH - 1) * 100, 3),
                max_drawdown_pct=round(player['drawdown'] * 100, 3),
                fills=len(player['fills']), sell_samples=samples,
                win_rate=round(100 * sum(v > 0 for v in player['realized']) / samples, 1) if samples else None,
                profit_factor=round(gains / losses, 3) if losses else ('無虧損' if gains else None),
                finished=player['finished'], bot=player['bot'])
