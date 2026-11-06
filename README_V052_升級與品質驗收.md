# SIGNAL V0.5.2｜情報重要性「人工審閱次序」與可選 AI 審閱草稿

版本日期：2026-11-06。基於已部署的 V0.5.1。這份更新包僅含程式，不含既有蒐集資料。

## 結論先說

- 系統會從 **7 日內**、已獲准介接的標題元資料中選出 **至多 8 則人工優先閱讀候選**，避免單一發布機構超過 2 則、單一分類超過 3 則。
- 「政策／經濟數據公告」、「產業／技術標題」、「活動資訊」的辨識是**透明的標題規則**，不是新聞真實性或全球重要性分數。
- AI **預設關閉**。設定 API 金鑰且明確啟用後，才會對最多 6 則尚未分析過的候選產生**有條件、未查證**的中文審閱草稿。原標題、來源、日期與連結完整保留；官方作者摘要僅限與 arXiv 記錄吻合的 M0A 元資料。
- 不能宣稱獨立驗證、全文研讀、同儕審查、商業化已確認、股價影響或投資勝率。沒有建立人工黃金基準時，不輸出重要性準確率。

## Windows / GitHub Desktop 安裝（沿用原 Repo）

1. 先在 GitHub Desktop 選擇正確 Repository：`signal-intelligence_V0.3.3`。點 **Fetch origin**；如果有 **Pull origin**，先 Pull。若出現 conflicts，先停止，不要強制覆蓋。
2. 下載本回覆附的 **V0.5.2 覆蓋更新包**，解壓縮。**只複製解壓後的內容**（`scripts/`、`.github/`、`index.html`、`index.template.html`、`README_V052_升級與品質驗收.md` 等）到 Repository **根目錄**。
3. 遇同名檔案取代；不要移動 `.git`、不要刪除 `data`、不要把整個新資料夾放進 Repo 產生多一層。
4. GitHub Desktop Summary：`Add SIGNAL V0.5.2 provisional editorial attention engine`。按 **Commit to main** → **Push origin**。
5. GitHub 網站：Actions → **SIGNAL V0.5.2 editorial attention + optional AI review + Pages** → Run workflow → main → Run workflow。
6. GitHub 工作摘要下半部應有 **SIGNAL V0.5.2｜暫定人工關注順序與 AI 審閱草稿**；`collect-build`、`deploy` 均需綠燈。
7. 用 **GitHub Pages** 而非 `file:///` 本機開啟「今日情報」；上半部應新增 **人工優先檢視**。若看不到，Ctrl+F5 強制刷新。

本更新包**不包含** `data/live_items.json`、`data/benchmark_candidates_v051.json` 等任何歷史資料，程式會在 Actions 中重新產生 `data/impact_review_v052.json`。

## 首次無 API 金鑰驗收

| 檢查 | 預期 |
| --- | --- |
| GitHub Jobs | `collect-build` ✅ + `deploy` ✅ |
| GitHub 報告 `AI 啟用` | **否** |
| AI 草稿數 / 模型呼叫 | **0 / 0** |
| 候選 | 最多 8，視實際 7 日來源資料而定；可能為 0 |
| 使用者可點擊原始出處 | 是 |
| 舊「每日選讀候選」與新清單 | 同時保留，可人工比較 |
| 「重大事件漏報率／可信度分數／投資預測」 | 不應出現任何聲稱已驗收的數值 |

⚠️ **GitHub Actions 成功只代表技術步驟通過**，不能證明 AI 做了深度查證。使用者仍需對候選進行實際人工審核。

## 之後啟用 AI：必須明確選擇，且 API 另外付費

建議先通過「無付費 API」的部署驗收，再設 API：

1. 在 [OpenAI API Platform](https://platform.openai.com/) 另行開通 API 帳單與額度。ChatGPT 付費方案不能代替 API 費用。
2. GitHub → 該 Repository → Settings → **Secrets and variables → Actions** → **Secrets** → New repository secret。
3. 名稱填 `OPENAI_API_KEY`；內容貼上 API key（**不要貼進聊天、程式碼、Git commit**）。
4. 同頁 **Variables** → New repository variable，名稱 `SIGNAL_V052_AI_ENABLED`，值 `true`。
5. 選擇性新增變數 `SIGNAL_V052_MODEL`，預設 `gpt-4.1-mini`。先不要更動。
6. 手動 Run workflow，檢查 `api_calls_attempted` 是否介於 0–6、`ai_drafts` 是否按實際成功顯示、失敗是否退回「規則初選」。
7. API 付費的硬上限要在 API 平台設定預算／使用限制。**每次至多 6 個新請求是程式級節流，不保證固定金額成本，也不保證模型回覆正確。** 定時排程每天執行 2 次。

## 與先前 5 件事件人工預審的連結

初期人工比較先看兩個現象：

- **美國貿易數據 vs NASA 活動標題**：同一時間窗下，具有經濟統計意涵的資料應該比一般教育交流活動更值得優先讀原文。V0.5.2 用明確可查的「標題型態」規則建立可比較的候選，不宣稱已證實重要性。
- **BOJ／IMF／歐洲理事會漏收事件**：若不在已准入來源，V0.5.2 也**無法自行發現**。AI 不能用幻想補齊缺口，來源補強與人工黃金基準建立仍是獨立待辦工作。

這 5 件預審不是已批准「黃金標籤」。 V0.5.1 正式人工核准門檻仍須遵守。

## 本版新增／修改檔案

- `scripts/impact_review_v052.py`：候選選取、來源／摘要驗證、AI Schema、快取、呼叫上限、失敗回退。
- `scripts/test_v052.py`：離線惡意／失敗情境測試。
- `scripts/v052_summary.py`：透明 GitHub 工作摘要。
- `scripts/build_public_site.py`：加入生產部署前資料合法性驗證，失敗則禁止發布。
- `.github/workflows/signal-live-v034.yml`：延續原路徑，**只更新工作流程名稱與功能**，避免重複產生新的排程。
- `index.template.html`、`index.html`：今日情報新增審閱區塊；不改版面配色與原編輯存檔。
- `docs/V0.5.2_品質邊界與驗收準則.md`：品質限制與人工驗收方法。

## 離線驗收紀錄

- 所有自動化腳本 `test_pipeline` 至 `test_v052` 共 **14 支測試入口**，在開發環境執行通過（歷史腳本包含預期的模擬失敗 log）。
- Node.js JavaScript 語法檢查通過。
- 用「無來源資料」的本機情境測試嚴格公開站點組裝通過；**未在這裡執行付費 OpenAI API 呼叫，也無法因此證明真實資料下的重要性表現**。
- 最終生產環境需由 GitHub Actions 新版執行與人工審閱結果驗收。

## V0.5.2 不等於 V1.0

正式情報發布仍缺少：跨媒體獨立驗證、完整的新聞來源覆蓋、人工確認的重大事件命中率、政策/產業因果與財務數據查核、AI 回覆的人工品質評估。這些未完成前，**不得把本頁當成交易建議**。
