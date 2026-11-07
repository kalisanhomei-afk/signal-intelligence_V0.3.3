# SIGNAL Evidence Rebuild R8-B｜受證據約束的真實 AI 分析 — 安裝與驗收

**版本：** R8-B 第一版受控測試包（2026-11-07）  
**範圍：** 僅在 `signal-evidence-rebuild` 開發分支新增內容；不改 `main`、首頁、RSS、不部署 Pages。  
**本次狀態：** 程式已完成、離線／假回應測試通過；**尚未在你的 GitHub 環境進行真正 OpenAI API 呼叫。**

## 這次修正了什麼問題

R6 已能讓模型「選擇已存在的事實 ID」，但產出的原因、影響與追蹤事項主要是既有預設內容。R8-A 先用人工撰寫的模擬輸出驗證自由敘述契約。R8-B 終於加入**真正呼叫 Responses API 的獨立程式**，讓模型在以下欄位自由撰寫可受查核的文字：

1. 核心觀察：必須選擇 BEA 事實 ID，標記 `fact`。
2. 可能機制：必須選擇事實 ID、標記 `inference`，並列出假設。
3. 條件式影響：必須選擇事實 ID、標記 `hypothesis`，並列出假設。
4. 重要性理由：提供具體理由與事實 ID，可選「待評估」，不能無理由升為重大。
5. 限制及不確定性：必須至少一項。
6. 可執行追蹤問題：必須說明 `question`、`target_source` 和 `decision_test`。

**數字的出處仍由 R4 固定事實資料表提供，模型只能提供 fact_ids，不可自行生成數字或年份。** 程式使用 R8-A 原有的 `validate_draft()` 進行結構檢查、引用 ID 比對與部分不實用語攔截，失敗即拒絕；不會把模型寫出的文字當成獨立驗證過的事實。

固定案例只有一篇 **BEA 美國對台貿易歷史資料**，沿用 R8-A 的十六筆資料快照，但本次模型只能引用其中六筆 BEA 事實。BEA 部分欄位仍缺統計期間與口徑資訊，**不可宣稱全數已獨立確認**。

## 更新包內容（增量更新，不要整個覆蓋舊資料夾）

```
README_先看這份.md
rebuild_r8/
    r8b_live.py                   # OpenAI Responses API 單次呼叫；模擬或真實模式
    r8b_gate.py                   # 完整記錄授權條件、並擋住 Re-run
    test_r8b_live.py              # 34 項網路隔離的測試
    APPROVE_R8B_ONE_CALL.txt      # 初始是 NO
    README_R8B_先看這份.md
    out/r8b_offline_preview.json  # 人工模擬報告，不是 AI
    out/r8b_offline_preview.html
.github/workflows/
    signal-evidence-r8b-branch.yml
```

注意：`r8b_live.py` **會匯入你已安裝的 `rebuild_r8/r8_offline.py`**，並讀取 `rebuild_r8/fixtures/`。因此請確保 R8-A 已上傳且該資料夾存在；這不是可獨立取代 R8-A 的完整包。

## 【現在只進行第一階段：零費用上傳與離線驗收】

1. 開啟 GitHub Desktop，Repository 選 `signal-intelligence_V0.3.3`；Current branch 必須是 **`signal-evidence-rebuild`**，不能是 `main`。
2. Repository → Show in Explorer，確認原有 `rebuild_r8/r8_offline.py`、`rebuild_r8/fixtures/` 與 `rebuild_r6/APPROVE_ONE_CALL.txt` 存在。**R6 的授權必須仍為 `APPROVE_ONE_CALL=NO`**。
3. 解壓本更新包。先進入解壓後的 `rebuild_r8`，**只複製其新增的 5 個檔案（`r8b_live.py`、`r8b_gate.py`、`test_r8b_live.py`、`APPROVE_R8B_ONE_CALL.txt`、`README_R8B_先看這份.md`）和 `out` 中兩個 R8-B 預覽檔案**至 Repository 原有的 `rebuild_r8` 內相同位置；原有 `r8_offline.py`、`test_r8_offline.py`、`fixtures` 不動。
4. 另外從更新包 `.github/workflows/` 中只複製 **`signal-evidence-r8b-branch.yml` 這一個檔案**，貼到 Repository 原本的 `.github/workflows`。不得刪改其他 `.yml`。
5. 再確認 `rebuild_r8/APPROVE_R8B_ONE_CALL.txt` 是 **`APPROVE_R8B_ONE_CALL=NO`**。這次絕對不要改 YES。
6. 回 GitHub Desktop → Changes：應是新檔案，不應刪除或修改原有程式。Commit Summary 輸入 **`Add R8-B isolated narrative pilot and gated single model call`**，然後 Commit to `signal-evidence-rebuild` → Push origin。
7. 進入 GitHub → Actions，尋找 **`SIGNAL R8-B isolated narrative QA and optional one API call`**。第一次預期：`offline_qa` Success、`approval_gate` Success（內部顯示 approved=false / commit_message_mismatch）、`one_paid_call` Skipped。此次 API 呼叫 **0 次**。
8. 在該次 Actions 下方 Artifacts 下載 **`signal-r8b-offline-qa`**。當作完成 GitHub 環境的離線驗收證據，提供給 ChatGPT 核對。**第一次不要執行付費測試。**

