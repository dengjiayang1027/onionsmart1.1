import unittest
from unittest.mock import patch
import pandas as pd
from battle.market import prepare

class HistoricalMarketTests(unittest.TestCase):
    def test_common_dates_and_original_prices(self):
        dates = pd.date_range('2023-01-01', periods=40)
        stock = pd.DataFrame(dict(Date=dates, Open=100., High=110., Low=90., Close=105., Volume=1000))
        benchmark = stock.iloc[3:].copy()
        benchmark['Close'] = 80.
        with patch('market_data.fetch_twse_daily', side_effect=[stock, benchmark]) as fetch:
            result = prepare()
        self.assertEqual(fetch.call_args_list[1].args[0], '0050')
        self.assertEqual(len(result['bars']), 24)
        self.assertEqual([r['Date'] for r in result['bars']], [r['Date'] for r in result['benchmark']])
        self.assertTrue(all(r['Close'] == 105. for r in result['bars']))
        self.assertTrue(all(r['Close'] == 80. for r in result['benchmark']))
        self.assertIn('證交所', result['source'])

    def test_download_failure_never_becomes_synthetic(self):
        with patch('market_data.fetch_twse_daily', side_effect=RuntimeError('下載失敗')):
            with self.assertRaisesRegex(RuntimeError, '下載失敗'):
                prepare()
