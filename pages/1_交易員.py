import time
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta
from pathlib import Path

from replay_engine import interpolate_bar, advance_clock, replay_finished
from trading_engine import open_position, close_position, log_order
from scorecard import METRICS, compute_scorecard
import market_data
from mobile_layout import MOBILE_CSS

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

st.markdown(MOBILE_CSS, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def make_data(n=320, seed=12):
    rng=np.random.default_rng(seed); r=rng.normal(.0007,.012,n); close=450*np.cumprod(1+r); close=close/close[-1]*525
    op=np.r_[close[0],close[:-1]*(1+rng.normal(0,.0025,n-1))]
    hi=np.maximum(op,close)*(1+rng.uniform(.002,.011,n)); lo=np.minimum(op,close)*(1-rng.uniform(.002,.011,n))
    return pd.DataFrame({"Date":pd.date_range("2023-01-02",periods=n,freq="B"),"Open":op,"High":hi,"Low":lo,"Close":close,"Volume":0})
defaults={"i":90,"replay_start_index":90,"replay_completed":False,"pos":0,"entry":None,"entry_time":None,"entry_replay":None,"entry_qty":0,"entry_sl":0.,"entry_tp":0.,"trade_mode":"Manual","qty":1,"trades":[],"order_events":[],"mode":"Manual Replay","progress":0.,"running":False,"pause_until":0.,"pause_reason":"","last_tick":time.time(),"last_full_refresh":time.time(),"dynamic_seconds":8,"decision_count":2,"decision_seconds":5,"editing_trade":False,"resume_trade":False,"previous_mode":"Manual Replay","drawings":[],"hidden_drawings":False,"undo":[]}
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
    st.session_state.replay_start_index = 90

with st.expander("📈 選股與期間｜台灣上市／上櫃・日線", expanded=False):
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
                if loaded.empty:
                    st.warning("所選區間沒有可播放的行情資料，請調整標的或日期。")
                    st.stop()

                st.session_state.market_bars = loaded
                st.session_state.market_symbol = instrument["code"]
                st.session_state.market_name = instrument["name"]
                st.session_state.market_source = "臺灣證券交易所｜歷史日成交資訊" if market == "上市" else "證券櫃檯買賣中心｜個股日成交資訊"
                st.session_state.replay_start_index = 0

                st.session_state.i = 0
                st.session_state.pos = 0
                st.session_state.entry = None
                st.session_state.entry_qty = 0
                st.session_state.progress = 0.0
                st.session_state.running = False
                st.session_state.editing_trade = False
                st.session_state.resume_trade = False
                st.session_state.pending_side = 0
                st.session_state.pause_until = 0.0
                st.session_state.replay_completed = False
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
    s = st.session_state
    s.editing_trade = False
    s.running = s.resume_trade and s.mode == "Dynamic Replay" and not s.replay_completed
    s.resume_trade = False
    s.pending_side = 0
    if s.pause_until:
        s.pause_until = time.time() + s.decision_seconds
    s.last_tick = time.time()


def prepare_trade(side):
    s = st.session_state
    if not s.editing_trade:
        s.resume_trade = s.running
    s.running = False
    s.editing_trade = True
    s.pending_side = side
    s.last_tick = time.time()

st.session_state.current_bar=current_bar()
if not st.session_state.replay_completed and replay_finished(st.session_state, len(df)):
    st.session_state.running = False
    if st.session_state.pos:
        close_position(st.session_state, "區間結束", [])
    st.session_state.replay_completed = True
    st.rerun()
trades=pd.DataFrame(st.session_state.trades)

if st.button("🏠 回主選單"):
    st.session_state.running = False
    st.session_state.resume_trade = False
    st.session_state.editing_trade = False
    st.session_state.last_tick = time.time()
    st.switch_page("app.py")
st.markdown('<div class="brand">🧅 蔥明錢 <span class="sub">交易訓練模式</span></div>',unsafe_allow_html=True)
def render_replay_controls():
    with st.container(border=True):
      st.session_state.mode=st.radio("Replay 模式",["Manual Replay","Dynamic Replay"],horizontal=True,index=0 if st.session_state.mode=="Manual Replay" else 1)
      if st.session_state.mode != st.session_state.previous_mode:
        s = st.session_state
        s.running = False
        s.editing_trade = False
        s.resume_trade = False
        s.pending_side = 0
        s.pause_until = 0.0
        s.last_tick = time.time()
        if s.mode == "Dynamic Replay":
          s.progress = 1.0  # The manual candle was already revealed.
          if s.i < len(df) - 1:
            s.i += 1
            s.progress = 0.0
        s.previous_mode = s.mode
        st.rerun()
      if st.session_state.mode=="Dynamic Replay":
        with st.expander("動態回放設定"):
          st.number_input("每根決策次數", min_value=0, max_value=4, key="decision_count", disabled=st.session_state.running)
          st.number_input("決策秒數", min_value=1, max_value=30, key="decision_seconds", disabled=st.session_state.running)
        st.caption("每根日 K 行情演進 8 秒，決策與交易操作時間另計；路徑為 OHLC 模擬。")
        play_label = "⏸ 暫停" if st.session_state.running else "▶ 開始 / 繼續"
        if st.button(play_label,use_container_width=True,shortcut="Space",disabled=st.session_state.replay_completed or st.session_state.editing_trade):
          st.session_state.running = not st.session_state.running
          if st.session_state.running: st.session_state.last_tick=time.time()
          st.rerun()
        if st.session_state.pause_until>time.time(): st.warning(f"市場暫停 {max(1,int(st.session_state.pause_until-time.time()+.99))} 秒｜{st.session_state.pause_reason}")
        elif st.session_state.running: st.caption(f"行情形成中　{st.session_state.progress*100:.0f}%")
      else:
        a,b=st.columns(2)
        if a.button("▶ 下一根",use_container_width=True): st.session_state.i=min(len(df)-1,st.session_state.i+1); st.session_state.progress=0; st.rerun()
        if b.button("⏩ +5 根",use_container_width=True): st.session_state.i=min(len(df)-1,st.session_state.i+5); st.session_state.progress=0; st.rerun()


def render_statistics():
    with st.container(border=True):
      st.markdown("### 交易統計")
      total=float(trades["損益"].sum()) if not trades.empty else 0
      wr=float((trades["損益"]>0).mean()*100) if not trades.empty else 0
      count=len(trades); avg=float(trades["R"].mean()) if count else 0
      best=float(trades["損益"].max()) if count else 0; worst=float(trades["損益"].min()) if count else 0
      st.markdown(f'<div class="cardgrid"><div class="card"><div class="k">總損益</div><div class="v">{total:+,.0f}</div></div><div class="card"><div class="k">勝率</div><div class="v">{wr:.0f}%</div></div><div class="card"><div class="k">交易次數</div><div class="v">{count}</div></div><div class="card"><div class="k">平均 R</div><div class="v">{avg:.2f}</div></div><div class="card"><div class="k">最大獲利</div><div class="v">{best:+,.0f}</div></div><div class="card"><div class="k">最大虧損</div><div class="v">{worst:+,.0f}</div></div></div>',unsafe_allow_html=True)


def render_chart():
    with st.container(border=True):
     row=st.session_state.current_bar
     st.markdown(f"### {st.session_state.market_symbol} {st.session_state.market_name}　{row.Date.date()}")
     st.markdown(f"開 {row.Open:.1f}　高 {row.High:.1f}　低 {row.Low:.1f}　現價 **{row.Close:.1f}**")
     start=max(0,st.session_state.i-119); vis=df.iloc[start:st.session_state.i+1].copy()
     if st.session_state.mode=="Dynamic Replay":
       evolving=interpolate_bar(df.iloc[st.session_state.i],st.session_state.i,st.session_state.progress)
       vis=vis.iloc[:-1].copy(); vis=pd.concat([vis,pd.DataFrame([{**evolving,"Date":row.Date}])],ignore_index=True)
     fig=go.Figure(go.Candlestick(x=vis.Date,open=vis.Open,high=vis.High,low=vis.Low,close=vis.Close,name="價格"))
     if st.session_state.pos:
       fig.add_hline(y=st.session_state.entry,line_dash="dot",line_color="#f3b64c",annotation_text="Entry")
     if not st.session_state.hidden_drawings:
       for shape in st.session_state.drawings: fig.add_shape(**shape)
     fig.update_layout(height=360,margin=dict(l=3,r=3,t=2,b=2),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",xaxis_rangeslider_visible=False,showlegend=False,font=dict(color="#aebdca",size=11),xaxis=dict(gridcolor="#172a37",nticks=7),yaxis=dict(gridcolor="#172a37",side="right"),dragmode="pan")
     chart=st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":True,"displaylogo":False,"scrollZoom":False,"staticPlot":False,"modeBarButtonsToAdd":["drawline","drawopenpath","drawrect","drawcircle","drawtext","eraseshape"],"edits":{"shapePosition":True}})
     # Plotly modebar provides trend lines, rectangles, freehand, text, erase, and built-in undo/redo.
     p,q,r=st.columns(3)
     if p.button("↶ Undo",use_container_width=True) and st.session_state.drawings: st.session_state.undo.append(st.session_state.drawings.pop()); st.rerun()
     if q.button("顯示 / 隱藏圖形",use_container_width=True): st.session_state.hidden_drawings=not st.session_state.hidden_drawings; st.rerun()
     if r.button("刪除圖形",use_container_width=True): st.session_state.drawings=[]; st.rerun()
     st.caption("圖表可用左上工具列畫線、矩形、自由畫筆與文字。動態日 K 僅為 OHLC 推演，並非真實盤中歷史。行情來源：臺灣證券交易所；示範行情為模擬資料。")


def render_trade_controls():
    with st.container(border=True):
     st.markdown("### 交易操作")
     st.caption("點買入／賣出，再按送出交易確認。電腦亦可用 B／S／Enter；空白控制動態播放。")
     buy_key, sell_key = st.columns(2)
     if buy_key.button("⬆ BUY 做多", shortcut="B", disabled=st.session_state.replay_completed):
       prepare_trade(1)
       st.rerun()
     if sell_key.button("⬇ SELL 做空", shortcut="S", disabled=st.session_state.replay_completed):
       prepare_trade(-1)
       st.rerun()
     if st.session_state.mode == "Dynamic Replay" and not st.session_state.replay_completed:
       if not st.session_state.editing_trade:
         if st.button("暫停並編輯交易", use_container_width=True):
           st.session_state.resume_trade = st.session_state.running
           st.session_state.running = False
           st.session_state.editing_trade = True
           st.session_state.last_tick = time.time()
           st.rerun()
     if st.session_state.editing_trade and st.button("取消編輯", use_container_width=True):
       resume_after_trade_action()
       st.rerun()
     trade_disabled = st.session_state.replay_completed or (st.session_state.mode == "Dynamic Replay" and not st.session_state.editing_trade)
     reasons=st.multiselect("交易理由",["趨勢","回撤","突破","支撐","壓力","均線","RSI","OB","BOS","Liquidity Sweep","其他"],placeholder="選擇交易理由",key="trade_reasons",disabled=trade_disabled)
     st.session_state.qty=int(st.number_input("數量",min_value=1,value=int(st.session_state.qty),step=1,disabled=trade_disabled))
     st.session_state.sl_pct=st.number_input("SL %",min_value=0.,step=.1,key="sl_input",disabled=trade_disabled)
     st.session_state.tp_pct=st.number_input("TP %",min_value=0.,step=.1,key="tp_input",disabled=trade_disabled)
     pending_side = st.session_state.get("pending_side", 0)
     if pending_side:
       st.info(f"待送出：{'買入做多' if pending_side == 1 else '賣出做空'} {st.session_state.qty} 單位，價格 {float(st.session_state.current_bar.Close):.2f}")
     if st.button("送出交易", shortcut="Enter", type="primary", use_container_width=True, disabled=trade_disabled or not pending_side):
       open_position(st.session_state,pending_side,reasons)
       resume_after_trade_action()
       st.rerun()
     if st.button("✕ 平倉",use_container_width=True,disabled=trade_disabled):
       st.session_state.running=False
       close_position(st.session_state,"Manual",reasons); resume_after_trade_action(); st.rerun()
     a,b=st.columns(2)
     if a.button("＋ 加碼",use_container_width=True,disabled=trade_disabled):
       st.session_state.running=False
       if st.session_state.pos:
         st.session_state.qty+=1; st.session_state.entry_qty+=1; log_order(st.session_state,"加碼",reasons)
       resume_after_trade_action(); st.rerun()
     if b.button("－ 減碼",use_container_width=True,disabled=trade_disabled):
       st.session_state.running=False
       if st.session_state.pos and st.session_state.entry_qty>1:
         st.session_state.qty=max(1,st.session_state.qty-1); st.session_state.entry_qty-=1; log_order(st.session_state,"減碼",reasons)
       resume_after_trade_action(); st.rerun()
     status="FLAT" if not st.session_state.pos else ("LONG" if st.session_state.pos==1 else "SHORT")
     if st.session_state.pos:
       upnl=(float(st.session_state.current_bar.Close)-st.session_state.entry)/st.session_state.entry*st.session_state.pos*100
       st.caption(f"部位：{status} ｜ 未實現：{upnl:+.2f}%")
     else: st.caption("部位：FLAT")


with st.container(key="price_chart"):
    render_chart()
with st.container(key="training_controls"):
    replay_col, trade_col = st.columns([.9, 1.5], gap="small")
    with replay_col:
        render_replay_controls()
    with trade_col:
        render_trade_controls()
with st.container(key="trade_statistics"):
    render_statistics()
with st.container(border=True):
  st.markdown("### Trade Record｜已平倉交易")
  if trades.empty: st.caption("尚無已平倉交易。")
  else: st.dataframe(trades.iloc[::-1],use_container_width=True,hide_index=True)
  st.caption("紀錄暫存於本次 Session；R 目前仍採損益百分比 ÷ 3 的示範算法。")
  st.markdown("### 操作紀錄")
  order_events=pd.DataFrame(st.session_state.order_events)
  if order_events.empty: st.caption("尚無交易操作。BUY、SELL、加減碼與平倉都會記錄於此。")
  else: st.dataframe(order_events.iloc[::-1],use_container_width=True,hide_index=True,height=205)

if st.session_state.replay_completed:
  result = compute_scorecard(
      pd.DataFrame(st.session_state.trades), df,
      st.session_state.replay_start_index, st.session_state.i,
  )
  st.markdown("## 📊 本次練習成績單")
  st.caption(f"{df.iloc[st.session_state.replay_start_index].Date.date()} ～ {df.iloc[st.session_state.i].Date.date()}｜六項能力皆為 1–5 分，越高代表表現越好。")
  summary_a, summary_b, summary_c = st.columns(3)
  summary_a.metric("本次總損益", f"{result['total_profit']:+,.0f}")
  summary_b.metric("勝率", f"{result['win_rate']:.0%}")
  summary_c.metric("完成交易", f"{result['trade_count']} 筆")

  score_col, persona_col = st.columns([1.25, .75], gap="large")
  with score_col:
    radar_values = [result["scores"][metric] for metric in METRICS]
    radar = go.Figure(go.Scatterpolar(
        r=radar_values + [radar_values[0]],
        theta=list(METRICS) + [METRICS[0]],
        fill="toself",
        fillcolor="rgba(77, 163, 230, .24)",
        line=dict(color="#4da3e6", width=3),
        marker=dict(size=9, color="#4da3e6", line=dict(color="#dceeff", width=1.5)),
        hovertemplate="%{theta}：%{r:.1f}/5<extra></extra>",
    ))
    radar.update_layout(
        height=430, margin=dict(l=42, r=42, t=44, b=36),
        paper_bgcolor="#08111a", plot_bgcolor="#08111a",
        font=dict(color="#f2f7fb", size=15), showlegend=False,
        polar=dict(
            bgcolor="#08111a",
            angularaxis=dict(direction="clockwise", rotation=90, gridcolor="#465360", linecolor="#465360"),
            radialaxis=dict(visible=True, range=[0, 5], tickmode="array", tickvals=[1, 2, 3, 4, 5],
                            tickfont=dict(size=10, color="#93a4b1"), gridcolor="#3a4652", linecolor="#3a4652"),
        ),
    )
    st.plotly_chart(radar, use_container_width=True, config={"displayModeBar": False})
    st.markdown("### 六項能力")
    left_metrics, right_metrics = st.columns(2, gap="medium")
    for index, metric in enumerate(METRICS):
      target = left_metrics if index % 2 == 0 else right_metrics
      score = result["scores"][metric]
      with target:
        st.markdown(f"**{metric}　{score:.1f} / 5**　·　{result['samples'][metric]} 筆樣本")
        st.progress(max(0.0, min(1.0, (score - 1.0) / 4.0)))
        st.caption(result["notes"][metric])
  with persona_col:
    st.markdown("### 🧙 本次交易人格")
    if result["role"]:
      st.subheader(result["role"])
      role_image = Path(__file__).resolve().parent.parent / "assets" / "occupations" / "reference-art" / result["role_image"]
      if role_image.exists():
        st.image(str(role_image), use_container_width=True)
      st.markdown(f"**優勢組合：** {'＋'.join(result['top_pair'])}")
      st.write(result["role_description"])
    else:
      st.info("完成至少兩項有效能力樣本後，系統會依最高的兩項能力顯示職業人格。")
    st.caption("職業由六項能力中分數最高的兩項決定；同分時依 守、效、買、賣、盈、穩 順序判定。")
  with st.expander("查看評分說明"):
    st.markdown("""
    - **守**：最大資產回撤越小，分數越高。
    - **效**：獲利因子（總獲利 ÷ 總虧損）越高，分數越高。
    - **買**：進場後下一根完整 K 棒走勢越有利，分數越高。
    - **賣**：平倉後行情越少沿原持倉方向延續，分數越高。
    - **盈**：實際落袋的獲利越接近持倉期間最大浮盈，分數越高。
    - **穩**：交易 R 值波動越小且平均為正，分數越高。

    買、賣、盈、穩少於 3 筆有效樣本時，以中間分 3/5 顯示並註明樣本不足。總損益另列，不納入六邊形。
    """)
  if st.button("↻ 重新練習此日期區間", type="primary"):
    st.session_state.i = st.session_state.replay_start_index
    st.session_state.pos = 0
    st.session_state.entry = None
    st.session_state.entry_time = None
    st.session_state.entry_replay = None
    st.session_state.entry_qty = 0
    st.session_state.progress = 0.0
    st.session_state.running = False
    st.session_state.replay_completed = False
    st.session_state.editing_trade = False
    st.session_state.resume_trade = False
    st.session_state.pending_side = 0
    st.session_state.pause_until = 0.0
    st.session_state.trades = []
    st.session_state.order_events = []
    st.rerun()


# Dynamic loop: a Streamlit fragment reruns frequently while its own clock advances the synthetic session.
if st.session_state.mode=="Dynamic Replay":
  @st.fragment(run_every="200ms")
  def dynamic_clock():
    s=st.session_state; now=time.time()
    advance_clock(s, now, len(df))
    st.session_state.current_bar=current_bar()
    # Refresh the full page at the fragment cadence so the evolving OHLC and chart repaint together.
    if (s.running or replay_finished(s, len(df))) and not s.replay_completed and now-s.last_full_refresh>=.18:
      s.last_full_refresh=now
      st.rerun(scope="app")
  dynamic_clock()
