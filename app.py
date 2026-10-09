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
    '<p>從個人練習到團隊協作，打造你的交易決策力</p></div>',
    unsafe_allow_html=True,
)

left, middle, right = st.columns(3, gap="medium")

with left:
    with st.container(border=True):
        st.markdown('<div class="mode-icon">👤</div>', unsafe_allow_html=True)
        st.subheader("交易員")
        st.markdown(
            '<div class="mode-copy">進入原有交易訓練介面，使用手動或動態 K 線回放，'
            '練習進出場、風險管理與復盤。</div>',
            unsafe_allow_html=True,
        )
        st.page_link("pages/1_交易員.py", label="進入交易員模式", icon="👤", use_container_width=True)

with middle:
    with st.container(border=True):
        st.markdown('<div class="mode-icon">🏦</div>', unsafe_allow_html=True)
        st.subheader("交易團隊")
        st.markdown(
            '<div class="mode-copy">與夥伴共同管理虛擬資金，'
            '追蹤經理人績效、團隊持倉與風險。</div>',
            unsafe_allow_html=True,
        )
        st.page_link("pages/2_交易團隊.py", label="查看交易團隊", icon="🏦", use_container_width=True)

with right:
    with st.container(border=True):
        st.markdown('<div class="mode-icon">🏆</div>', unsafe_allow_html=True)
        st.subheader("多人競賽")
        st.markdown(
            '<div class="mode-copy">和其他玩家在相同行情與起始條件下比賽，'
            '用交易表現爭取排行榜名次。</div>',
            unsafe_allow_html=True,
        )
        st.page_link("pages/3_多人競賽.py", label="查看多人競賽", icon="🏆", use_container_width=True)

st.caption("訪客可直接開始交易練習。團隊協作、多人同步與帳號保存將於後續階段推出。")
