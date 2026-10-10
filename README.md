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
- Dynamic Replay 使用同一顆「開始／暫停」切換鍵。
- Dynamic Replay 設定可折疊收合；交易操作放在 K 線旁，交易統計放在左下方回放控制區，交易紀錄留在頁面下方。
- Dynamic Replay 每根日 K 固定 8 秒，分為四段各 2 秒：Open → 第一個極值 → 第二個極值 → Close。僅使用 OHLC 時這只是合成的盤中示意，不代表真實歷史順序。
- 開始動態播放後會連續播放，不再自動插入決策暫停。按 BUY、SELL、加碼、減碼或平倉時，行情先暫停；操作記錄完成後自動續播。
- 手動交易共用 Trade Record，包含日期、Replay 時點、股票、方向、價格、數量、SL/TP、損益、R、理由、持有日數及模式欄位；交易面板的每個操作另記錄在操作紀錄。自動交易模式尚未實作，紀錄模式欄位已預留。
- Plotly 圖表工具列提供趨勢線、矩形、圓形、自由畫筆、文字和刪除形狀。繪圖目前只在瀏覽器圖表互動期間存在；Undo/Redo、Lock、形狀跨 rerun/交易紀錄保存與還原尚待接入能回傳 Plotly relayout/edit 事件的元件。這是 Streamlit 原生 `plotly_chart` 事件支援的限制，尚未宣稱完成持久化。
- 單人回放抵達所選行情區間末端時，會自動平掉未結部位並產生個人成績單：六軸能力雷達圖（守、效、買、賣、盈、穩）、1–5 分說明，以及依前兩高能力顯示的九種職業角色圖。樣本不足的軸以 3/5 中間分呈現並註明；總損益獨立顯示，不納入六軸。角色與版面參考圖保存在 `assets/occupations/reference-art/`。

下一階段可把圖表事件包成獨立 component，將畫圖與交易時點快照保存至 session/database，再加入 Auto Trading 規則引擎並沿用 `trading_engine.py` 的紀錄介面。

## Phase 2（台灣上市／上櫃日線）

- 交易員模式可使用證交所上市標的清單搜尋，載入所選區間的台股日線 OHLCV，並沿用既有手動／動態 Replay、下單及交易記錄。
- 行情選擇器可切換上市／上櫃；上櫃標的清單來自櫃買中心每日行情，歷史日線依標的與月份查詢，正規化成共用 OHLCV 欄位。
- 若清單漏列標的，可直接輸入上市或上櫃代碼查詢歷史日線。
- 行情下載使用交易所歷史月查詢；標的清單及各月行情由 Streamlit 快取，避免重複請求。
- 首次進頁仍使用明確標示的示範行情；外部行情載入失敗時不會把示範資料誤稱為歷史行情。
- 證交所的政府開放資料集頁列示政府資料開放授權條款第 1 版，但該資料集提供每日資料。歷史端點是證交所查詢服務；正式公開或商用前仍需確認該端點的具體授權與使用條件。行情僅供模擬訓練，請以證交所公告為準。

官方來源：

- [臺灣證券交易所歷史個股日成交資訊](https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY)
- [上市個股日成交資訊開放資料集](https://data.gov.tw/dataset/11549)
- [櫃買中心個股日成交資訊](https://www.tpex.org.tw/ch/stock/aftertrading/daily_trading_info/st43.php)
- [上櫃股票收盤行情開放資料集](https://data.gov.tw/dataset/11371)
- [政府資料開放授權條款](https://data.gov.tw/license)

上櫃資料來源的每日開放資料集列有政府資料開放授權條款第 1 版；歷史個股頁自民國 83 年起提供資料。正式商用或大量抓取前仍應確認櫃買中心相關使用條件。行情僅供模擬訓練。

## 多人競賽模式（產品與架構草案）

- [多人競賽架構草案](docs/BATTLE_MODE_ARCHITECTURE.md) 定義 QR／邀請連結入房、Guest ID、隨機與盲選標的、玩家各自交易且賽後統整、玩家獨立帳本、賽後評分和分階段導入 Supabase 的方向。
- 競賽目前仍為規劃頁，尚未實作房間服務、同步或排行榜。
