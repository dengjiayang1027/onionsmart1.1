import tempfile
import unittest
from pathlib import Path
from battle import store
from battle_fixtures import question


class SampledRoomTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'rooms.db')
        self.code, self.host = store.create(path=self.path)
        self.guest = store.join(self.code, 'Guest', path=self.path)
        store.start(self.code, self.host, question(), 'players', 'Host', path=self.path)
        self.start = self.view(-1)['started']

    def view(self, seconds, token=None, action=None):
        now = getattr(self, 'start', 0) + seconds
        return store.snapshot(self.code, token or self.host, action, path=self.path, now=now)

    def test_shared_boundaries_frozen_board_and_immediate_orders(self):
        first = self.view(0)
        bought = self.view(1, action=dict(id='buy', action='order', side='buy', type='market', quantity=100))
        self.assertEqual(bought['player']['shares'], 100)
        self.assertEqual(first['board'], bought['board'])
        self.assertEqual(self.view(4.99)['board_at'], 0)
        tick = self.view(5)
        self.assertEqual(tick['board_at'], 5)
        self.assertNotEqual(first['board'], tick['board'])
        # All clients see the same published values, even on staggered requests.
        self.assertEqual(tick['board'], self.view(7, self.guest)['board'])
        self.assertEqual([s['seconds'] for s in self.view(17)['history']], [0, 5, 10, 15])
        self.assertEqual(len(self.view(17, self.guest)['history']), 4)

    def test_option_is_personal_and_chart_uses_wall_time(self):
        self.view(1, action=dict(id='pause', action='option'))
        host, guest = self.view(10), self.view(10, self.guest)
        self.assertEqual(host['player']['processed'], 1)
        self.assertEqual(guest['player']['processed'], 10)
        self.assertEqual(host['history'], guest['history'])
        self.assertEqual(host['history'][-1]['seconds'], 10)

    def test_rank_gaps_include_losses_and_ties(self):
        with store._db(self.path) as db:
            room = store._read(db, self.code)
            players = list(room['players'].values())
            players[0]['equity'], players[1]['equity'] = 980000, 995000
            board = store._board(room)
            self.assertEqual([p['rank'] for p in board], [1, 2])
            self.assertEqual(board[1]['gap_pct'], 1.5)
            players[0]['equity'] = 995000
            self.assertEqual([p['rank'] for p in store._board(room)], [1, 1])

    def test_rematch_keeps_team_and_rejects_stale_round(self):
        end = self.view(240)
        self.assertEqual(end['status'], 'results')
        ids = {p['id'] for p in end['board']}
        with self.assertRaises(ValueError):
            store.rematch(self.code, self.guest, end['round'], path=self.path)
        store.rematch(self.code, self.host, end['round'], path=self.path)
        lobby = self.view(241, self.guest)
        self.assertEqual(lobby['status'], 'lobby')
        self.assertEqual(lobby['round'], 2)
        self.assertEqual({p['id'] for p in lobby['board']}, ids)
        self.assertEqual(lobby['player']['cash'], 1000000)
        self.assertFalse(lobby['player']['fills'])
        self.assertFalse(lobby['history'])
        with self.assertRaises(ValueError):
            store.rematch(self.code, self.host, 1, path=self.path)
        store.start(self.code, self.host, question(), 'players', 'Host', path=self.path)
        new_start = store.snapshot(self.code, self.host, path=self.path)['started']
        stale = dict(id='old', action='order', side='buy', type='market', quantity=100, round=1)
        view = store.snapshot(self.code, self.host, stale, path=self.path, now=new_start + 1)
        self.assertFalse(view['player']['fills'])
        self.assertEqual(view['player']['shares'], 0)

    def test_bot_rematch_does_not_duplicate_bot(self):
        code, token = store.create(path=self.path)
        for round_number in (1, 2):
            store.start(code, token, question(), 'benchmark', 'Host', path=self.path)
            view = store.snapshot(code, token, path=self.path)
            end = store.snapshot(code, token, path=self.path, now=view['started'] + 240)
            self.assertEqual(len(end['board']), 2)
            self.assertEqual(sum(p['bot'] for p in end['board']), 1)
            store.rematch(code, token, round_number, path=self.path)
            self.assertEqual(len(store.snapshot(code, token, path=self.path)['board']), 1)
