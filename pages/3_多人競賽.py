"""Experimental rooms and independent phone terminals."""
from pathlib import Path
import time
import streamlit as st
import streamlit.components.v1 as components
from battle import store
from battle.component import terminal
from battle.market import prepare, POOL

st.set_page_config(page_title='對戰模式｜蔥明錢', page_icon='🏆', layout='centered', initial_sidebar_state='collapsed')
st.markdown('''<style>
.stApp{background:#0d0d13;color:#edf2f7}.block-container{padding:.5rem .5rem 1rem;max-width:760px}
[data-testid="stHeader"]{display:none}.stButton button{min-height:44px;border-radius:11px}
[data-testid="stWidgetLabel"] p{color:#b9c5d5}input{font-size:16px!important}
</style>''', unsafe_allow_html=True)

incoming = str(st.query_params.get('room', '')).strip().upper()
if incoming and (len(incoming) != 8 or any(c not in '0123456789ABCDEF' for c in incoming)):
    st.error('房號格式錯誤')
    st.stop()
if incoming and incoming != st.session_state.get('battle_code'):
    st.session_state.pop('battle_token', None)
    st.session_state.battle_invite = incoming

if st.session_state.get('battle_invite') and not st.session_state.get('battle_token'):
    code = st.session_state.battle_invite
    st.title('🏆 加入對戰房間')
    st.caption(f'房號 {code} · 最多四位玩家')
    nickname = st.text_input('暱稱', max_chars=16)
    if st.button('加入房間', type='primary', use_container_width=True):
        try:
            token = store.join(code, nickname)
            st.session_state.update(battle_code=code, battle_token=token)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    if st.button('另開新房間'):
        st.session_state.pop('battle_invite', None)
        st.query_params.clear()
        st.rerun()
    st.stop()

if not st.session_state.get('battle_token'):
    code, token = store.create()
    st.session_state.update(battle_code=code, battle_token=token)
    st.query_params['room'] = code

code, token = st.session_state.battle_code, st.session_state.battle_token
try:
    current = store.snapshot(code, token)
except (ValueError, OSError) as exc:
    st.error(str(exc))
    if st.button('建立新房間'):
        for key in ('battle_code', 'battle_token', 'battle_invite'):
            st.session_state.pop(key, None)
        st.query_params.clear()
        st.rerun()
    st.stop()

if current['status'] == 'playing' and not current['player']['finished']:
    @st.fragment(run_every='5s')
    def play():
        view = store.snapshot(code, token)
        if view['round'] != current['round'] or view['status'] != 'playing' or view['player']['finished']:
            st.rerun(scope='app')
        action = terminal(snapshot=view, key=f"battle_live_{code}_{view['round']}", default=None)
        if action:
            after = store.snapshot(code, token, action)
            if after['player']['ack'] != view['player']['ack']:
                st.rerun(scope='fragment')
    play()
    st.stop()

st.markdown(f'### 🏆 對戰房間 · {code}')
st.caption(f"第 {current['round']} 局 · 原房間成員可連續再戰")
st.caption('測試版｜網站重啟可能清除房間，請勿輸入私人資料。')

if current['status'] == 'lobby':
    components.html('''<div style="font:14px system-ui;color:#dce5ef">房間邀請連結</div>
    <input id="link" readonly style="box-sizing:border-box;width:100%;padding:12px;border-radius:10px;border:1px solid #394252;background:#151b27;color:#e9f0f8;font-size:14px" />
    <div style="color:#9daec3;font:12px system-ui;margin-top:4px">點選連結欄後全選複製，傳給朋友。</div>
    <script>const field=document.getElementById('link');try{const invite=new URL(window.parent.location.href);invite.pathname=invite.pathname.replace('/~/+', '');field.value=invite.toString();field.onclick=()=>field.select()}catch(e){field.value=document.referrer}</script>''', height=94)
    @st.fragment(run_every='5s')
    def members():
        view = store.snapshot(code, token)
        if view['status'] != 'lobby':
            st.rerun(scope='app')
        st.markdown(f"**房間成員 {len(view['board'])}/4**")
        for member in view['board']:
            st.write('🟢 ' + member['name'])
    members()
    if current['host']:
        name = st.text_input('你的暱稱', value=current['player']['name'], max_chars=16)
        mode = st.radio('對戰方式', ['players', 'benchmark'],
                        index=0 if current['mode'] == 'players' else 1,
                        format_func=lambda m: '玩家對戰（2–4 人）' if m == 'players' else '人機對戰：0050 定期定額（1 人）', horizontal=True)
        with st.expander('賽事規則與行情'):
            st.info('使用證交所真實歷史日 K，與單人模式相同來源；下載失敗不使用合成行情替代。')
            st.caption('日 K 開高低收為歷史資料；八秒內價格路徑為 OHLC 模擬，非歷史逐筆成交。')
            st.caption('熱門候選池（人工選定，非即時排行）：' + '、'.join(n for _, n in POOL))
            st.write('每人一百萬元；相同隨機股票與二十四交易日，從 2019–2024 抽選。')
            st.write('每根日 K 八秒；沒有決策倒數。Option 十秒、每人最多三次。最長四分鐘，自動平倉。')
            st.write('每五秒統一更新帳面報酬排名與走勢；Option 只暫停自己，記分板橫軸為開賽經過時間。與前一名的差距以報酬率百分點顯示。')
            st.write('現股買賣：股數、市價／限價；限價按模擬路徑首度觸及成交，預留資金／股數。')
            st.write('0050 每五個交易日投入二十萬元，共五次；未投入現金也計入資產。只比較價格報酬，不含權息／費稅。')
            st.caption('此測試版使用 SQLite；行情會傳至瀏覽器製作動畫，不適用有獎金或需要防作弊的正式競賽。')
        if st.button('▶ 開始對戰', type='primary', use_container_width=True):
            try:
                if mode == 'players' and len(current['board']) < 2:
                    raise ValueError('至少兩人才能開始；一人請選人機模式')
                if mode == 'benchmark' and len(current['board']) != 1:
                    raise ValueError('人機模式限一位玩家')
                with st.spinner('載入共同行情，完成後才開始倒數…'):
                    question = prepare()
                    store.start(code, token, question, mode, name, expected_round=current['round'])
                st.rerun()
            except Exception as exc:
                st.error(f'尚未開賽：{exc}')
    else:
        st.info('已加入，等待房主開始；開賽後自動進入操作頁。')
