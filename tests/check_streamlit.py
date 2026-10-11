import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, '.runtime')
from streamlit.testing.v1 import AppTest
at = AppTest.from_file(str(root / 'pages/1_交易員.py')).run(timeout=30)
assert not at.exception, at.exception
for label, expected in [('▶ +1',91),('⏩ +5',96)]:
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception, at.exception
    assert at.session_state['i'] == expected
next(b for b in at.button if b.label == '⬆ 買入').click().run()
assert at.session_state['pos'] == 0
next(b for b in at.button if b.label == '送出交易').click().run()
next(b for b in at.button if b.label == '▶ +1').click().run()
next(b for b in at.button if b.label == '✕ 平倉').click().run()
assert not at.exception, at.exception
assert len(at.session_state['trades']) == 1
assert len(at.session_state['order_events']) == 2
at.radio[1].set_value('Dynamic Replay').run()
assert not at.exception, at.exception
assert at.session_state['i'] == 98
next(b for b in at.button if b.label == '暫停並編輯交易').click().run()
assert at.session_state['editing_trade']
assert not at.session_state['running']
frozen = at.session_state['progress']
next(b for b in at.button if b.label == '⬇ 賣出').click().run()
next(b for b in at.button if b.label == '送出交易').click().run()
assert not at.exception, at.exception
assert at.session_state['pos'] == -1
assert not at.session_state['running']  # A paused market stays paused after trading.
assert at.session_state['progress'] == frozen
assert any(b.label == '🏠 回主選單' for b in at.button)
home = AppTest.from_file(str(root / 'app.py')).run(timeout=30)
assert not home.exception, home.exception
print('PASS: home, manual +1/+5, BUY/close, single trade and two events')
