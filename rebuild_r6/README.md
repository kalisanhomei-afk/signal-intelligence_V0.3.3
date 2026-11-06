# 視界 SIGNAL｜Evidence Rebuild R6：真實模型「一則 BEA」技術驗收

**這次只開發 R6，不改 R1～R5，也不合併 `main`。** 這套 GitHub Actions 採用 `push` 觸發，因為新 `workflow_dispatch` 若只放在非預設分支，GitHub 不保證能從 Actions 頁面手動執行。此版本透過「兩次不同提交」避免影響 `main`，也不需要使用者在本機處理 API Key。

## 重要區別：第一步絕對不付費

| 階段 | 觸發條件 | API 次數 | 預期結果 |
|---|---|---|---|
| 第一階段離線 | 將 `rebuild_r6/` 及 `.github/workflows/signal-evidence-r6-branch.yml` 上傳到 `signal-evidence-rebuild` | **0** | `offline_qa` ✅；`one_paid_call` 灰色 Skipped |
| 第二階段真實 API | `APPROVE_ONE_CALL.txt` 從 NO 改 YES，且 Summary 必須精確等於 `SIGNAL_R6_APPROVE_ONE_PAID_CALL` | **最多一次 POST /v1/responses，不重試** | `offline_qa` ✅，`one_paid_call` ✅或提供可診斷錯誤 |

這裡**沒有自動發佈正式網站**的步驟，所有 GitHub Token 權限只有 `contents: read`。

## 你現在要做的第一步：只上傳，跑離線驗收

1. GitHub Desktop 上方 **Current branch** 必須是 `signal-evidence-rebuild`，不能是 `main`。
2. 解壓縮 R6 ZIP，將其中 **`rebuild_r6`** 資料夾複製到原始 Repository 根目錄；另將 `.github/workflows/signal-evidence-r6-branch.yml` 複製到 Repository 原本的 **`.github/workflows/`** 資料夾；**合併資料夾，不是刪除原資料夾或整份覆蓋**。Windows 如看不到 `.github`，在檔案總管勾選「檢視 → 顯示 → 隱藏的項目」。
3. 請不要修改 `rebuild_r6/APPROVE_ONE_CALL.txt`，應顯示 **`APPROVE_ONE_CALL=NO`**。
4. GitHub Desktop 左下角 Summary 輸入 `Add SIGNAL R6 branch-only offline and gated model smoke test`。
5. 點 **Commit to signal-evidence-rebuild** → **Push origin**。不要 Create Pull Request。
6. GitHub 網頁 → Repository → **Actions** → 從左側 All workflows 或最新執行紀錄找到 **SIGNAL R6 isolated branch QA + optional one paid call**。它是因 **Push** 自動執行，這裡不需要找 Run workflow 按鈕。
7. 第一階段應顯示 `offline_qa` Success，`one_paid_call` Skipped。下載 `signal-r6-offline-qa`，檢視 `r6_result.json` 應有 `status = OFFLINE_MOCK_ONLY` 與 `api_calls_attempted = 0`。
8. **如果離線失敗，就停在此步，不能進行付費測試。**

## 第二步：離線通過後，才授權一次付費測試

1. 使用檔案總管找到 Repository 裡的 `rebuild_r6/APPROVE_ONE_CALL.txt`。
2. 用記事本，將原本唯一一行：

   `APPROVE_ONE_CALL=NO`

   改成：

   `APPROVE_ONE_CALL=YES`

   儲存。**只能改這個檔案，不要把任何 API Key 寫進去。**
3. GitHub Desktop 的 Summary **必須完全相同，不能有空格或其他字**：

   `SIGNAL_R6_APPROVE_ONE_PAID_CALL`

   不需要 Description。按 **Commit to signal-evidence-rebuild → Push origin**。
4. GitHub Actions 會因 Push 自動執行；先重新通過 R5+R6 離線測試，才會進入 `one_paid_call`。它只向 OpenAI 發出最多 **1 次** `Responses API` 請求；沒有重試。金鑰從現有 GitHub Secret `OPENAI_API_KEY` 讀取。
5. 執行後從該次 Actions → **Artifacts** 下載 `signal-r6-one-bea-live-manual-review`，其中：

   - `r6_result.json`：是否有成功選取 BEA 事實編號／錯誤分類、API 次數；
   - `r6_review.html`：開啟 Chrome 閱讀，不是已查證新聞；
   - `_preflight`：R5 離線檢查資料（如存在）。

6. 將下載的 ZIP 上傳回對話供 R7 人工品質驗收。請**不要 Re-run 該次付費 workflow**，也不要對已核准的相同提交重新執行付費 Job，避免重複計費。
7. 完成後，再把 `APPROVE_ONE_CALL.txt` 改回 `APPROVE_ONE_CALL=NO`，Commit 摘要使用 `Disable R6 one-call approval` 然後 Push。這次只會執行離線檢查。

### 一定要注意的工作流程限制

- **這不是 `workflow_dispatch`。** GitHub 官方規定，手動的 `workflow_dispatch` 工作流程定義通常須存在於預設分支；我們因為要讓 `main` 完全不動，使用開發分支 `push` 事件配合**嚴格的人工授權檔案＋提交摘要＋原帳號身份＋變更清單**雙重保護。
- 如果 Actions 顯示 `one_paid_call` Skipped，先確認摘要**完全一樣**、修改的是 `APPROVE_ONE_CALL.txt`、且使用 `kalisanhomei-afk` 帳號推送。不要把 `APPROVE_ONE_CALL=YES` 留在分支後繼續用相同摘要亂試。
- GitHub Actions **Success 不代表情報品質合格**，只表示受控的 API→模型輸出契約→程式帶入數字能完成。R7 才會人工核對原文、模型選擇價值與因果推論。
- 若輸出 `api_http_401` 是 API 認證問題，`api_http_403` 是權限，`api_http_429` 是額度／速率，`model_selection_rejected_by_r4` 是模型輸出不符合契約。請保留錯誤 JSON，不要將完整 Key 傳到聊天或存入 Repository。
- 這次只使用先前保存的 BEA E7 官方摘錄，不重新抓取最新網站，也不證明該摘錄在當前真實可靠。

## 程式架構與限制

1. 使用 `rebuild_r5/qa_gate.py` 完整驗證 R1～R5，**80 項**原有離線測試。
2. R6 新增 **19 項**離線單元測試，涵蓋 JSON schema、拒絕跨來源／不存在事實、輸出拒絕、格式失敗、額外自由文字、數值幻覺、付費前阻擋、API 一次呼叫上限與密鑰不落地。
3. 只針對 **BEA** 做一則真實模型選擇。傳入固定 E7 摘錄及由 R4 統一規格生成的數值，模型只回傳 `case_id`、`priority`、`focus_fact_ids`、`theme_id`、`question_ids` 五個欄位；**沒有自由生成的新聞分析文字或數字**。
4. 使用 OpenAI Responses API 的 **Structured Outputs**，配合 R4 Python 校驗，不因欄位合法就自動發佈。
5. 由程式從事實表帶入原始數值，形成 HTML／JSON；全部標記 `publication_allowed=false`、`human_approved=false`。
6. API 使用 `gpt-4.1-mini`、`max_output_tokens=320`、`store=false`、**最多一次 POST，不自動重試**。若發生逾時等無法確定伺服器是否已處理的狀況，也不會重試。

**目前只能確認本機的離線測試，尚未於你的 GitHub 進行真實 OpenAI API 測試。** 若模型順利回傳結構化欄位，也僅完成 R6 **技術驗收**；R7 還需要證明 AI 分析是否提供實質情報價值。
