# 蔥明錢 Lite

## 執行

```powershell
python -m pip install streamlit pandas numpy plotly
streamlit run app.py
```

`app.py` 是 Streamlit 介面；`replay_engine.py` 負責日 K 合成路徑；`trading_engine.py` 統一記錄交易。

## 目前實作

- Manual Replay 保留逐根和每次五根前進。
- Dynamic Replay 每日以 Open、兩個極值、Close 的規則路徑形成 K 棒。僅使用 OHLC 時這只是合成的盤中示意，不代表真實歷史順序。
- 動態模式可設定行情秒數、決策暫停次數及倒數時間。決策點根據日內時間進度產生，倒數後自動恢復；按交易操作時先停住，再於操作後恢復。
- 手動交易共用 Trade Record，包含日期、Replay 時點、股票、方向、價格、數量、SL/TP、損益、R、理由、持有日數及模式欄位。自動交易模式尚未實作，紀錄模式欄位已預留。
- Plotly 圖表工具列提供趨勢線、矩形、圓形、自由畫筆、文字和刪除形狀。繪圖目前只在瀏覽器圖表互動期間存在；Undo/Redo、Lock、形狀跨 rerun/交易紀錄保存與還原尚待接入能回傳 Plotly relayout/edit 事件的元件。這是 Streamlit 原生 `plotly_chart` 事件支援的限制，尚未宣稱完成持久化。

下一階段可把圖表事件包成獨立 component，將畫圖與交易時點快照保存至 session/database，再加入 Auto Trading 規則引擎並沿用 `trading_engine.py` 的紀錄介面。
