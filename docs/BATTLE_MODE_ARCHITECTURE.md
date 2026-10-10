# 蔥明錢多人競賽模式｜架構草案

## 第一版目標

玩家以房間代碼和暱稱加入私人賽事，不必先註冊。每場比賽使用相同標的、歷史區間、起始 K 棒、初始資金、槓桿與交易規則；每位玩家獨立交易。房主開始後，所有玩家共用同一個 Replay 時點，結束後依相同資料計算排行榜。

## 建議技術切分

- **Streamlit**：房間建立／加入、等待室、Replay 畫面、交易操作與賽後排行榜。
- **共用 Replay Engine**：沿用交易員模式的 OHLCV 資料和 K 棒索引；競賽模式只新增房間時鐘和賽事設定，不複製 K 線與交易邏輯。
- **Supabase PostgreSQL**：保存房間、參賽者、賽事設定、交易指令及最後狀態；使用資料庫交易／RPC 保證下單檢查與資金更新一次完成。
- **Supabase Realtime**：推送房間狀態、開始／暫停／結束和索引變化。Streamlit 第一版可以 1–2 秒輪詢作為簡化同步；競賽同步確認後再升級為自訂元件或前端即時連線。

## 房間流程

1. 房主建立房間，伺服器產生不可預測的房間代碼。
2. 玩家輸入代碼和暱稱，取得短期 Guest Token；暱稱在該房間內必須唯一。
3. 等待室顯示參賽者、賽事設定和準備狀態；只有房主可修改設定及開始。
4. 開始時將標的、資料版本、起訖日期、起始索引、起始資金和規則鎖定在賽事快照。
5. 伺服器保存唯一的 `current_bar_index` 和 `revision`。玩家下單時帶上看到的 revision；逾期命令退回並要求刷新。
6. 房主可暫停或提前結束；伺服器保存結束快照並計算最終排行榜。

## 同步和公平性

- 伺服器是賽事時鐘的唯一權威。玩家端不自行推進 K 棒，只呈現伺服器公布的索引。
- 每根 K 棒開始前，只公開該時點以前可見的 OHLC 歷史；當根 OHLC 依現有 Dynamic Replay 規則逐步揭露。不得把未揭露的未來資料送進前端。
- 相同房間中所有玩家的 K 棒索引一致，但倉位、現金、SL/TP 和交易紀錄彼此隔離。
- 每筆命令帶唯一 `idempotency_key`，避免網路重試造成重複成交。
- 伺服器檢查房間狀態、參賽者身分、可用資金、數量、價格時點和重複命令，再以單一資料庫交易寫入訂單與部位。
- Blind Challenge 的標的、日期和區間由伺服器以隨機種子抽出並保存；開始前不得回傳代碼、名稱和實際日期。賽後才揭露題目。

## 資料表草案

- `battle_rooms`: `id`, `join_code_hash`, `host_participant_id`, `status`, `created_at`, `expires_at`。
- `battle_matches`: `id`, `room_id`, `mode`, `market`, `symbol`, `data_start`, `data_end`, `data_fingerprint`, `initial_cash`, `rules_json`, `current_bar_index`, `revision`, `started_at`, `ended_at`。
- `battle_participants`: `id`, `match_id`, `guest_token_hash`, `nickname`, `status`, `joined_at`。
- `battle_orders`: `id`, `match_id`, `participant_id`, `idempotency_key`, `bar_index`, `action`, `side`, `quantity`, `price`, `created_at`。
- `battle_snapshots`: `match_id`, `participant_id`, `bar_index`, `cash`, `equity`, `position_json`, `drawdown`, `updated_at`。

訪客 Token 和房間代碼只保存雜湊；房間設過期時間並限制加入次數。第一版可讓 guest 戰績只保存在房間期限內，註冊帳號永久保存列為後續功能。

## 排行榜與規則

第一版固定採用相同初始資金與不加槓桿；排名先依總報酬率，再以較低最大回撤、較高 Trader Score 作為同分排序。另顯示報酬率、最大回撤、勝率、交易次數和 Trader Score。賽事開始後不得更改規則；手續費與滑價要嘛全員同一設定，要嘛第一版先統一不計並明確標示。

## 實作階段

1. **規則與單人模擬驗證**：定義訂單、部位、報酬與回撤公式；同一行情快照重播可得到相同結果。
2. **房間 MVP**：Supabase schema/RPC、Guest Token、建立／加入／等待室／房主開始與結束。
3. **同步 Replay**：共享索引、暫停續播、revision 衝突和斷線重連；先限制每房人數與房間期限。
4. **交易與排行榜**：獨立資金帳本、原子下單、事件紀錄和賽後報告。
5. **Blind Challenge**：伺服器端抽題、隱藏題目中繼資料，完賽後揭露。

Streamlit 多使用者 session 不適合單獨承擔共享即時狀態，因此不能只把房間狀態放在 `st.session_state`。若之後需要更低延遲及更穩定的同步，再把競賽畫面換成 React/Next.js + FastAPI/WebSocket；交易員模式仍可先保留 Streamlit。
