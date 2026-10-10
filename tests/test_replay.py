import unittest
from types import SimpleNamespace
import pandas as pd
from replay_engine import interpolate_bar, advance_clock, replay_finished


class ReplayTests(unittest.TestCase):
    def state(self, **changes):
        values = dict(i=0, mode="Dynamic Replay", progress=0.0, running=True,
                      last_tick=0.0, pause_until=0.0, pause_reason="",
                      dynamic_seconds=8, decision_count=2, decision_seconds=5,
                      editing_trade=False)
        return SimpleNamespace(**(values | changes))

    def test_path_uses_all_eight_seconds_and_only_visited_extrema(self):
        row = pd.Series(dict(Open=100, High=120, Low=80, Close=110))
        bar = interpolate_bar(row, 0, .1)
        self.assertEqual(bar["Low"], 100)
        self.assertLess(bar["High"], 120)
        self.assertNotEqual(interpolate_bar(row, 0, .75)["Close"], 110)
        self.assertEqual(interpolate_bar(row, 0, 1), row.to_dict())

    def test_decision_time_is_excluded(self):
        state = self.state()
        advance_clock(state, 3, 2)
        self.assertAlmostEqual(state.progress, .18)
        advance_clock(state, 7, 2)
        self.assertAlmostEqual(state.progress, .18)
        advance_clock(state, 8, 2)
        self.assertAlmostEqual(state.progress, .18)
        advance_clock(state, 9, 2)
        self.assertAlmostEqual(state.progress, .305)

    def test_final_candle_and_edit_pause(self):
        state = self.state(i=1, decision_count=0, editing_trade=True)
        advance_clock(state, 20, 2)
        self.assertEqual(state.progress, 0)
        self.assertFalse(replay_finished(state, 2))
        state.editing_trade = False
        advance_clock(state, 24, 2)
        self.assertEqual(state.progress, .5)
        advance_clock(state, 28, 2)
        self.assertTrue(replay_finished(state, 2))
        self.assertFalse(state.running)


if __name__ == "__main__":
    unittest.main()
