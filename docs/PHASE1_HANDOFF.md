# 第一階段紀錄 · 2026-10-11

基底：origin/main，ce5ffd4faa1c9d23d3eebe6a923e20ff9715b4aa。
本機分支：codex/phase1-trade-record。尚未推送或部署。

## 修改

- trading_engine.py：操作與平倉紀錄使用實際行情標的，保存進場理由。
- pages/1_交易員.py：移除重複下單記錄邏輯，統一呼叫引擎；顯示已平倉明細。
- tests/test_trade_record.py：驗證多空損益、標的、反向平倉與操作筆數。
- tests/check_streamlit.py：驗證首頁、交易員頁、Manual +1/+5、BUY、平倉與紀錄筆數。
- .gitignore：忽略本機依賴與 Python 快取。
- run_local.ps1：使用此電腦的 bundled Python 與專案 .runtime 啟動。

## 執行與驗收

在專案目錄執行 `./run_local.ps1`。其他 Python 環境則先安裝 requirements.txt，再執行 `python -m streamlit run app.py`。

`python -m unittest discover -s tests -v`：2 個測試通過，涵蓋多空、反向與空手平倉。
以 bundled Python 執行 `tests/check_streamlit.py`：全部斷言通過。
git diff --check 通過。Streamlit AppTest 不代表瀏覽器圖表視覺驗收或外部行情下載驗收。

## 尚待處理

- 加碼沒有更新平均成本，減碼尚未實現損益；SL/TP 尚未觸發。
- R 仍採損益百分比除以 3 的示範公式；交易數量單位與費用尚需定義。
- Dynamic Replay 目前沒有 Decision Window，最後一根會提前結束，模式切換與交易編輯暫停流程尚需修正。
- Chart Tools 未保存瀏覽器繪圖事件；Auto Trading 尚未實作。
- 紀錄僅在 Session，尚未持久化。
- 本次未驗收動態動畫、真實行情端點或線上部署。

下一階段先修 Replay 狀態與最後一根完成判斷，再加入與價格無關的 Decision Window。
