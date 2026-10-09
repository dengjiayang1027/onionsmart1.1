import streamlit as st

st.set_page_config(page_title="多人競賽｜蔥明錢 Lite", page_icon="🏆", layout="wide")
st.markdown("""
<style>
.stApp { background: #08111a; color: #eef5f9; }
.block-container { max-width: 1050px; padding-top: 3rem; }
[data-testid="stAlert"] { background: #10202c; }
</style>
""", unsafe_allow_html=True)
st.title("🏆 多人競賽")
st.info("多人競賽模式正在規劃中。")
st.markdown(
    "第一版將支援建立私人賽事房間、訪客參賽、同步歷史行情與回放，並在競賽結束後比較報酬率、最大回撤、勝率和 Trader Score。"
)
st.markdown("[🏠 回到首頁](../)")