若不想先上傳 GitHub，Windows 安裝 Python 3.10+ 後在 Repository 根目錄可以執行：

```powershell
py -3 -m unittest discover -s rebuild_r8 -p "test_r8_offline.py" -v
py -3 -m unittest discover -s rebuild_r8 -p "test_r8b_live.py" -v
py -3 rebuild_r8\r8b_live.py --mock
```

成功可開啟 `rebuild_r8/out/r8b_offline_preview.html`，其內容明確標記為**人工編寫模擬案例，非 AI 產生**。

## 【第二階段：離線確認後才由你授權一次付費 API】

**不要在第一階段直接操作。** 需先確認：第一階段 GitHub 測試成功；R6 舊授權仍為 NO；且 `OPENAI_API_KEY` 已設定在 GitHub Secrets。

1. 在 Repository 中**只修改** `rebuild_r8/APPROVE_R8B_ONE_CALL.txt`：`APPROVE_R8B_ONE_CALL=NO` → `APPROVE_R8B_ONE_CALL=YES`。
2. GitHub Desktop 確認只有這個檔案變更；Commit Summary 必須一字不差：**`SIGNAL_R8B_APPROVE_ONE_PAID_CALL`**。
3. Commit → Push origin。`approval_gate` 必須確認**分支正確、GitHub 重跑次數為首次、該次提交僅修改授權檔、上一個版本 NO、新版本 YES、Commit 訊息正確**，才會執行 `one_paid_call`。
4. 有效時程式最多呼叫 **1 次** OpenAI `Responses API`，沒有自動重試。結果為 **`signal-r8b-one-bea-narrative-unverified`** Artifact，包含 `r8b_live_result.json`、`r8b_live_result.html`。若模型拒絕、不完整或不通過校驗，工作應顯示 Failure，Artifact 會保留安全診斷，不會發布。
5. **不要使用 Re-run jobs 或 Re-run all jobs。** 即使重跑，程式會檢查 `GITHUB_RUN_ATTEMPT != 1` 並禁止付費操作，但仍不應有不必要重跑。
6. 執行後不論成功失敗，立即將授權檔恢復為 `NO`，以一般 Commit Summary `Close R8-B paid authorization` 提交 Push，不會觸發付費呼叫。

## 與之前 R6 授權的區別

- **R6：** `rebuild_r6/APPROVE_ONE_CALL.txt` 必須保持 **NO**。
- **R8-B：** 使用**另一個獨立檔案** `rebuild_r8/APPROVE_R8B_ONE_CALL.txt`，本次上傳必須保持 **NO**。
- 新工作流程不與 R6 既有工作流程合併或修改。推送本分支時，R6 原有 workflow 也可能執行離線測試，但不應付費；請檢查它仍跳過 `one_paid_call`。

## 技術、安全與品質限制

- **工作流程狀態 Success ≠ 情報品質通過。** 只有 `r8b_live_result.json` 實際標示 `mode=LIVE_MODEL_UNVERIFIED`，才可證明生成了真實 AI 草稿；之後仍須 R8-C 人工審閱五項品質。
- 來源為**固定歷史摘錄**，不是即時新聞；目前不做新的來源抓取與交叉驗證。
- 本版透過 Structured Outputs 保障欄位與 enum 格式，但不能保證自由文字內容正確。數字與禁語攔截是**詞彙防護**，不是語義核查。倘若模型自由文字作出沒有數字的錯誤事實宣稱，仍須人工識別。
- `publication_allowed=false`、`human_approved=false`，不部署 Pages；GitHub Artifacts 不是私人保險箱，**請不要把個人敏感資料、帳號或 API Key 放入快照**。
- 程式使用 Python 標準庫，直接向 `https://api.openai.com/v1/responses` 送出一個 POST（`store: false`，不自動重試）。不同 ChatGPT 訂閱不包含 API 使用額度。
- GitHub 的再執行護欄主要限制 API **同一 Workflow run 的 rerun**，不是跨所有 Repo 的全局計費上限；若手動再次授權另一個 NO→YES 提交，仍可能產生另一筆費用。
- API 可能發生 HTTP 錯誤，或 Structured Outputs 完成但 R8-A 的詞彙規則拒絕部分文字。此時請先下載診斷 Artifact，不要連續嘗試，避免重複原來 V0.5.4 的付費除錯循環。

## 交付驗收

本包在隔離環境複製 R8-A 已有內容後執行了 **R8-A 33 項 + R8-B 34 項 = 67 項測試通過**，測試包含模擬 HTTP 回覆、錯誤碼、格式、引用、數值、頁面安全、授權、重跑擋下與真正 Git 提交 NO→YES 的閘門模擬。**沒有實際付費 API 呼叫，也沒有驗證 GitHub 的真實執行結果。**

**品質 Go/No-Go：** 真實草稿所有關鍵硬條件通過，仍須進行 R8-C 人工評分，各項至少 4/5 且沒有重大事實／因果錯誤，才能討論整合；即便通過也不能自動發布。
