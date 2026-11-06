# SIGNAL V0.5.1｜獨立事件基準與漏報驗收

**這是每日情報品質測試工具，不是 AI 每日重要新聞排名。**

## 版本作用

- `data/benchmark_candidates_v051.json`：以系統外部官方公告整理 **20 項參考事件候選**，包括日期、標題、發文者及原始來源連結。初始 `review_status=pending`，**全部尚未人工審核重要性**，不可視為黃金標準或全球新聞代表性樣本。
- `scripts/benchmark_v051.py`：同時讀取人工審核清單、來源原始歷史及 72 小時選讀候選，產生 `data/benchmark_audit_v051.json`；只顯示**提示性**的可能同事件候選，絕不自動視為命中。
- GitHub Actions 產生人工基準使用狀況與必要缺口；網站「證據檢核」下新增「重大事件對照與漏報診斷」，不開新選單。
- 不啟用付費 API，不複製新聞全文，不修改任何既有來源的授權閘門，不改寫個人記錄。

## 人工審核步驟（稍後進行，不影響本次部署）

審核員須**打開官方來源頁面**，逐筆判定事件的實際重要性及是否應納入樣本；本次候選清單仍偏重宏觀經濟，後續要補足政治、能源、社會、工程量產、台灣、巴西與非 AI 科學。確認後才在 `data/benchmark_candidates_v051.json` 該事件資料設為：

1. `review_status`: `approved`；`evidence_audited`: `true`；`reviewed_by`: 審核者代稱；`reviewed_at`: 帶時區 ISO-8601 日期時間；`impact_justification`: 至少 12 字的重要性理由。
2. 如果該官方連結只是索引／列表，須先換成**該事件專屬的原始頁面**，不可用列表網址冒充已核對原始發布。
3. 另外檢查 SIGNAL 原始 `data/live_items.json` 是否有相對應事件後：`match_status` 設為 `confirmed_present` 並填原始 `match_item_id`；或 `confirmed_absent` 且 `match_item_id` 留空；必須填 `match_reviewed_by`、`match_reviewed_at`、`match_note`（至少 12 字）。只憑標題或 URL 相似度的自動**建議**不能算已證實收錄。
4. 若該事件並不值得列為重要資訊，改設 `review_status=rejected`，`match_status=pending`；不要為了湊 20 筆勉強核准。

不可在 `match_status=confirmed_present` 時使用不存在或時間不符的 item ID。這項要求與資料授權、來源可信度不同。

## 統計口徑（嚴格限縮）

- **沒有通過人工驗收就不產出命中率**。最少 20 件經人工核准且人工完成資料核對的事件，涵蓋至少 5 個領域、3 個地域、任何單一領域不超過樣本 35%，且都在 45 天保存期內，才允許展示**這個人工樣本**的來源收錄比例。若不足則為 `null`。
- 72 小時的「今日選讀候選」採不同時間窗：只允許在 72 小時內且有人工核對的事件進入選讀樣本分母；至少 5 件才能顯示同一樣本的選讀比例，並和「同一來源池最新八則」的純時間排序進行對照。兩者均不是重要性評分。
- 無論如何，**全球重大新聞遺漏率、新聞主張真實性及 AI 重要性精準率都是未知，不產生數字**。
- 來源未覆蓋的領域，不應被 AI 虛構訊息補上。由人工測試集驗證的召回率，不代表開放世界的召回率。

## GitHub 升級

1. GitHub Desktop：`Fetch origin` → `Pull origin`，確認無衝突。
2. 將本 ZIP **裡面的內容**貼到既有 Repo 根目錄（已存在 `.github`、`scripts`、`data`、`index.html` 的地方）。**不要把外層資料夾多包一層**，不覆蓋 `data/live_items.json`。
3. Summary：`Add V0.5.1 human-gated external event benchmark` → `Commit to main` → `Push origin`。如遇遠端更新，先 Fetch/Pull 再 Push；有衝突停止、不要強制覆蓋。
4. GitHub `Actions` → `SIGNAL V0.5.1 independent reference benchmark + Pages` → `Run workflow` (main)。
5. 執行成功後，摘要應出現「V0.5.1｜重要事件參考庫與漏報驗收門檻」，初始外部候選 20、人工核准 0、全球遺漏率不可量。打開正式 GitHub Pages「證據檢核」頁。

## 測試及回滾

離線：`python scripts/test_v051.py`。全部回歸測試請依照 `.github/workflows/signal-live-v034.yml` 列出的逐支 Python 檔執行。本版本不需要任何 API Key 或存取授權外資料。

如部署失敗，先看 `collect-build → Check offline acceptance tests` 及 `Cross-check external reference candidates`；保留既有 Repo，還原本次 commit 即可。GitHub Actions 成功僅代表程式執行，**不代表已驗證任何重要新聞。**
