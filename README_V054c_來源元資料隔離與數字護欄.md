# SIGNAL V0.5.4c｜來源元資料與 AI 證據隔離（最小修復）

## 根據使用者 2026-11-06 測試檔案得到的確定結果

`signal-v054-source-excerpts-ai-manual-review(2).zip` 中的 `analysis.json` 顯示：`api_calls_attempted=1`、`draft_count=0`、`api_failures=1`，錯誤為 `numeric_not_exactly_in_cited_excerpt`，被拒絕的數字是 `2026`。對應來源為 BEA 2026 年 9 月貿易報告。該候選的 9 段證據摘錄中沒有 `2026`，但報告**標題**包含 2026。這證明輸出數字沒有在引用摘錄內找到，**不證明模型在哪個句子如何使用該數字**，因為原始模型回應已依安全設計丟棄。

證據擷取狀態仍然是 3/3：BEA 9 段、EIA 8 段、arXiv 6 段。EIA / arXiv 未使用付費 AI 是因為 `max_paid_calls=1`。GitHub 綠燈只能代表工作流程執行，**這次 AI 草稿沒有通過**。

## 修正原則

不再直接讓模型看到原始標題、URL、發布日期等元資料；只傳入**選定的證據摘錄**、摘錄 ID、來源機構代號及證據類型。完整的文章標題、年份、日期與原始 URL **仍保存在 evidence.json 和人工審核網頁**，沒有刪除來源追溯。這可避免標題中的 `2026`、URL 識別碼等數字被模型錯誤帶入「以 E1～E9 為證據的事實句」。

數字逐字校驗規則、無授權自動發布、人工審查門檻及最多三次 API 呼叫上限均未放寬。如模型仍產生未被引用摘錄支持的數字，仍然拒絕輸出。這是減少錯誤的一項來源隔離修補，**不能保證每次 AI 請求成功**，也沒有執行任何真實付費 API 呼叫。

## 安裝

1. GitHub Desktop → Fetch origin；如有 Pull origin 再執行。**不要 Force push**。
2. 解壓縮本 ZIP；將 `.github`、`scripts` 兩個資料夾複製至 `signal-intelligence_V0.3.3` **Repository 根目錄**，覆蓋同名檔案。不要覆蓋 `data/`。
3. Summary：`Isolate source metadata from evidence-bound AI pilot V0.5.4c` → Commit to main → Push origin。
4. GitHub Actions → `SIGNAL V0.5.4 official evidence + optional AI pilot (manual only)`。第一次先 `run_paid_ai=false`，確認新的離線測試、來源擷取都正常（不收 AI API 費）。
5. 再新開一次 `Run workflow`，`main`、`run_paid_ai=true`、`max_paid_calls=1`。**不要按舊紀錄的 Re-run jobs**，以免仍使用舊程式。
6. 下載 Artifact：`signal-v054-source-excerpts-ai-manual-review`。檢查 `analysis.json`：`draft_count=1` 和 `api_failures=0` 才表示**格式及數字字面**初步通過；仍非事實查證成功。若失敗，提供 `analysis.json` 的 `error_code` 與 `rejected_numeric_token`，不需要洩漏 API Key。

## 本機測試及限制

- `test_v054.py`、`test_v054_hotfix.py`、`test_v054b.py`、`test_v054c.py` 由本機 Python 執行，不連網、不使用 API 額度。
- 仍須人工確認模型是否正確解讀摘錄的因果、期間及單位。**完整原始頁面並未交給模型**。
- 請留意：來源標題/日期不再提供給模型，中文草稿標題可能較籠統；人工審閱 HTML 頁面仍展示精確原始標題、日期和連結。
