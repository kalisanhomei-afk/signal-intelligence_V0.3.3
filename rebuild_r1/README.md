# SIGNAL｜Evidence Rebuild R1（隔離離線實驗）

## 目的與邊界
這是針對既有 V0.5.4 錯誤的**結構重建最小實驗**，不是全套 SIGNAL 更新，也不是可上線的正式 AI 引擎。

- **只讀已保存的 BEA E7 摘錄**，不連網、不爬蟲、不呼叫 OpenAI、不更新網站或資料庫。
- 以**明確的文字格式**擷取來源原始數值，並固定 `fact_id`、原始數值、原始單位及來源摘要雜湊。
- AI 將來只能選用事實編號與提出**標示為假說**的文字，不得再自行寫金額或其他數值。數字由程式從事實資料表產生。
- 人工審核前 `publication_allowed=false`；不標示獨立查證。
- 遇到文件文字結構不符，**拒絕產生事實**，不猜測。

這是針對固定摘錄的概念驗證，不是可任意讀取所有 BEA／EIA／arXiv 文章的通用解析器。不得因通過這些測試而宣稱全系統可信。

## 在 Windows 本地執行
從本資料夾的上一層（Repository 根目錄）執行：

```powershell
python -m unittest discover -s rebuild_r1 -p "test_*.py" -v
python rebuild_r1/fact_pipeline.py --input rebuild_r1/fixtures/bea_e7.json --output rebuild_r1/out/bea_facts.json --report rebuild_r1/out/bea_review.html
```

開啟 `rebuild_r1/out/bea_review.html`，可看到黑金風格的待人工審核對照頁。

目前**不需要執行任何付費 GitHub Actions**。

## GitHub Desktop 開發隔離（不影響 main）
1. 先確定 Current branch 是 `main`，左側無未提交的變更。
2. `Fetch origin`，如果顯示 `Pull origin` 就點選。
3. `Current branch` → `New branch` → 名稱 `signal-evidence-rebuild` → `Create branch`。
4. **確認 Current branch 已切換至 `signal-evidence-rebuild`，才複製 `rebuild_r1` 資料夾到 Repository 根目錄。**
5. Commit Summary：`Start isolated evidence-fact rebuild R1 (offline only)`。
6. 先在本機執行上述離線測試。通過後可 `Publish branch`（**不是 merge into main**）。
7. 不要執行舊的 `SIGNAL V0.5.4 official evidence + optional AI pilot` 付費工作流程。

## 下一個關卡（未完成）
1. 人工核對 BEA E7 的指標、統計範圍與編輯日期；修正/確認 source metadata。
2. 依同一個 schema 增加 EIA 和 arXiv，但要**分別寫資料型別的抽取規則**，不得套用 BEA 的正規表示式。
3. 建立只接受 fact IDs 的模型輸出 schema，使用本地模擬回覆測試多筆失敗情況。
4. 在**保留完整錯誤診斷、零自動發布、離線測試通過**後，才啟動單次真實付費 API 驗收。
5. 人工驗收通過後，再以 Pull Request 合併；不要直接覆蓋 `main`。

## 來源
`bea_e7.json` 僅轉用使用者提供之 SIGNAL V0.5.4 測試 Artifact 中的 E7 段落，用於離線驗證；沒有新增未經查證事實或其他來源。
