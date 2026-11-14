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
                players={pid: new_player(name[:16])}, market=None, started=0)
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
        _write(db, room)
    return token


def start(code, token, market, mode, name, path=None):
    with _db(path) as db:
        db.execute('BEGIN IMMEDIATE')
        room = _read(db, code)
        pid = token_hash(token)
        if pid != room['host'] or room['status'] != 'lobby':
            raise ValueError('只有房主可開始尚未開賽的房間')
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
            for key, player in room['players'].items():
                bars = room['market']['benchmark' if player['bot'] else 'bars']
                (advance_bot if player['bot'] else advance)(player, bars, room['started'], now)
            if data:
                event(room['players'][pid], room['market']['bars'], room['started'], now, data)
            if all(p['finished'] for p in room['players'].values()):
                room['status'] = 'results'
            _write(db, room)
        own = room['players'][pid]
        board = sorted((summary(p) for p in room['players'].values()), key=lambda p: -p['profit'])
        # Return only your ledger. Other players expose summary metrics, never tokens.
        return dict(code=code, status=room['status'], host=pid == room['host'], mode=room['mode'],
                    started=room['started'], server_now=now, player=own, board=board,
                    market=room['market'], deadline=room['started'] + DEADLINE)
