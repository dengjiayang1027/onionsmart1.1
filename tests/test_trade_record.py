import unittest
from types import SimpleNamespace
from datetime import datetime

from trading_engine import open_position, close_position


class RecordTests(unittest.TestCase):
    def state(self):
        return SimpleNamespace(
            current_bar={"Date": datetime(2026, 1, 1), "Close": 100.0},
            i=0, pos=0, qty=2, sl_pct=3.0, tp_pct=6.0,
            market_symbol="3297", market_name="杭特", trades=[], order_events=[],
        )

    def test_long_and_short_records(self):
        for side, price in ((1, 110.0), (-1, 90.0)):
            with self.subTest(side=side):
                state = self.state()
                open_position(state, side, ["突破"])
                state.current_bar = {"Date": datetime(2026, 1, 2), "Close": price}
                state.i = 1
                close_position(state)
                self.assertEqual(len(state.order_events), 2)
                self.assertEqual(len(state.trades), 1)
                self.assertEqual(state.trades[0]["損益"], 20)
                self.assertEqual(state.trades[0]["股票"], "3297 杭特")
                self.assertEqual(state.trades[0]["進場理由"], "突破")
                self.assertTrue(all(x["股票"] == "3297 杭特" for x in state.order_events))
                close_position(state)
                self.assertEqual(len(state.order_events), 2)

    def test_reverse_records_exit_and_new_entry_once(self):
        state = self.state()
        open_position(state, 1, ["支撐"])
        state.current_bar["Close"] = 95.0
        open_position(state, -1, ["壓力"])
        self.assertEqual(len(state.order_events), 3)
        self.assertEqual(state.trades[0]["損益"], -10)
        self.assertEqual(state.trades[0]["出場原因"], "Reverse")
        self.assertEqual(state.trades[0]["進場理由"], "支撐")
        self.assertEqual(state.pos, -1)


if __name__ == "__main__":
    unittest.main()
