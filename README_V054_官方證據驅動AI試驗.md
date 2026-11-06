# 視界 SIGNAL V0.5.4｜官方證據驅動 AI 人工試驗

**本次更新是「獨立手動試驗」，不是網站改版，不會改動主站、Github Pages 或資料庫。**

## 為什麼要做這版？

V0.5.3 已成功呼叫 3 次 `gpt-4.1-mini`，產生 3 份中文草稿，但模型主要只看標題。它提出的「如果重要，則可能造成影響」沒有足夠的決策價值。

V0.5.4 的目的是先為三家不同發布機構取得有限、可連回原始出處的證據摘錄，然後讓 AI 對 **相同主題** 再做一次分析，核查是否比標題式推論具體。

### 這次讀取什麼

1. **BEA**（美國經濟分析局）：限定 `https://www.bea.gov/news/20xx/...` 的官方 HTML 頁面。
2. **EIA**（美國能源資訊署）：限定 `https://www.eia.gov/todayinenergy/detail.php?id=...` 的官方 HTML 頁面。
3. **arXiv**：只讀取官方 API 作者投稿摘要，**不是論文全文**、學術同儕審查或獨立重現。

**固定與 V0.5.3 相同的三篇文章作為比較樣本，禁止自動換成近期其他文章。** 這三篇必須仍存在現有7天優先閱讀候選中；若期限已過，流程會停止，應另外進行可追溯的樣本保存作業，而不是偷偷替換對照組。只從現有、允許來源白名單的「優先閱讀候選」核對；不爬取 Reuters、AP、BBC、FT 等未核准來源；不下載 PDF 或付費內容。

**原則**：官方頁面摘錄支持「這個機構有這樣的陳述」，並不代表陳述已經由第三方證實。AI 提出的任何語義解讀仍須人工核對。

## 一、更新至 GitHub（先同步後覆蓋）

1. GitHub Desktop 選擇正確的 `signal-intelligence_V0.3.3` Repository，點選 **Fetch origin**，如出現 **Pull origin** 則先同步。
2. 解壓縮本次覆蓋包。將壓縮包**內部**的 `.github`、`scripts` 與 `README_V054_官方證據驅動AI試驗.md` 複製至現有 Repository 根目錄（不是再建立一層子資料夾）。
3. GitHub Desktop Summary 輸入：`Add SIGNAL V0.5.4 evidence-bound manual AI pilot`
4. 點選 **Commit to main → Push origin**。如遇 merge conflict，不要強制覆蓋資料。

此包未附 `data/`、`index.html`、`index.template.html`，不會改動現有歷史新聞或正式網站。

## 二、先進行免費的證據抽取試跑（建議）

在 Repository 的 GitHub Actions 頁面選擇：

**`SIGNAL V0.5.4 official evidence + optional AI pilot (manual only)`**

→ **Run workflow** → Branch=`main` → `run_paid_ai` **不勾選** → **Run workflow**。

這次會測試官方頁面是否能讀取，**不會呼叫 OpenAI API**。

執行後在 Summary 看到：

- `Source excerpt retrieval: x/3`：成功取得幾篇可供人工查核的官方摘錄；若固定對照樣本不足3則也會停止。
- 各來源 `excerpts_available`、`unavailable` 及錯誤類型。
- `AI calls: 0`。若全部資料來源失敗，本次工作流程會顯示紅燈，這是刻意的防護措施。

## 三、讀取至少一個官方摘錄後，才做付費 AI 小樣本試驗

原本 GitHub 的 Repository secret **`OPENAI_API_KEY` 可以繼續沿用**，不必再建立新的金鑰。若沒有設定或已過期，才需要更新 Secret。

再次執行同一個 workflow，將 `run_paid_ai` **勾選 true**，單次最多 3 次 API 呼叫，模型為 `gpt-4.1-mini`。**單次呼叫數量限制並不等於固定金額預算上限**；重跑可能再次計費。建議在 OpenAI Project 用量頁設定預算提醒。

AI 無法取得原文的項目不會生成文章內容；AI 輸出不會寫入公開網站，也不會 Commit 至 `main`。

## 四、下載 AI 分析成果

工作流程頁面向下捲動，在 **Artifacts** 區塊下載：

**`signal-v054-source-excerpts-ai-manual-review`**

ZIP 內預期包含：

- `evidence.json`：哪個原始來源可讀、摘錄內容、來源連結、SHA-256 指紋與缺失資訊。
- `analysis.json`：AI 草稿、資料引用 ID、影響假說、查證缺口、失敗原因及 API 用量。
- `pilot_review_v054.html`：黑金／米白／鎏金風格的列印式人工查核頁。可用 Chrome 開啟，不必架網站。

Artifacts 留存 7 天。**重要：你的 GitHub Repository 目前是 Public。Artifacts 不等同私人保險箱，具有該 Repository 讀取權限的人可能取得檔案。**本版只擷取原則上可合法使用的少量官方資料，不放個人資訊、密鑰、付費新聞內容。若之後要分析非公開投資資料或內部情報，必須把付費 AI 試驗移往獨立 Private Repository。這三份報告不要直接貼入網站的公開 `data/` 資料夾。

## 五、驗收標準（請勿用 GitHub 綠勾取代內容驗收）

| 指標 | 最低要求 | 不代表什麼 |
|---|---|---|
| 官方摘錄 | 至少 1 家來源讀取成功，最好 3 家 | 不代表是完整文章或數據已核實 |
| 引用追溯 | AI 的 `key_facts` 每一項都有有效 `E1`、`E2` 等來源ID | 引用對應正確不代表解讀正確 |
| 未知事項 | 每則 AI 草稿有不確定性與下一步查核 | 不代表第三方獨立查證 |
| AI 呼叫 | ≤ 3 次、失敗需明確顯示 | 不表示費用永遠不超支 |
| 風險界線 | 已驗證主張持續為 0、絕不更新公開網站 | 不代表可以直接做交易決策 |

### 這次要人工評估的問題

- BEA：是否真正找到貿易差額與期間、是否有修正口徑？AI 是否有正確理解數據的增減方向？
- EIA：是否找到產品產出率與時間區間？AI 有沒有把歷史變化誤寫成必然的價格走勢？
- arXiv：是否找到方法、基準與測試範圍？AI 是否混淆作者報告與獨立驗證？

如果來源阻擋、標題不匹配或程式只取得雜訊，保留 `unavailable`、改進來源擷取，不應由 AI 補造數據。

## 六、已做與未做的測試

- 已通過：V0.5.4 自包含離線測試（官方網址白名單、重新導向限制、抽取、來源指紋、防篡改、無原文不產 AI、模型輸出結構與引用ID檢查、HTML 產生等）。
- 已通過：現有 V0.3.2–V0.5.2a 的離線回歸測試入口。
- **尚未測試**：GitHub 端對 BEA／EIA／arXiv 的實際連線與 HTML 擷取相容性；尚未進行 V0.5.4 付費 API 呼叫；尚未人工評分。
- OpenAI 的結構化輸出能限制欄位與格式，但無法保證每個中文句子有正確的證據支持，仍需人工查核。

## 七、預設為手動，不影響常態更新

排程 RSS 採集與 GitHub Pages 部署仍使用既有 `signal-live-v034.yml`。本次只新增一個 `signal-v054-evidence-pilot.yml`，預設 `run_paid_ai=false`，沒有 schedule，也沒有 deploy 階段。舊版 V0.5.3 workflow 不用再執行。
