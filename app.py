import streamlit as st

st.set_page_config(
    page_title="蔥明錢 Lite",
    page_icon="🧅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp { background: #08111a; color: #eef5f9; }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1120px; padding-top: 3rem; }
    .hero { text-align: center; padding: 2.2rem 1rem 1.5rem; }
    .hero h1 { font-size: 3rem; margin-bottom: .35rem; }
    .hero p { color: #9aabba; font-size: 1.1rem; }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
      background: #0d1822; border: 1px solid #223442; border-radius: 16px;
      min-height: 245px;
    }
    .mode-icon { font-size: 2rem; }
    .mode-copy { color: #aebdca; min-height: 68px; }
    .stButton button, a[data-testid="stPageLink-NavLink"] {
      min-height: 44px; border-radius: 9px; font-weight: 750;
    }
    a[data-testid="stPageLink-NavLink"] {
      display: flex; align-items: center; justify-content: center;
      padding: .6rem .8rem; background: #155d70;
      border: 1px solid #2b8192; color: #fff !important;
      text-decoration: none;
    }
    a[data-testid="stPageLink-NavLink"] *,
    a[data-testid="stPageLink-NavLink"] { color: #fff !important; opacity: 1 !important; }
    a[data-testid="stPageLink-NavLink"]:hover { background: #1a7488; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero"><h1>🧅 蔥明錢 Lite</h1>'
    '<p>一百萬本金，同場對戰，四分鐘決勝負</p></div>',
    unsafe_allow_html=True,
)

battle_col, practice_col, team_col = st.columns([1.3, 1, 1], gap='medium')

with battle_col:
    with st.container(border=True):
        st.markdown('<div class="mode-icon">🏆</div>', unsafe_allow_html=True)
        st.subheader('對戰模式')
        st.markdown('<div class="mode-copy">建立房間、邀請朋友，或挑戰大盤定期定額。最多四位玩家，同一行情、各自操作。</div>', unsafe_allow_html=True)
        st.page_link('pages/3_多人競賽.py',label='進入對戰房間',icon='🏆',use_container_width=True)
with practice_col:
    with st.container(border=True):
        st.subheader('👤 單人練習')
        st.markdown('<div class="mode-copy">保留手動與動態回放、交易紀錄、六軸成績單與九型人格。</div>',unsafe_allow_html=True)
        st.page_link('pages/1_交易員.py',label='進入交易員模式',icon='👤',use_container_width=True)
with team_col:
    with st.container(border=True):
        st.subheader('🏦 交易團隊')
        st.markdown('<div class="mode-copy">團隊共用資金與協作仍在規劃中。</div>',unsafe_allow_html=True)
        st.page_link('pages/2_交易團隊.py',label='查看交易團隊',icon='🏦',use_container_width=True)
st.caption('對戰測試版：不計費稅與權息。網站重啟可能清除房間；尚未提供永久保存。')
