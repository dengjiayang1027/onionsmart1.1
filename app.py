import time
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from replay_engine import interpolate_bar, decision_progresses
from trading_engine import open_position, close_position

st.set_page_config(page_title="蔥明錢 Lite", page_icon="🧅", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
html,body,[data-testid="stAppViewContainer"]{background:#08111a;color:#eef5f9}
[data-testid="stHeader"],[data-testid="stToolbar"]{display:none}.block-container{padding:.45rem .55rem .8rem;max-width:100%}
div[data-testid="stVerticalBlockBorderWrapper"]>div{background:#0d1822;border:1px solid #223442;border-radius:12px}
.stButton button{min-height:42px;border-radius:9px;font-weight:800;background:#10202c;color:#f2f7fb}
.brand{font-size:28px;font-weight:900;padding:2px 4px 8px}.sub{color:#73889a;font-size:13px;margin-left:8px}
.cardgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.card{background:#111f2a;border:1px solid #223544;border-radius:9px;padding:9px 10px;min-height:56px}.card .k{font-size:12px;color:#8094a4}.card .v{font-size:20px;font-weight:850;margin-top:3px}
</style>""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def make_data(n=320, seed=12):
    rng=np.random.default_rng(seed); r=rng.normal(.0007,.012,n); close=450*np.cumprod(1+r); close=close/close[-1]*525
    op=np.r_[close[0],close[:-1]*(1+rng.normal(0,.0025,n-1))]
    hi=np.maximum(op,close)*(1+rng.uniform(.002,.011,n)); lo=np.minimum(op,close)*(1-rng.uniform(.002,.011,n))
    return pd.DataFrame({"Date":pd.date_range("2023-01-02",periods=n,freq="B"),"Open":op,"High":hi,"Low":lo,"Close":close})
df=make_data()
defaults={"i":90,"pos":0,"entry":None,"entry_time":None,"entry_replay":None,"entry_qty":0,"entry_sl":0.,"entry_tp":0.,"trade_mode":"Manual","qty":1,"trades":[],"mode":"Manual Replay","progress":0.,"running":False,"pause_until":0.,"pause_reason":"","last_tick":time.time(),"last_full_refresh":time.time(),"dynamic_seconds":8,"decision_seconds":5,"decision_count":2,"decision_seen":set(),"drawings":[],"hidden_drawings":False,"undo":[]}
for k,v in defaults.items():
    if k not in st.session_state: st.session_state[k]=v

def current_bar():
    base=df.iloc[st.session_state.i].copy()
    if st.session_state.mode=="Dynamic Replay":
        evolving=interpolate_bar(base,st.session_state.i,st.session_state.progress)
        for k,v in evolving.items(): base[k]=v
    return base
st.session_state.current_bar=current_bar()

st.markdown('<div class="brand">🧅 蔥明錢 <span class="sub">交易訓練模式</span></div>',unsafe_allow_html=True)
left,right=st.columns([2.55,7.45],gap="small")
with left:
  with st.container(border=True):
    st.session_state.mode=st.radio("Replay 模式",["Manual Replay","Dynamic Replay"],horizontal=True,index=0 if st.session_state.mode=="Manual Replay" else 1)
    if st.session_state.mode=="Dynamic Replay":
      st.session_state.dynamic_seconds=st.slider("每日行情秒數",4,20,st.session_state.dynamic_seconds)
      st.session_state.decision_count=st.slider("每日決策暫停次數",0,4,st.session_state.decision_count)
      st.session_state.decision_seconds=st.slider("決策倒數秒數",3,10,st.session_state.decision_seconds)
      a,b=st.columns(2)
      if a.button("▶ 開始 / 繼續",use_container_width=True): st.session_state.running=True; st.session_state.last_tick=time.time(); st.rerun()
      if b.button("⏸ 暫停",use_container_width=True): st.session_state.running=False; st.rerun()
      if st.session_state.pause_until>time.time(): st.warning(f"市場暫停 {max(1,int(st.session_state.pause_until-time.time()+.99))} 秒｜{st.session_state.pause_reason}")
      elif st.session_state.running: st.caption(f"行情形成中　{st.session_state.progress*100:.0f}%")
    else:
      a,b=st.columns(2)
      if a.button("▶ 下一根",use_container_width=True): st.session_state.i=min(len(df)-1,st.session_state.i+1); st.session_state.progress=0; st.rerun()
      if b.button("⏩ +5 根",use_container_width=True): st.session_state.i=min(len(df)-1,st.session_state.i+5); st.session_state.progress=0; st.rerun()
    st.markdown("### 交易操作")
    reasons=st.multiselect("交易理由",["趨勢","回撤","突破","支撐","壓力","均線","RSI","OB","BOS","Liquidity Sweep","其他"],placeholder="選擇交易理由")
    st.session_state.qty=int(st.number_input("數量",min_value=1,value=int(st.session_state.qty),step=1))
    sl,tp=st.columns(2)
    st.session_state.sl_pct=sl.number_input("SL %",min_value=0.,step=.1,key="sl_input")
    st.session_state.tp_pct=tp.number_input("TP %",min_value=0.,step=.1,key="tp_input")
    buy,sell=st.columns(2)
    if buy.button("⬆ BUY 做多",use_container_width=True):
      st.session_state.running=False; open_position(st.session_state,1,reasons); st.session_state.running=(st.session_state.mode=="Dynamic Replay"); st.session_state.last_tick=time.time(); st.rerun()
    if sell.button("⬇ SELL 做空",use_container_width=True):
      st.session_state.running=False; open_position(st.session_state,-1,reasons); st.session_state.running=(st.session_state.mode=="Dynamic Replay"); st.session_state.last_tick=time.time(); st.rerun()
    x,y,z=st.columns(3)
    if x.button("✕ 平倉",use_container_width=True): st.session_state.running=False; close_position(st.session_state,"Manual",reasons); st.session_state.running=(st.session_state.mode=="Dynamic Replay"); st.session_state.last_tick=time.time(); st.rerun()
    if y.button("＋ 加碼",use_container_width=True) and st.session_state.pos: st.session_state.qty+=1; st.session_state.running=False; st.rerun()
    if z.button("－ 減碼",use_container_width=True) and st.session_state.pos: st.session_state.qty=max(1,st.session_state.qty-1); st.session_state.running=False; st.rerun()
    status="FLAT" if not st.session_state.pos else ("LONG" if st.session_state.pos==1 else "SHORT")
    if st.session_state.pos:
      upnl=(float(st.session_state.current_bar.Close)-st.session_state.entry)/st.session_state.entry*st.session_state.pos*100
      st.caption(f"部位：{status} ｜ 未實現：{upnl:+.2f}%")
    else: st.caption("部位：FLAT")

with right:
  with st.container(border=True):
    row=st.session_state.current_bar
    h1,h2,h3=st.columns([2.1,1.2,4.7]); h1.markdown("### 2330 台積電"); h2.markdown(f"**{row.Date.date()}**")
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
    st.caption("圖表可用左上工具列畫線、矩形、自由畫筆與文字。OHLC-only 動態路徑為合成示意，並非真實盤中歷史。")

trades=pd.DataFrame(st.session_state.trades)
tcol,scol=st.columns([6.5,3.5],gap="small")
with tcol:
  with st.container(border=True):
    st.markdown("### Trade Record")
    if trades.empty: st.caption("尚無已完成交易。平倉後交易將記錄於此。")
    else: st.dataframe(trades.iloc[::-1],use_container_width=True,hide_index=True,height=205)
with scol:
  with st.container(border=True):
    st.markdown("### 交易統計")
    total=float(trades["損益"].sum()) if not trades.empty else 0; wr=float((trades["損益"]>0).mean()*100) if not trades.empty else 0
    count=len(trades); avg=float(trades["R"].mean()) if count else 0; best=float(trades["損益"].max()) if count else 0; worst=float(trades["損益"].min()) if count else 0
    st.markdown(f'<div class="cardgrid"><div class="card"><div class="k">總損益</div><div class="v">{total:+,.0f}</div></div><div class="card"><div class="k">勝率</div><div class="v">{wr:.0f}%</div></div><div class="card"><div class="k">交易次數</div><div class="v">{count}</div></div><div class="card"><div class="k">平均 R</div><div class="v">{avg:.2f}</div></div><div class="card"><div class="k">最大獲利</div><div class="v">{best:+,.0f}</div></div><div class="card"><div class="k">最大虧損</div><div class="v">{worst:+,.0f}</div></div></div>',unsafe_allow_html=True)

# Dynamic loop: a Streamlit fragment reruns frequently while its own clock advances the synthetic session.
if st.session_state.mode=="Dynamic Replay":
  @st.fragment(run_every="200ms")
  def dynamic_clock():
    s=st.session_state; now=time.time()
    if s.running and now>=s.pause_until and s.i<len(df)-1:
      elapsed=max(0.,now-s.last_tick); s.last_tick=now
      s.progress=min(1.,s.progress+elapsed/max(1,s.dynamic_seconds))
      marks=decision_progresses(s.decision_count)
      mark=next((m for m in sorted(marks) if s.progress>=m and (s.i,m) not in s.decision_seen),None)
      if mark is not None:
        s.decision_seen.add((s.i,mark)); s.running=False; s.pause_reason="決策時間"; s.pause_until=now+s.decision_seconds
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
