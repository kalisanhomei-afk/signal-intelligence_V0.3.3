# SIGNAL Evidence Rebuild R5｜離線整合品質驗收

**本次只新增 `rebuild_r5/`；請維持 GitHub Desktop `Current branch = signal-evidence-rebuild`。**

## R5 的作用

R5 是 R1–R4 的**固定離線測試資料之回歸／對抗驗收關卡**，不是新聞蒐集升級、不是 AI 新模型，更不是可發布的新聞分析引擎。

核心測試包括：

1. 固定 R1–R4 程式／三份存檔證據／R4 模擬選擇資料的 SHA256 指紋；若來源或程式意外改變即拒絕通過。Windows CRLF 換行差異會正規化後再檢查。
2. 使用同一組證據連續生成兩次，核對 16 筆事實及離線分析報告的**重播一致性**。
3. 以對抗範例測試不合法 JSON、重複 JSON 鍵、未知來源、跨來源 Fact ID、偽造數字、越權發布、型別錯誤、HTML 注入等，確保出錯時**拒絕**而不是自行猜測修正。
4. 自動重跑 R1、R2、R3、R4 與 R5 的單元測試，產出 `qa_result.json` 和黑金風格 `qa_review.html`。

**執行環境：Python 3.10+，只用 Python 標準函式庫；不使用 OpenAI API、不呼叫網站、不需任何密鑰、不發布 GitHub Pages。**

## 使用者操作：只新增一個資料夾

1. GitHub Desktop → `Current branch` 確認是 `signal-evidence-rebuild`；**不要切換 main**。
2. 解壓縮 R5，將整個 `rebuild_r5` 複製到 GitHub Repository 根目錄，與 `rebuild_r1` ~ `rebuild_r4` 並列。
3. 用瀏覽器開啟 `rebuild_r5/out/qa_review.html`，先讀本次預產出的離線驗收報告。
4. GitHub Desktop → Summary 輸入 `Add R5 offline preflight regression and adversarial QA gate`。
5. 點 `Commit to signal-evidence-rebuild` → `Push origin`。**不要 Create pull request、不要 Merge into main，也不要再執行 V0.5.4 付費工作流程。**

## 可選：在自己的 Windows 電腦上重跑實測

若已安裝 Python，可雙擊 `rebuild_r5/執行R5離線驗收.bat`（它會切換到 Repository 根目錄執行）。成功時自動開啟新的 `qa_review.html`。未安裝 Python 時仍可閱讀原附的報告，但該預產出報告只能證明**開發時的固定樣本**通過測試，不是你 GitHub 工作區已經通過本機驗收。

也可在 Repository 根目錄 PowerShell 執行：

```powershell
python rebuild_r5/qa_gate.py --root . --out rebuild_r5/out
```

成功的終端輸出範例：

```text
OFFLINE_PASS_R6_CANDIDATE: 80 tests; replay=PASS; sources=PASS; API calls=0
```

若出現 `BLOCKED_NO_R6`，請查看 `rebuild_r5/out/qa_result.json` 的 `issues` 與 `suites`；**在修復並重新驗收前，不進行 R6 真實 API 測試**。

## R5 驗收範圍及不可聲稱的事項

- 開發環境的固定樣本已完成 **80 項測試**：R1=9、R2=11、R3=17、R4=22、R5=21。這些數字是 test method 數量，不是完整涵蓋率。
- 來源及事實仍是「存檔摘錄、待人工審核」，不能升格為獨立查證新聞。
- R4 的模擬模型只能選擇封閉 ID 與預設分析主題；沒有真正驗證自由生成洞察或重要性判斷的品質。
- SHA256 指紋防止**固定快照**意外漂移，不等於證明新聞或原始資料在外部世界真實無誤。
- 若未來想更新 R1～R4 程式或資料，請建立新基準並重新審查，**不要直接刪除指紋檢查讓測試變綠**。

## 下一階段：R6（尚未執行）

完成 R5 後，將在分支上額外建立可選、最多 1 次付費呼叫的**真實模型回覆契約冒煙測試**；仍不合併 main、不發布正式情報。只有 R6 成功後才進入 R7 人工品質驗收。
