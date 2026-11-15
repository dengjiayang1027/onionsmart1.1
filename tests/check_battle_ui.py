import os
import sys
import tempfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(root),str(root/'.runtime')]
temp=tempfile.TemporaryDirectory()
os.environ['ONION_BATTLE_DB']=str(Path(temp.name)/'ui.sqlite3')
from streamlit.testing.v1 import AppTest
from battle import store
from battle_fixtures import question
from unittest.mock import patch
page=str(root/'pages/3_多人競賽.py')
host=AppTest.from_file(page).run(timeout=40)
assert not host.exception, host.exception
code=host.session_state['battle_code']
host_token=host.session_state['battle_token']
guest=AppTest.from_file(page)
guest.query_params['room']=code
guest.run(timeout=40)
assert not guest.exception, guest.exception
guest.text_input[0].set_value('Guest').run()
next(b for b in guest.button if b.label=='加入房間').click().run()
assert not guest.exception, guest.exception
assert guest.session_state['battle_code']==code
host.run()
assert not host.exception, host.exception
assert len(host.checkbox)==0
with patch('battle.market.prepare', return_value=question()):
    next(b for b in host.button if b.label=='▶ 開始對戰').click().run()
assert not host.exception, host.exception
v=store.snapshot(code,host_token)
assert v['status']=='playing'
assert len(v['board'])==2
store.snapshot(code,host_token,now=v['started']+240)
host.run()
guest.run()
assert not host.exception, host.exception
assert not guest.exception, guest.exception
assert any('全員完成' in x.value for x in host.success)
home=AppTest.from_file(str(root/'app.py')).run(timeout=40)
assert not home.exception,home.exception
print('PASS: auto room, invite/join, two clients, start, terminal render, deadline, results, home')
temp.cleanup()
