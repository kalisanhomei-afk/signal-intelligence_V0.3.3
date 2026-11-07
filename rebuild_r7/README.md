# SIGNAL Evidence Rebuild R7｜情報品質驗收（離線預審）

## 目的與狀態

R6 已證明：`gpt-4.1-mini` 可以選擇固定 BEA 事實 ID，程式再根據來源紀錄呈現數值。**但模型並未撰寫原創深度分析，不能把 R6 的 `Success` 當作 R7 情報品質通過。**

這份 R7 增量包只做「離線編輯品質預審與人工記錄」，**不改變 R1～R6、不呼叫 OpenAI、不設定 API Key、不修改 GitHub Actions、不觸發付費、不發布網站**。

依據：你上傳的 `signal-r6-one-bea-live-manual-review.zip` 內 `r6_result.json`。本包 `fixtures/r6_live_result_sanitized.json` 移除不需要的 OpenAI request ID，其餘涉及品質判斷的欄位保留。資料是 **2026-11-06 的歷史固定快照**，不是目前重新讀取 BEA 網頁。

## 已得出的結論（不能當作人工簽核）

| 項目 | R7 預審 |
| --- | --- |
| R6 技術契約 | 通過（僅限該筆歷史輸出） |
| 模型自行生成數字 | 0（根據 R6 輸出紀錄） |
| 選中事實 | 4 筆，F001/F002/F005/F006 |
| 統計期間 | 四筆 `period_as_written` 均為 null，尚未核實 |
| 統計口徑 | F005、F006 標為「範圍待核」 |
| 模型提供新的分析論述 | 未提供；R6 只選預設枚舉 ID |
| 重要性評分 | 不能由單一案例估計準確率 |
| 已有人工審核 | 尚未完成 |
| 是否允許正式發布 | **NO-GO** |

R7 評估程式只根據 **R6 結果可直接證明的欄位** 判斷工程狀態與資訊缺口。它不會假裝完成外部新聞查證。

## 使用方式 A：不用 Python（最簡單）

1. 解壓縮本包，直接用 Chrome 開啟 `rebuild_r7/out/r7_quality_review.html`。
2. 查看事實對照、驗收未完成的原因。
3. 完整核對 BEA 官方來源後，填寫網頁下方人工評分與備註。
4. 按「匯出人工審閱 JSON」；檔案只會下載至你的電腦，不會上傳資料。
5. **人工評分並不解除 NO-GO 或發布閘門。** 後續還需完成可信度、深度、重要性、可用性要求。

## 使用方式 B：重新執行離線規則檢查（需 Python）

在 Repository 根目錄執行：

```powershell
py -3 rebuild_r7\evaluate_r6.py
py -3 -m unittest discover -s rebuild_r7 -p "test_evaluate_r6.py" -v
```

或雙擊 `rebuild_r7/執行R7離線預審.bat`。

預期：產生 / 覆寫 `rebuild_r7/out/r7_quality_result.json` 與 `r7_quality_review.html`，10 項本地測試通過，決策 `NO_GO_PEND_EVIDENCE_AND_HUMAN_REVIEW`。

## GitHub Desktop 增量更新

1. 確認 `Current branch` 為 `signal-evidence-rebuild`，不要切換 `main`。
2. **先確認 `rebuild_r6/APPROVE_ONE_CALL.txt` 目前是 `APPROVE_ONE_CALL=NO`。**
3. 從更新包中**只複製整個 `rebuild_r7` 資料夾**到 Repository 根目錄，與 `rebuild_r1`～`rebuild_r6` 並列。
4. `Changes` 應僅新增 `rebuild_r7`。不要改 `.github/workflows` 或 R6 授權檔案。
5. Commit Summary：`Add offline R7 editorial quality gate and review scorecard`。Commit 到 `signal-evidence-rebuild`、Push origin。
6. **不建立 PR、不 Merge、不點 Re-run、不付費。** 由於工作流程 R6 是分支 push 觸發，新增 R7 時仍可能看到 `offline_qa` 執行，而 `one_paid_call` 必須是 Skipped；若不是，停止並檢查工作流程。

## R7 後續進入整合的硬性標準（提案，尚未達成）

- 每項關鍵數據具有來源、期間、範圍、原始單位及核對記錄；零個無證據的重大數據主張。
- 解釋段落明確區分「已知事實、合理假說、待查問題」；不以預設泛用文字冒充分析成果。
- 至少包含 BEA、EIA、arXiv 代表案例，讓人工比較模型的事實、推論、重要性與決策價值；需預先固定評量尺度。
- 對模型評分至少經人工對照後，才討論 R8 整合；**本次單一 BEA 案例不能推算全球重大新聞召回率。**

## 檔案

- `evaluate_r6.py`：離線規則檢查與報告產生程式。
- `test_evaluate_r6.py`：10 項防止誤判/誤發布檢查。
- `fixtures/r6_live_result_sanitized.json`：由你上傳的 R6 真實執行結果處理而來。
- `out/r7_quality_result.json`：可供機器閱讀的規則式預審結果。
- `out/r7_quality_review.html`：離線黑金人工審閱頁面，可在瀏覽器填寫並下載審閱 JSON。
- `執行R7離線預審.bat`：Windows 一鍵重新驗證。
