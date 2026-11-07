# 視界 SIGNAL｜Evidence Rebuild R8-A：受證據約束的深度分析離線原型

## 這次**實際**完成什麼

本包是一個**新加的 `rebuild_r8` 資料夾**，只承接此前完成的 R8 規格；未修改原有 `rebuild_r1`～`rebuild_r7`、既有網站或 `.github/workflows`。

- 載入 R4 的**固定歷史快照**：BEA 6 筆、EIA 4 筆、arXiv 6 筆，共 16 筆待查核事實；SHA256 固定，以免測試資料在不知情時變更。
- 以 **人工撰寫的三則模擬分析** 演練 R8 的自由敘述契約（不是實際 OpenAI 生成）。區分「事實索引／推論／待證假說」，另列重要性理由、資訊缺口、可操作的追蹤問題。
- AI 未來只能填結構化文字和事實 ID；展示的數值、原始單位和來源網址由程式從 R4 快照帶入。
- 離線規則拒絕：不存在或跨來源 ID、重複 ID、模型自由文字中直接生成的數字/部分中文數量字詞、錯誤 claim_type、未列假設、缺少追蹤問題、絕對化斷言、要求自動發布、修改了事實快照。
- 產生黑金主題的 HTML 審閱頁，可在 Chrome 直接開啟、填寫人工分數並**下載本機 JSON**。R7 編輯參考評分作為背景，**不可冒稱 R8 AI 成績**。

## 非常重要的限制

1. **零付費、零 API、零網路讀取**。這是 `R8-A`，不是 `R8-B` 真實 AI。沒有在 GitHub 上執行付費測試。
2. 來源是 R4 **歷史快照**，資料為原來源的摘錄，不等於當下已重新核實的官方事實。原始數字可能仍缺統計期間與口徑；尤其 BEA F003～F006 保留「範圍待核」。
3. 程式的數字與禁語檢查是**詞彙規則，不是全面語義事實查核**；諸如暗示性因果、無數字的錯誤資訊，仍可能通過。重大主張需要人工核對原文。
4. arXiv 評估成績僅為作者摘要主張；不是已獨立查證的模型準確率或商業成功率。
5. `publication_allowed=false` 永遠保留；**不得拿這份範例當成正式新聞或已通過情報品質測試的內容**。

## 不安裝 Python 也可閱讀

開啟 `rebuild_r8/out/r8a_offline_review.html`，逐則閱讀 BEA／EIA／arXiv 模擬報告。頁面下方可輸入人工評分及文字備註，下載 `SIGNAL_R8A_人工評估_離線範例.json`。此功能不會連接外網。

## 如要在 Windows 重新執行離線驗收

在 Repository 根目錄開啟 PowerShell：

```powershell
py -3 rebuild_r8\r8_offline.py --check
py -3 -m unittest discover -s rebuild_r8 -p "test_r8_offline.py" -v
```

或者雙擊 `rebuild_r8/執行R8A離線驗收.bat`。只需要 Python 3.10+ 標準函式庫，無第三方安裝需求。執行會重新生成 `out/r8a_offline_result.json` 與 `out/r8a_offline_review.html`。

## GitHub Desktop 安裝：與之前 R1～R7 相同

1. 確認 `Current branch = signal-evidence-rebuild`；**不是 `main`**。
2. 檢查 `rebuild_r6/APPROVE_ONE_CALL.txt` 為 `APPROVE_ONE_CALL=NO`。
3. 解壓 ZIP，**只將 `rebuild_r8` 資料夾**放到 Repository 根目錄，與 `rebuild_r7` 並列。不得把整份 ZIP 放進 `.github/workflows`，也**不要修改任何 `.yml`**。
4. GitHub Desktop 的 Changes 應只有 `rebuild_r8/...` 新檔案。若看到舊檔案變更或刪除，請先取消提交並檢查。
5. Commit Summary：`Add R8-A offline evidence-bound narrative prototype`
6. 按 `Commit to signal-evidence-rebuild` → `Push origin`。**不開 PR、不合併到 main**。
7. 如果 GitHub 的 R6 工作流程因 Push 自動執行，付費 `one_paid_call` 應為 **Skipped**；不要使用 Re-run all jobs。

## 檔案

- `r8_offline.py`：離線驗證、綁定事實、產生審閱 JSON/HTML；沒有任何 HTTP/OpenAI 客戶端。
- `test_r8_offline.py`：固定快照、正反例、數字防護、安全顯示等離線單元測試。
- `fixtures/fact_catalog_snapshot.json`：由 R4 成果保留的 16 筆固定事實快照。
- `fixtures/mock_analysis_drafts.json`：**手工撰寫**的 BEA/EIA/arXiv 模擬分析，絕非 OpenAI 回答。
- `fixtures/r8_model_output_schema_reference.json`：R8 規格階段的 JSON Schema 參考；**尚未驗證是否與 OpenAI Structured Outputs 全面相容**。
- `fixtures/r7_editorial_reference_scores.json`：先前的編輯參考人工評分，不能宣稱為 AI 品質分數。
- `out/r8a_offline_result.json`：契約驗收摘要與三則分析。
- `out/r8a_offline_review.html`：黑金風格靜態審閱頁、人工評分匯出。
- `執行R8A離線驗收.bat`：一鍵離線測試。

## R8-A 下一步的 Go / No-Go

現在只完成**離線規則契約測試**。下一步 `R8-B` 應先針對 BEA 單筆真實模型輸出，使用既有 R6 權限控制、增加結構化文字生成的審閱層，並先驗證 OpenAI 輸出契約的實際相容性。未通過以前，不得宣稱 R8 AI 情報品質優於 R7，亦不可接入正式網站。
