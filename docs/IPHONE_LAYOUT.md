# iPhone 網頁版 · 2026-10-11

沿用 Streamlit 網站，目標瀏覽器為 iPhone Safari 與 Chrome。

依使用者草圖排序：選股與期間 → K 線 → 回放／交易操作 → 交易統計 → 已平倉交易 → 操作紀錄。
390px 手機寬度並排回放與交易面板；380px 以下改為垂直排列，避免欄位太窄。
圖表高 360px，手機工具列在圖內下方；觸控按鈕至少 44px，輸入文字 16px。
保留 Manual／Dynamic Replay、桌面快捷鍵、9 型人格與六軸成績單。

修改檔案：pages/1_交易員.py、mobile_layout.py、tests/check_streamlit.py。
Streamlit AppTest 的回放、模式切換、買入確認、平倉與做空流程通過。
已檢查線上 390px 排版，實體 iPhone Safari／Chrome 尚未實機驗收。

執行：run_local.ps1，或安裝 requirements.txt 後 python -m streamlit run app.py。
驗收：手機開啟網站，展開選股設定、前進 K 棒、選買入或賣出並送出，下滑確認統計與兩種紀錄；完成區間後檢查成績單。

繪圖保存、SL/TP 自動觸發、完整加減碼帳務、永久保存仍是既有待辦，本次未新增。
