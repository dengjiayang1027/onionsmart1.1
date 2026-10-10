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
    "交易室會統一標的、日期區間、起始本金與賽事規則；每位玩家使用自己的交易介面，不同步交易進度或操作。完成後在房間等待其他玩家，全部完成再公布成績。"
)
st.markdown("""
### 第一版規則
- 可用遊戲 ID 以 Guest 身分加入，不需先註冊。
- 標的可由房主指定，或選擇公開／盲選隨機標的。
- 所有人使用相同起始本金與受限制的日期區間；交易次數不限。
- 系統依共同規則統整賽後成績與排行榜。

房間建立、邀請連結／QR Code、多人資料保存與賽後計分仍在規劃中。
""")
st.markdown("[🏠 回到首頁](../)")
