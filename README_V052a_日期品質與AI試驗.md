# 視界 SIGNAL V0.5.2a｜日期品質修復與 AI 試驗入口

## 本次修正
- `新發現` 只顯示近 7 天、發布日期可解析、且不超前超過 1 小時的來源標題。`first_seen_at` 是系統首次取得資料的時間，不是新聞發表日，禁止用來代替來源發布時間。
- `新發現` 下方新增「日期待核對清單」，可看來源缺日期或日期超前的公開元資料，**不得宣稱最新新聞**。
- 保留原本的 `live_items.json` 儲存資料；日期異常不再放入近期列表，但不擅自更改日期。
- 原本 2026-11-05 固定編輯樣本連同展示評分移入獨立的「編輯存檔」左側選單，今日情報只呈現最新候選及來源標題。
- GitHub Actions 的常態每天 2 次採集工作**強制不呼叫付費 AI**。另增加 V0.5.3 手動限定 3 次模型呼叫的試驗工作流，輸出供人工對照的 HTML／JSON，只上傳 7 天保留的 Actions Artifact，**不更新正式網站**。

## 安裝
1. GitHub Desktop 先 `Fetch origin`，必要時 `Pull origin`；若有衝突先檢查，再覆蓋更新檔。
2. 解壓本 ZIP，將內容複製至 repository **根目錄**（不是再建立一個資料夾），切勿覆蓋或刪除 `data/live_items.json`、`data/benchmark_candidates_v051.json`、`data/feed.json` 等資料檔。更新包只含程式與工作流程，沒有動到原始歷史紀錄。
3. Summary：`Fix SIGNAL publication date integrity and isolate editorial archive`。
4. `Commit to main` → `Push origin`。
5. GitHub → Actions → `SIGNAL V0.5.2a date-quality guard + Pages` → `Run workflow` → `main`。
6. 成功後先驗 `collect-build / deploy` 都綠燈，再打開 https://kalisanhomei-afk.github.io/signal-intelligence_V0.3.3/：`今日情報` 與 `編輯存檔` 分開、`新發現` 能顯示日期待核對資訊。

## V0.5.3 小型 AI 試驗：預設不執行
- 不要把 API Key 寫在對話、GitHub 程式或前端網站。
- 需要自備 OpenAI API 額度，ChatGPT 訂閱不等於 API 訂閱。在 GitHub Repository → Settings → Secrets and variables → Actions → Repository secrets 新增 `OPENAI_API_KEY`。
- 請先確認願意付費，再手動點 Actions → `SIGNAL V0.5.3 AI hypothesis pilot (manual only / no Pages)` → `Run workflow`，勾選 `run_paid_ai`。
- 成功後於該次 Actions Artifacts 下載 `signal-v053-review-hypotheses-not-verified`。包含 `pilot_review.html`（人工查核表）與 `review.json`（有跡可循的條件式草稿），最多 3 筆 AI 分析；不自動正式發布、也不標示查證成功。
- Repository 是 Public，**不要在此試驗輸入私人持倉、客戶資料或秘密**；不應假定 Actions Artifacts 永久私密。
- 若無 API Key，不需要啟動 AI；正常自動資料蒐集不會受影響。

## 品質驗收
- 離線測試：14 個既有測試入口加新增 `scripts/test_v052a.py`；Javascript 語法檢查。
- 正式環境需手動驗：日期未知是否從最新列表移出；過去編輯分數是否從首頁移除；更新排程是否持續成功；AI 試驗工作流是否必須人工勾選才能觸發。
- 本次不宣稱已完成獨立事實查證、全球新聞覆蓋、重要性準確率或自動投資建議。
