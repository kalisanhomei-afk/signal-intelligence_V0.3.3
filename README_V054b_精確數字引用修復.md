# 視界 SIGNAL V0.5.4b｜數字引用精確校驗修復（覆蓋包）

## 這次實測確定的事

2026-11-06 新上傳的 `signal-v054-source-excerpts-ai-manual-review(1).zip` 顯示：官方證據擷取 **3/3**；此次 `run_paid_ai=true` 且 `max_paid_calls=1`；付費呼叫 **1**、驗收草稿 **0**、失敗 **1**。失敗發生在 BEA 美國貿易報告，錯誤代碼為 `numeric_not_exactly_in_cited_excerpt`。EIA 與 arXiv 被標記 `evidence_only_not_ai` 是因為本次設為 1 次付費呼叫上限，不是這兩家出錯。

這表示**模型返回的一個數字沒有逐字出現在它所引用的 E1～E9 摘錄中**，不能據此推斷 API Key 設定錯誤。原版僅保留錯誤代碼，因此目前尚不知道是哪個數字引起拒絕。可能是把來源標題的年份放到事實句，或做了數字／單位轉換；尚無證據證明是哪種。

## 本包包含 4 個檔案（只覆蓋程式和工作流程）

- `scripts/evidence_analysis_v054.py`：
  - 強化模型指示：`key_facts` 中的數字須與所引用的證據片段逐字一致；不引用標題、網址、日期當成數據依據。
  - 將「字串包含」校驗改為**完整數字 token 相符**，避免把 `9` 錯認為出現在 `21.9` 裡面。
  - 若還有不一致，僅在私有測試 Artifact 記錄最多一個 `rejected_numeric_token`，不儲存模型未過審的完整回覆。
  - 未通過校驗的草稿，不會寫入 `analysis` 欄位。
- `scripts/pilot_report_v054.py`：人工審查 HTML 顯示失敗數字（如有）；所有報告仍標示未獨立驗證。
- `.github/workflows/signal-v054-evidence-pilot.yml`：在付費測試前執行新的離線回歸測試；原本的 1 次／3 次付費上限保留。
- `scripts/test_v054b.py`：新增無網路／不收費的回歸測試（錯誤年份、數值片段誤判、單位轉換、通過案例）。

## 安裝

1. 先在 GitHub Desktop 執行 **Fetch origin**，如有 **Pull origin** 再執行；不要 Force push。
2. 將此 ZIP 解壓縮，直接把**包內的 `.github` 與 `scripts` 資料夾**複製到 `signal-intelligence_V0.3.3` 的 Repository **根目錄**；遇同名檔案選擇覆蓋。不要覆蓋或刪掉 `data/`。
3. GitHub Desktop Summary 填：`Harden numeric citation matching in SIGNAL V0.5.4b`，點 **Commit to main → Push origin**。
4. GitHub → Actions → **SIGNAL V0.5.4 official evidence + optional AI pilot (manual only)** → **Run workflow**。
5. Branch `main`；`run_paid_ai=true`；`max_paid_calls=1`。不要選 **Re-run jobs**（那會用原本執行時的 Commit）。
6. 即使 AI 驗收失敗，工作流程仍應上傳 Artifact。下載 `signal-v054-source-excerpts-ai-manual-review`，檢查 `analysis.json` 的 `draft_count`、`error_code`、新欄位 `rejected_numeric_token`（如果有）。

## 驗收標準

- 技術：證據來源至少一個可讀；對 BEA 的 **1 次付費呼叫**產生 `draft_count=1`、`api_failures=0`，才算 AI 草稿通過**格式與字面證據校驗**。
- 可信度：即使草稿通過，`verified_claims` 仍為 **0**，不得視為已查證新聞、外部獨立證明或投資訊號；需人工逐項閱讀原始頁面核實含意。
- **本包無法保證下次真實模型一定成功**：提示詞改善可以減少不匹配，但若仍出錯會留下更有診斷價值的「數字 token」，而且仍然拒絕不符引用的內容。

## 本機離線驗收（開發者紀錄）

- `test_v054.py`: PASS
- `test_v054_hotfix.py`: PASS
- `test_v054b.py`: PASS
- 以上都是本機／模擬測試；**未呼叫真正付費 API**。
