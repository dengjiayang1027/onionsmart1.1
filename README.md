# 蔥明錢 Lite

## Phase 1：首頁與模式入口

- `app.py` 顯示交易員、交易團隊、多人競賽三個入口。
- `pages/1_交易員.py` 保留既有 Replay、繪圖、交易操作、Trade Record 與 Trader Score 介面。
- `pages/2_交易團隊.py` 與 `pages/3_多人競賽.py` 是功能規劃頁，房間、多人同步及共用資金尚未實作。

## 執行

```powershell
python -m pip install streamlit pandas numpy plotly
streamlit run app.py
```

`app.py` 是 Streamlit 介面；`replay_engine.py` 負責日 K 合成路徑；`trading_engine.py` 統一記錄交易。

## 目前實作

- Manual Replay 保留逐根和每次五根前進。
- Dynamic Replay 設定可折疊收合；交易操作放在 K 線旁，交易統計放在左下方回放控制區，交易紀錄留在頁面下方。
- Dynamic Replay 每根日 K 固定 8 秒，分為四段各 2 秒：Open → 第一個極值 → 第二個極值 → Close。僅使用 OHLC 時這只是合成的盤中示意，不代表真實歷史順序。
- 開始動態播放後會連續播放，不再自動插入決策暫停。按 BUY、SELL、加碼、減碼或平倉時，行情先暫停；操作記錄完成後自動續播。
- 手動交易共用 Trade Record，包含日期、Replay 時點、股票、方向、價格、數量、SL/TP、損益、R、理由、持有日數及模式欄位；交易面板的每個操作另記錄在操作紀錄。自動交易模式尚未實作，紀錄模式欄位已預留。
- Plotly 圖表工具列提供趨勢線、矩形、圓形、自由畫筆、文字和刪除形狀。繪圖目前只在瀏覽器圖表互動期間存在；Undo/Redo、Lock、形狀跨 rerun/交易紀錄保存與還原尚待接入能回傳 Plotly relayout/edit 事件的元件。這是 Streamlit 原生 `plotly_chart` 事件支援的限制，尚未宣稱完成持久化。

下一階段可把圖表事件包成獨立 component，將畫圖與交易時點快照保存至 session/database，再加入 Auto Trading 規則引擎並沿用 `trading_engine.py` 的紀錄介面。
