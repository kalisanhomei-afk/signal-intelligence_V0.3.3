# 視界 SIGNAL V0.5.4a｜AI 試驗錯誤診斷修復

## 背景與結論
2026-11-06 的兩份 GitHub Actions Artifact 顯示：官方頁面與摘要擷取 3/3 成功；付費 AI 試驗執行 3 次，但 3 次均因 `ValueError` 被程式拒絕，沒有任何可審閱的草稿。這不是擷取流程失敗，也不能單憑 `ValueError` 認定 API 金鑰失效。原始試驗沒有保存錯誤原因，因此 **尚無法確定是輸出不完整、格式、引用數值不一致或條件句檢查**。

## 本次更新 5 個檔案（含 1 個新測試檔）
- `scripts/evidence_analysis_v054.py`：記錄安全的錯誤代碼，不保存 AI 原始回覆、不輸出金鑰；對不完整回覆與引用檢查提供可判讀分類。
- `scripts/evidence_pilot_v054.py`：排除 EIA 網站導覽與標籤等非文章內容。
- `scripts/pilot_report_v054.py`：AI 失敗時顯示錯誤分類。
- `.github/workflows/signal-v054-evidence-pilot.yml`：新增 `max_paid_calls` 選擇 1 / 3，預設 1；所有草稿均失敗時在上傳 Artifact **之後**將工作判定為失敗，避免假綠燈。
- `scripts/test_v054_hotfix.py`：新增離線回歸測試；可自行保留作為驗收文件。

## 更新方式
1. GitHub Desktop：Fetch origin、若有 Pull origin 先執行；請勿 Force push。
2. 解壓縮本包，**複製包內資料夾/檔案到 Repository 根目錄**；覆蓋同名檔案，**不要**刪掉或覆蓋 `data/`。
3. Summary：`Diagnose V0.5.4 AI pilot failures and filter navigation snippets`。
4. Commit to main → Push origin。
5. GitHub Actions → `SIGNAL V0.5.4 official evidence + optional AI pilot (manual only)` → Run workflow。
6. `run_paid_ai=true`、`max_paid_calls=1`（先只花費一次模型呼叫）。
7. 到本次執行 Summary 查看 `AI rejection for ...: <reason>`；即使紅燈仍可從 Artifacts 下載 `analysis.json`。
8. 將新的 `analysis.json` 上傳對話；不要上傳任何金鑰。若有一則 AI 草稿通過，我們再進入人工品質檢查，並考慮三則全面測試。

## 重要限制
- 本修正**沒有放寬證據數字驗證**，不會因 AI 文字看起來合理就通過。
- 尚未保證真實 AI 呼叫可產生合格草稿，因目前沒有新的付費測試結果；第一次測試只為辨識問題。
- 網站 Pages 不受影響；API Key 保持放在 GitHub Secrets。
