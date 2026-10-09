import streamlit as st

st.set_page_config(page_title="交易團隊｜蔥明錢 Lite", page_icon="🏦", layout="wide")
st.markdown("""
<style>
.stApp { background: #08111a; color: #eef5f9; }
.block-container { max-width: 1050px; padding-top: 3rem; }
[data-testid="stAlert"] { background: #10202c; }
</style>
""", unsafe_allow_html=True)
st.title("🏦 交易團隊")
st.info("交易團隊模式正在規劃中。")
st.markdown(
    "第一版將支援建立或加入房間、以暱稱加入、分配虛擬資金，並查看團隊持倉與績效。多人共用資金和即時同步會在後續階段實作。"
)
st.markdown("[🏠 回到首頁](../)")
