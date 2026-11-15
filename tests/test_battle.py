import copy
from concurrent.futures import ThreadPoolExecutor
import tempfile
from pathlib import Path
import unittest
from battle.engine import *
from battle import store
from battle_fixtures import question

def bars():
    return [dict(Date=f'day-{i}', Open=100.0, High=110.0, Low=90.0, Close=105.0, Volume=0) for i in range(24)]

def order(identifier='x', **changes):
    data = dict(id=identifier, action='order', side='buy', type='market', quantity=10)
    data.update(changes)
    return data

class EngineTests(unittest.TestCase):
    def test_ohlc_does_not_reveal_future(self):
        _, _, px, candle = price_at(bars(), .8)
        self.assertEqual(candle['Low'], 100)
        self.assertLess(candle['High'], 110)
        self.assertNotEqual(px, 105)
        self.assertEqual(price_at(bars(),192)[3]['Close'],105)

    def test_retries_and_budget_and_no_short(self):
        p = new_player('A')
        event(p,bars(),0,0,order())
        event(p,bars(),0,0,order())
        self.assertEqual(len(p['fills']),1)
        self.assertEqual(p['cash'],999000)
        event(p,bars(),0,0,order('over',quantity=100000))
        self.assertTrue(p['error'])
        event(p,bars(),0,0,order('short',side='sell',quantity=11))
        self.assertTrue(p['error'])
        self.assertEqual(p['shares'],10)

    def test_late_polling_fills_crossed_limit(self):
        p = new_player('A')
        event(p,bars(),0,0,order(type='limit',limit=95))
        advance(p,bars(),0,7)
        self.assertEqual(p['shares'],10)
        self.assertEqual(p['fills'][0]['price'],95)
        self.assertFalse(p['orders'])
        self.assertGreater(p['fills'][0]['elapsed'],2)
        self.assertLess(p['fills'][0]['elapsed'],6)

    def test_reserved_cash_and_shares(self):
        p = new_player('A')
        event(p,bars(),0,0,order(type='limit',limit=95,quantity=10000))
        event(p,bars(),0,0,order('second',quantity=1000))
        self.assertTrue(p['error'])
        event(p,bars(),0,0,dict(id='cancel',action='cancel',order_id='x'))
        self.assertFalse(p['orders'])
        event(p,bars(),0,0,order('buy',quantity=10))
        event(p,bars(),0,0,order('sell',side='sell',type='limit',limit=108,quantity=10))
        event(p,bars(),0,0,order('sell2',side='sell',quantity=1))
        self.assertTrue(p['error'])

    def test_open_gap_receives_better_fill(self):
        b=bars()
        b[1].update(Open=80,High=90,Low=75,Close=85)
        p=new_player('A')
        event(p,b,0,0,order(type='limit',limit=85))
        advance(p,b,0,8)
        self.assertEqual(p['fills'][0]['price'],80)

    def test_options_and_max_duration(self):
        p = new_player('A')
        for n,t in enumerate((1,12,23)):
            event(p,bars(),0,t,dict(id=str(n),action='option'))
        self.assertEqual(len(p['pauses']),3)
        event(p,bars(),0,34,dict(id='fourth',action='option'))
        self.assertTrue(p['error'])
        advance(p,bars(),0,221)
        self.assertFalse(p['finished'])
        advance(p,bars(),0,222)
        self.assertTrue(p['finished'])
        self.assertEqual(p['processed'],192)

    def test_paused_and_finished_reject_duplicate_pause(self):
        p=new_player('A')
        event(p,bars(),0,1,dict(id='one',action='option'))
        event(p,bars(),0,2,dict(id='two',action='option'))
        self.assertEqual(len(p['pauses']),1)
        advance(p,bars(),0,500)
        event(p,bars(),0,501,order())
        self.assertTrue(p['error'])

    def test_timing_poll_frequency_does_not_change_result(self):
        p=new_player('A')
        event(p,bars(),0,0,order(quantity=100))
        a,b=copy.deepcopy(p),copy.deepcopy(p)
        for t in range(1,193):
            advance(a,bars(),0,t)
        advance(b,bars(),0,192)
        self.assertEqual(a['cash'],b['cash'])
        self.assertEqual(a['drawdown'],b['drawdown'])
        self.assertTrue(a['finished'])
        self.assertEqual(a['shares'],0)

    def test_limit_drawdown_is_independent_of_polling(self):
        p=new_player('A')
        event(p,bars(),0,0,order(type='limit',limit=95,quantity=100))
        a,b=copy.deepcopy(p),copy.deepcopy(p)
        for n in range(1,193):
            advance(a,bars(),0,n)
        advance(b,bars(),0,192)
        self.assertAlmostEqual(a['drawdown'],b['drawdown'])
        self.assertAlmostEqual(a['cash'],b['cash'])

    def test_bot_equal_five_budgets_and_cash(self):
        p=new_player('bot',True)
        advance_bot(p,bars(),0,192)
        buys=[f for f in p['fills'] if f['side']=='buy']
        self.assertEqual(len(buys),5)
        self.assertTrue(all(f['value']==200000 for f in buys))
        self.assertTrue(p['finished'])
        self.assertEqual(p['cash'],1050000)

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=str(Path(self.temp.name)/'rooms.db')
    def tearDown(self):
        self.temp.cleanup()

    def test_capacity_transaction_and_duplicate_names(self):
        code,token=store.create(path=self.path)
        def enter(i):
            try:
                return store.join(code,'P'+str(i),path=self.path)
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(enter,range(6)))
        self.assertEqual(sum(v is not None for v in results),3)
        view=store.snapshot(code,token,path=self.path)
        self.assertEqual(len(view['board']),4)

    def test_only_host_starts_then_atomic_settlement(self):
        code,token=store.create(path=self.path)
        guest=store.join(code,'Guest',path=self.path)
        market=question()
        with self.assertRaises(ValueError):
            store.start(code,guest,market,'players','Guest',path=self.path)
        store.start(code,token,market,'players','Host',path=self.path)
        view=store.snapshot(code,token,path=self.path)
        start=view['started']
        early=store.snapshot(code,guest,path=self.path,now=start-1)
        self.assertEqual(early['player']['processed'],0)
        view=store.snapshot(code,token,order(),path=self.path,now=start)
        self.assertEqual(view['player']['shares'],10)
        # Even an absent guest is finished at the server deadline.
        end=store.snapshot(code,token,path=self.path,now=start+240)
        self.assertEqual(end['status'],'results')
        self.assertTrue(all(p['finished'] for p in end['board']))
        self.assertNotIn('players',end)
        self.assertIsInstance(end['board'][0]['fills'],int)
        with self.assertRaises(ValueError):
            store.join(code,'Late',path=self.path)

    def test_bot_room_and_bad_token(self):
        code,token=store.create(path=self.path)
        with self.assertRaises(ValueError):
            store.snapshot(code,'fake',path=self.path)
        store.start(code,token,question(),'benchmark','Me',path=self.path)
        view=store.snapshot(code,token,path=self.path)
        end=store.snapshot(code,token,path=self.path,now=view['started']+240)
        self.assertEqual(len(end['board']),2)
        self.assertEqual(end['status'],'results')

if __name__=='__main__':
    unittest.main()