else:
    @st.fragment(run_every='5s')
    def settlement():
        view = store.snapshot(code, token)
        if view['status'] == 'lobby' or view['round'] != current['round']:
            st.rerun(scope='app')
        if view['status'] == 'playing':
            done = sum(p['finished'] for p in view['board'])
            st.info(f"已完成 {done}/{len(view['board'])}，等待其他玩家；最遲 {max(0,int(view['deadline']-time.time()))} 秒後結算。")
            st.dataframe([{'玩家': p['name'], '報酬率 %': p['return_pct'], '完成': p['finished']} for p in view['board']], hide_index=True, use_container_width=True)
            return
        st.success('🏁 全員完成 · 依總盈虧排名，同盈虧並列')
        rows, previous, rank = [], None, 0
        for position, p in enumerate(view['board'], 1):
            if p['profit'] != previous:
                rank = position
            previous = p['profit']
            rows.append({'排名': rank, '玩家': p['name'], '總盈虧': p['profit'], '報酬率 %': p['return_pct'],
                         '最大回撤 %': p['max_drawdown_pct'], '成交次數': p['fills'],
                         '賣出樣本': p['sell_samples'], '勝率 %': p['win_rate'], '獲利因子': str(p['profit_factor'])})
        st.dataframe(rows, hide_index=True, use_container_width=True)
        market = view['market']
        st.caption(f"{market['symbol']} {market['name']}｜{market['bars'][0]['Date']} ～ {market['bars'][-1]['Date']}｜{market['source']}")
        own = view['player']
        st.markdown('#### 我的操作分析')
        stats = next(p for p in view['board'] if p['name'] == own['name'] and not p['bot'])
        st.write(f"成交 {stats['fills']} 次，最大資產回撤 {stats['max_drawdown_pct']:.2f}%。")
        if stats['sell_samples'] < 3:
            st.info('有效賣出少於三筆，樣本不足；不做交易能力定論。')
        else:
            st.write('依每筆成交時點檢視進出場；最大回撤反映資產風險，獲利因子顯示賣出獲利相對虧損。')
        turnover = sum(f['value'] for f in own['fills']) / 1_000_000
        st.write(f"資金成交週轉 {turnover:.2f} 倍；使用 Option {len(own['pauses'])}/3 次。")
        if stats['max_drawdown_pct'] >= 5:
            st.write('本場資產回撤超過 5%，可檢查持倉是否過度集中。')
        if stats['fills'] >= 12:
            st.write('本場成交至少十二次；加入真實費稅後，頻繁進出會增加成本。')
        st.caption('勝率按賣出成交分筆計算，分批賣出會增加樣本；不作人格評分。未計費稅、滑價、股息。')
        st.dataframe(own['fills'], hide_index=True, use_container_width=True)
        if view['host']:
            if st.button('🔁 再來一局（保留隊伍）', type='primary', use_container_width=True):
                try:
                    store.rematch(code, token, view['round'])
                    st.rerun(scope='app')
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.info('等待房主開啟下一局；房號與隊伍會保留，不用重新加入。')
    settlement()

if st.button('🏠 回主選單'):
    st.query_params.clear()
    st.switch_page('app.py')
