import time
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta

from replay_engine import interpolate_bar
from trading_engine import open_position, close_position
import market_data

fetch_twse_daily = market_data.fetch_twse_daily
listed_instruments = market_data.listed_instruments


def fetch_tpex_daily(*args, **kwargs):
    loader = getattr(market_data, "fetch_tpex_daily", None)
    if loader is None:
        raise RuntimeError("部署中的行情模組尚未更新，請稍候重新載入後再試。")
    return loader(*args, **kwargs)


def otc_instruments():
    loader = getattr(market_data, "otc_instruments", None)
    if loader is None:
        raise RuntimeError("部署中的行情模組尚未更新，請稍候重新載入後再試。")
    return loader()

st.set_page_config(page_title="蔥明錢 Lite", page_icon="🧅", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
html,body,[data-testid="stAppViewContainer"]{background:#08111a;color:#eef5f9}
[data-testid="stHeader"],[data-testid="stToolbar"]{display:none}.block-container{padding:.45rem .55rem .8rem;max-width:100%}
div[data-testid="stVerticalBlockBorderWrapper"]>div{background:#0d1822;border:1px solid #223442;border-radius:12px}
.stButton button{min-height:42px;border-radius:9px;font-weight:800;background:#10202c;color:#f2f7fb}
.brand{font-size:28px;font-weight:900;padding:2px 4px 8px}.sub{color:#73889a;font-size:13px;margin-left:8px}
.cardgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:7px;padding-bottom:10px}.card{background:#111f2a;border:1px solid #223544;border-radius:9px;padding:8px 9px;min-height:56px}.card .k{font-size:12px;color:#8094a4}.card .v{font-size:18px;font-weight:850;margin-top:3px}
</style>""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def make_data(n=320, seed=12):
    rng=np.random.default_rng(seed); r=rng.normal(.0007,.012,n); close=450*np.cumprod(1+r); close=close/close[-1]*525
    op=np.r_[close[0],close[:-1]*(1+rng.normal(0,.0025,n-1))]
    hi=np.maximum(op,close)*(1+rng.uniform(.002,.011,n)); lo=np.minimum(op,close)*(1-rng.uniform(.002,.011,n))
    return pd.DataFrame({"Date":pd.date_range("2023-01-02",periods=n,freq="B"),"Open":op,"High":hi,"Low":lo,"Close":close,"Volume":0})
defaults={"i":90,"pos":0,"entry":None,"entry_time":None,"entry_replay":None,"entry_qty":0,"entry_sl":0.,"entry_tp":0.,"trade_mode":"Manual","qty":1,"trades":[],"order_events":[],"mode":"Manual Replay","progress":0.,"running":False,"pause_until":0.,"pause_reason":"","last_tick":time.time(),"last_full_refresh":time.time(),"dynamic_seconds":8,"drawings":[],"hidden_drawings":False,"undo":[]}
for k,v in defaults.items():
    if k not in st.session_state: st.session_state[k]=v

if "listed_instruments" not in st.session_state:
    st.session_state.listed_instruments = [{"code": "2330", "name": "台積電"}]
if "otc_instruments" not in st.session_state:
    st.session_state.otc_instruments = [{"code": "3297", "name": "杭特"}]
if "market_bars" not in st.session_state:
    st.session_state.market_bars = make_data()
    st.session_state.market_symbol = "2330"
    st.session_state.market_name = "台積電"
    st.session_state.market_source = "示範行情（模擬資料）"

with st.expander("📈 行情設定｜台灣上市／上櫃・日線", expanded=False):
    choose_col, date_col, action_col = st.columns([2.2, 2.4, 1.2])
    with choose_col:
        market = st.radio("市場", ["上市", "上櫃"], horizontal=True, key="market_venue")
        instruments_key = "listed_instruments" if market == "上市" else "otc_instruments"
        fetch_list = listed_instruments if market == "上市" else otc_instruments
        market_label = "上市" if market == "上市" else "上櫃"
        if st.button(f"↻ 更新{market_label}標的清單", help="搜尋清單取自交易所最新每日行情"):
            try:
                with st.spinner(f"讀取{market_label}標的…"):
                    st.session_state[instruments_key] = fetch_list()
                st.success(f"{market_label}標的清單已更新，共 {len(st.session_state[instruments_key])} 檔")
            except Exception as exc:
                st.error(str(exc))
        options = st.session_state[instruments_key]
        labels = {f"{item['code']}｜{item['name']}": item for item in options}
        if not labels:
            st.error("目前標的清單是空的，請更新清單或直接輸入代碼。")
            selected = None
        else:
            current = next((label for label, item in labels.items() if item["code"] == st.session_state.market_symbol), next(iter(labels)))
            selected = st.selectbox("搜尋代碼或名稱", list(labels), index=list(labels).index(current), key=f"instrument_{market}")
        manual_code = st.text_input(f"選單找不到時，直接輸入{market_label}代碼", max_chars=6, placeholder="例如 3297")
    with date_col:
        today = date.today()
        default_start = today - timedelta(days=183)
        date_range = st.date_input("歷史區間", value=(default_start, today), max_value=today)
        st.caption("目前支援 1D；每次最多查詢 25 個月。")
    with action_col:
        st.caption("載入新行情會重設目前練習紀錄。")
        load_market = st.button("載入日線", type="primary", use_container_width=True)
    if load_market:
        if len(date_range) != 2:
            st.warning("請選擇完整的開始與結束日期。")
        else:
            instrument = labels[selected] if selected else None
            if manual_code.strip():
                code = manual_code.strip()
                if not code.isdigit():
                    st.error("請輸入純數字股票代碼。")
                    st.stop()
                instrument = {"code": code, "name": next((item["name"] for item in options if item["code"] == code), code)}
            if instrument is None:
                st.stop()
            try:
                with st.spinner(f"載入 {instrument['code']} 歷史日線…"):
                    loader = fetch_twse_daily if market == "上市" else fetch_tpex_daily
                    loaded = loader(instrument["code"], date_range[0], date_range[1])
                st.session_state.market_bars = loaded
                st.session_state.market_symbol = instrument["code"]
                st.session_state.market_name = instrument["name"]
                st.session_state.market_source = "臺灣證券交易所｜歷史日成交資訊" if market == "上市" else "證券櫃檯買賣中心｜個股日成交資訊"
                st.session_state.i = min(90, len(loaded) - 1)
                st.session_state.pos = 0
                st.session_state.entry = None
                st.session_state.entry_qty = 0
                st.session_state.progress = 0.0
                st.session_state.running = False
                st.session_state.trades = []
                st.session_state.order_events = []
                st.session_state.drawings = []
                st.session_state.undo = []
                st.success(f"載入完成：{instrument['code']} {instrument['name']}，{len(loaded)} 根日 K")
            except Exception as exc:
                st.error(f"行情載入失敗：{exc}；目前仍可使用示範行情。")

df = st.session_state.market_bars
st.caption(f"行情：{st.session_state.market_source}｜{st.session_state.market_symbol} {st.session_state.market_name}｜{len(df)} 根日 K")
st.session_state.i = min(max(0, int(st.session_state.i)), len(df) - 1)

def current_bar():
    base=df.iloc[st.session_state.i].copy()
    if st.session_state.mode=="Dynamic Replay":
        evolving=interpolate_bar(base,st.session_state.i,st.session_state.progress)
        for k,v in evolving.items(): base[k]=v
    return base

def resume_after_trade_action():
    """Resume the 8-second Dynamic Replay only after the trade action has completed."""
    st.session_state.running = st.session_state.mode == "Dynamic Replay"
    st.session_state.last_tick = time.time()

def log_order(state, action, reasons=None):
    """Record a submitted trading-panel action in the replay operation log."""
    row = state.current_bar
    state.order_events.append({
        "日期": str(row["Date"].date()), "Replay 時點": int(state.i),
        "股票": f"{st.session_state.market_symbol} {st.session_state.market_name}", "操作": action,
        "價格": round(float(row["Close"]), 2), "數量": int(state.qty),
        "部位": "多" if state.pos == 1 else ("空" if state.pos == -1 else "空手"),
        "SL %": float(getattr(state, "sl_pct", 0) or 0),
        "TP %": float(getattr(state, "tp_pct", 0) or 0),
        "交易理由": "、".join(reasons or []), "交易模式": "Manual",
    })

st.session_state.current_bar=current_bar()
trades=pd.DataFrame(st.session_state.trades)

st.markdown('<div class="brand">🧅 蔥明錢 <span class="sub">交易訓練模式</span></div>',unsafe_allow_html=True)
left,right=st.columns([2.55,7.45],gap="small")
with left:
  with st.container(border=True):
    st.session_state.mode=st.radio("Replay 模式",["Manual Replay","Dynamic Replay"],horizontal=True,index=0 if st.session_state.mode=="Manual Replay" else 1)
    if st.session_state.mode=="Dynamic Replay":
      st.caption("每根日 K 固定 8 秒；只有交易操作會暫停行情。")
      play_label = "⏸ 暫停" if st.session_state.running else "▶ 開始 / 繼續"
      if st.button(play_label,use_container_width=True):
        st.session_state.running = not st.session_state.running
        if st.session_state.running: st.session_state.last_tick=time.time()
        st.rerun()
      if st.session_state.pause_until>time.time(): st.warning(f"市場暫停 {max(1,int(st.session_state.pause_until-time.time()+.99))} 秒｜{st.session_state.pause_reason}")
      elif st.session_state.running: st.caption(f"行情形成中　{st.session_state.progress*100:.0f}%")
    else:
      a,b=st.columns(2)
      if a.button("▶ 下一根",use_container_width=True): st.session_state.i=min(len(df)-1,st.session_state.i+1); st.session_state.progress=0; st.rerun()
      if b.button("⏩ +5 根",use_container_width=True): st.session_state.i=min(len(df)-1,st.session_state.i+5); st.session_state.progress=0; st.rerun()
  with st.container(border=True):
    st.markdown("### 交易統計")
    total=float(trades["損益"].sum()) if not trades.empty else 0
    wr=float((trades["損益"]>0).mean()*100) if not trades.empty else 0
    count=len(trades); avg=float(trades["R"].mean()) if count else 0
    best=float(trades["損益"].max()) if count else 0; worst=float(trades["損益"].min()) if count else 0
    st.markdown(f'<div class="cardgrid"><div class="card"><div class="k">總損益</div><div class="v">{total:+,.0f}</div></div><div class="card"><div class="k">勝率</div><div class="v">{wr:.0f}%</div></div><div class="card"><div class="k">交易次數</div><div class="v">{count}</div></div><div class="card"><div class="k">平均 R</div><div class="v">{avg:.2f}</div></div><div class="card"><div class="k">最大獲利</div><div class="v">{best:+,.0f}</div></div><div class="card"><div class="k">最大虧損</div><div class="v">{worst:+,.0f}</div></div></div>',unsafe_allow_html=True)
with right:
  chart_col, trade_col = st.columns([7.3,2.7],gap="small")
  with chart_col:
   with st.container(border=True):
    row=st.session_state.current_bar
    h1,h2,h3=st.columns([2.1,1.2,4.7]); h1.markdown(f"### {st.session_state.market_symbol} {st.session_state.market_name}"); h2.markdown(f"**{row.Date.date()}**")
    h3.markdown(f"開 {row.Open:.1f}　高 {row.High:.1f}　低 {row.Low:.1f}　現價 **{row.Close:.1f}**")
    start=max(0,st.session_state.i-119); vis=df.iloc[start:st.session_state.i+1].copy()
    if st.session_state.mode=="Dynamic Replay":
      evolving=interpolate_bar(df.iloc[st.session_state.i],st.session_state.i,st.session_state.progress)
      vis=vis.iloc[:-1].copy(); vis=pd.concat([vis,pd.DataFrame([{**evolving,"Date":row.Date}])],ignore_index=True)
    fig=go.Figure(go.Candlestick(x=vis.Date,open=vis.Open,high=vis.High,low=vis.Low,close=vis.Close,name="價格"))
    if st.session_state.pos:
      fig.add_hline(y=st.session_state.entry,line_dash="dot",line_color="#f3b64c",annotation_text="Entry")
    if not st.session_state.hidden_drawings:
      for shape in st.session_state.drawings: fig.add_shape(**shape)
    fig.update_layout(height=500,margin=dict(l=3,r=3,t=2,b=2),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",xaxis_rangeslider_visible=False,showlegend=False,font=dict(color="#aebdca",size=11),xaxis=dict(gridcolor="#172a37",nticks=7),yaxis=dict(gridcolor="#172a37",side="right"),dragmode="pan")
    chart=st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":True,"scrollZoom":False,"staticPlot":False,"modeBarButtonsToAdd":["drawline","drawopenpath","drawrect","drawcircle","drawtext","eraseshape"],"edits":{"shapePosition":True}})
    # Plotly modebar provides trend lines, rectangles, freehand, text, erase, and built-in undo/redo.
    p,q,r=st.columns(3)
    if p.button("↶ Undo",use_container_width=True) and st.session_state.drawings: st.session_state.undo.append(st.session_state.drawings.pop()); st.rerun()
    if q.button("顯示 / 隱藏圖形",use_container_width=True): st.session_state.hidden_drawings=not st.session_state.hidden_drawings; st.rerun()
    if r.button("刪除圖形",use_container_width=True): st.session_state.drawings=[]; st.rerun()
    st.caption("圖表可用左上工具列畫線、矩形、自由畫筆與文字。動態日 K 僅為 OHLC 推演，並非真實盤中歷史。行情來源：臺灣證券交易所；示範行情為模擬資料。")
  with trade_col:
   with st.container(border=True):
    st.markdown("### 交易操作")
    reasons=st.multiselect("交易理由",["趨勢","回撤","突破","支撐","壓力","均線","RSI","OB","BOS","Liquidity Sweep","其他"],placeholder="選擇交易理由",key="trade_reasons")
    st.session_state.qty=int(st.number_input("數量",min_value=1,value=int(st.session_state.qty),step=1))
    st.session_state.sl_pct=st.number_input("SL %",min_value=0.,step=.1,key="sl_input")
    st.session_state.tp_pct=st.number_input("TP %",min_value=0.,step=.1,key="tp_input")
    if st.button("⬆ BUY 做多",use_container_width=True):
      st.session_state.running=False; open_position(st.session_state,1,reasons); log_order(st.session_state,"BUY 做多",reasons); resume_after_trade_action(); st.rerun()
    if st.button("⬇ SELL 做空",use_container_width=True):
      st.session_state.running=False; open_position(st.session_state,-1,reasons); log_order(st.session_state,"SELL 做空",reasons); resume_after_trade_action(); st.rerun()
    if st.button("✕ 平倉",use_container_width=True):
      st.session_state.running=False
      if st.session_state.pos: log_order(st.session_state,"平倉",reasons)
      close_position(st.session_state,"Manual",reasons); resume_after_trade_action(); st.rerun()
    a,b=st.columns(2)
    if a.button("＋ 加碼",use_container_width=True):
      st.session_state.running=False
      if st.session_state.pos:
        st.session_state.qty+=1; st.session_state.entry_qty+=1; log_order(st.session_state,"加碼",reasons)
      resume_after_trade_action(); st.rerun()
    if b.button("－ 減碼",use_container_width=True):
      st.session_state.running=False
      if st.session_state.pos and st.session_state.entry_qty>1:
        st.session_state.qty=max(1,st.session_state.qty-1); st.session_state.entry_qty-=1; log_order(st.session_state,"減碼",reasons)
      resume_after_trade_action(); st.rerun()
    status="FLAT" if not st.session_state.pos else ("LONG" if st.session_state.pos==1 else "SHORT")
    if st.session_state.pos:
      upnl=(float(st.session_state.current_bar.Close)-st.session_state.entry)/st.session_state.entry*st.session_state.pos*100
      st.caption(f"部位：{status} ｜ 未實現：{upnl:+.2f}%")
    else: st.caption("部位：FLAT")
with st.container(border=True):
  st.markdown("### Trade Record｜操作紀錄")
  order_events=pd.DataFrame(st.session_state.order_events)
  if order_events.empty: st.caption("尚無交易操作。BUY、SELL、加減碼與平倉都會記錄於此。")
  else: st.dataframe(order_events.iloc[::-1],use_container_width=True,hide_index=True,height=205)

# Dynamic loop: a Streamlit fragment reruns frequently while its own clock advances the synthetic session.
if st.session_state.mode=="Dynamic Replay":
  @st.fragment(run_every="200ms")
  def dynamic_clock():
    s=st.session_state; now=time.time()
    if s.running and now>=s.pause_until and s.i<len(df)-1:
      elapsed=max(0.,now-s.last_tick); s.last_tick=now
      s.progress=min(1.,s.progress+elapsed/8.0)
      if s.progress>=1:
        s.i+=1; s.progress=0.; s.last_tick=now
    elif not s.running and s.pause_until and now>=s.pause_until:
      s.running=True; s.pause_until=0.; s.last_tick=now
    st.session_state.current_bar=current_bar()
    # Refresh the full page at the fragment cadence so the evolving OHLC and chart repaint together.
    if (s.running or s.pause_until>now) and now-s.last_full_refresh>=.18:
      s.last_full_refresh=now
      st.rerun(scope="app")
  dynamic_clock()
