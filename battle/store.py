"""Shared SQLite prototype. Tokens identify players; room codes only invite.

All mutations run under BEGIN IMMEDIATE. A production multi-instance deployment
must replace this store with a shared database, keeping the engine interface.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from contextlib import contextmanager
from .engine import new_player, advance, advance_bot, event, summary, DEADLINE

BOARD_SECONDS = 5


def _board(room):
    rows = [dict(summary(p), id=token_hash(key)[:16]) for key, p in room['players'].items()]
    rows.sort(key=lambda p: -p['profit'])
    rank, previous = 0, None
    for position, row in enumerate(rows, 1):
        if row['profit'] != previous:
            rank = position
        previous = row['profit']
        row['rank'] = rank
        row['gap_pct'] = (round(rows[position - 2]['return_pct'] - row['return_pct'], 3)
                          if position > 1 else 0)
    return rows


def _sample(room, seconds):
    room['board'] = _board(room)
    room['board_at'] = seconds
    room.setdefault('history', []).append(dict(seconds=seconds, rates={p['id']: p['return_pct'] for p in room['board']}))


def _ticks(room, now):
    """One common wall-clock sampling schedule, including missed polls.

    Actions between samples update only their owner's ledger; the published
    board stays frozen until the next common five-second boundary.
    """
    if now < room['started']:
        return False
    target = int(min(DEADLINE, now - room['started']) // BOARD_SECONDS) * BOARD_SECONDS
    changed = False
    if 'board_at' not in room:  # Legacy ledgers may already be beyond this boundary.
        for player in room['players'].values():
            bars = room['market']['benchmark' if player['bot'] else 'bars']
            (advance_bot if player['bot'] else advance)(player, bars, room['started'], now)
        room.update(board_at=target, board=_board(room), history=[])
        if all(p['finished'] for p in room['players'].values()):
            room['status'] = 'results'
        return True
    for seconds in range(room.get('board_at', -BOARD_SECONDS) + BOARD_SECONDS, target + 1, BOARD_SECONDS):
        for player in room['players'].values():
            bars = room['market']['benchmark' if player['bot'] else 'bars']
            (advance_bot if player['bot'] else advance)(player, bars, room['started'], room['started'] + seconds)
        _sample(room, seconds)
        changed = True
        if all(p['finished'] for p in room['players'].values()):
            room['status'] = 'results'
            break
    return changed


@contextmanager
def _db(path=None):
    location = Path(path or os.getenv('ONION_BATTLE_DB', str(Path(__file__).resolve().parent.parent / '.battle-data' / 'rooms.sqlite3')))
    location.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(location), timeout=10)
    connection.execute('CREATE TABLE IF NOT EXISTS rooms(code TEXT PRIMARY KEY, created REAL, body TEXT)')
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _write(db, room):
    db.execute('UPDATE rooms SET body=? WHERE code=?', (json.dumps(room, ensure_ascii=False), room['code']))


def _read(db, code):
    record = db.execute('SELECT body FROM rooms WHERE code=?', (code,)).fetchone()
    if not record:
        raise ValueError('房間不存在、已過期，或網站曾重啟')
    return json.loads(record[0])


def create(name='房主', path=None):
    token = secrets.token_urlsafe(24)
    code = secrets.token_hex(4).upper()
    pid = token_hash(token)
    room = dict(code=code, host=pid, created=time.time(), status='lobby', mode='players',
                players={pid: new_player(name[:16])}, market=None, started=0, round=1)
    with _db(path) as db:
        db.execute('DELETE FROM rooms WHERE created<?', (time.time() - 86400,))
        db.execute('INSERT INTO rooms VALUES(?,?,?)', (code, room['created'], json.dumps(room)))
    return code, token


def join(code, name, path=None):
    name = name.strip()[:16]
    if not name:
        raise ValueError('請輸入暱稱')
    token = secrets.token_urlsafe(24)
    with _db(path) as db:
        db.execute('BEGIN IMMEDIATE')
        room = _read(db, code)
        if room['status'] != 'lobby':
            raise ValueError('比賽已開始，請建立新房間')
        if len(room['players']) >= 4:
            raise ValueError('房間已滿，最多四位玩家')
        if any(p['name'] == name for p in room['players'].values()):
            raise ValueError('暱稱已有人使用')
        room['players'][token_hash(token)] = new_player(name)
        room.pop('board', None)
        _write(db, room)
    return token


def start(code, token, market, mode, name, path=None, expected_round=None):
    with _db(path) as db:
        db.execute('BEGIN IMMEDIATE')
        room = _read(db, code)
        pid = token_hash(token)
        if pid != room['host'] or room['status'] != 'lobby':
            raise ValueError('只有房主可開始尚未開賽的房間')
        if expected_round is not None and room.get('round', 1) != expected_round:
            raise ValueError('房間已進入下一局，請重新開始')
        humans = list(room['players'].values())
        if mode not in ('players', 'benchmark'):
            raise ValueError('無效的對戰方式')
        if mode == 'benchmark' and len(humans) != 1:
            raise ValueError('人機模式限一人')
        if mode == 'players' and len(humans) < 2:
            raise ValueError('多人對戰至少需要兩位玩家；一人可選人機模式')
        name = name.strip()[:16] or '房主'
        if any(k != pid and p['name'] == name for k, p in room['players'].items()):
            raise ValueError('房主暱稱已被使用')
        room['players'][pid]['name'] = name
        if mode == 'benchmark':
            room['players']['benchmark'] = new_player('0050 定期定額', True)
        room.update(status='playing', market=market, mode=mode, started=time.time() + 3)
        room.update(board=_board(room), board_at=-BOARD_SECONDS, history=[])
        _write(db, room)


def rematch(code, token, expected_round, path=None):
    """Keep invitations, identities and human members, reset only the match."""
    with _db(path) as db:
        db.execute('BEGIN IMMEDIATE')
        room = _read(db, code)
        if token_hash(token) != room['host']:
            raise ValueError('只有房主可開啟下一局')
        if room['status'] != 'results' or room.get('round', 1) != expected_round:
            raise ValueError('本局尚未結束，或已開啟下一局')
        room['players'] = {key: new_player(p['name']) for key, p in room['players'].items() if not p['bot']}
        room.update(status='lobby', market=None, started=0, round=expected_round + 1,
                    board_at=-BOARD_SECONDS, history=[], board=[])
        _write(db, room)


def snapshot(code, token, data=None, path=None, now=None):
    now = time.time() if now is None else now
    with _db(path) as db:
        db.execute('BEGIN IMMEDIATE')
        room = _read(db, code)
        pid = token_hash(token)
        if pid not in room['players']:
            raise ValueError('玩家識別失效；請從邀請連結重新加入')
        if room['status'] == 'playing':
            changed = _ticks(room, now)
            if isinstance(data, dict) and data and room['status'] == 'playing' and data.get('round', 1) == room.get('round', 1):
                event(room['players'][pid], room['market']['bars'], room['started'], now, data)
                changed = True
            if changed:
                _write(db, room)
        own = room['players'][pid]
        board = room.get('board') or _board(room)
        # Return only your ledger. Other players expose summary metrics, never tokens.
        return dict(code=code, status=room['status'], host=pid == room['host'], mode=room['mode'],
                    started=room['started'], server_now=now, player=own, board=board,
                    player_id=token_hash(pid)[:16], round=room.get('round', 1),
                    board_at=room.get('board_at', 0), history=room.get('history', []),
                    market=room['market'], deadline=room['started'] + DEADLINE)
