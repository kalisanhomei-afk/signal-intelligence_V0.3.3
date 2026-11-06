# SIGNAL Evidence Rebuild R4｜三來源整合＋AI 選擇／程式引用契約

**版本定位：獨立離線驗收版，禁止直接合併 `main`；本包不呼叫 OpenAI API，不觸發 GitHub Actions。**

## 此版本完成什麼

- 不改動 `rebuild_r1`、`rebuild_r2`、`rebuild_r3`，而是**再次從其固定來源摘錄重新執行原有擷取程式**，統一產生 16 筆待核對事實（BEA 6、EIA 4、arXiv 6），並保持時間、單位、數值角色、來源 E 編號、SHA256 與限制。
- AI 的輸出介面暫時只允許選擇 `case_id`、`priority`、`focus_fact_ids`、`theme_id`、`question_ids`。**AI 不提供數字、不填入數值、不產生可發布的事實文字**。
- 事實表和金額／百分比只由程式使用來源擷取值渲染；分析角度與待查問題從固定、分來源的文字庫選出，內容明確為**條件式假說**。
- BEA 的年份不能只靠標題升格成統計期間；EIA 的 12% 是門檻，45–50% 是典型範圍；arXiv 的 52%／49% 是**作者摘要自述，不能稱成功率／準確率**。
- 遇到跨來源 ID、未知 ID、模型新增數字欄位、預設主題以外的自由文字、重複 ID、異常優先級，都拒絕，不會「盡量猜」。

> **關鍵限制：這並非任意來源通用的抽取器；只檢驗事先保存、限定內容的三則資料。** R4 所謂「AI 分析」是**模擬模型選擇**，不是模型生成完整洞察，也無獨立事實查證。若要生成真正有用的分析，需要在 R5 離線測試輸出契約與品質後，再於 R6 受控測試。

## GitHub Desktop｜只要複製一個資料夾

1. `Current branch` 應為 **`signal-evidence-rebuild`**，不要選 `main`。
2. 下載並解壓縮 R4 ZIP。把其中的 **`rebuild_r4` 資料夾**直接複製至 Repository 根目錄，與 `rebuild_r1`、`rebuild_r2`、`rebuild_r3` 並列。
3. 用 Chrome 打開 `rebuild_r4/out/offline_review.html`，可閱讀預先產生的三則對照報告。
4. 回 GitHub Desktop，確認新增的檔案只在 `rebuild_r4`；Summary：

   `Add R4 offline cross-source fact binding and mock AI contract`

5. 點 **Commit to signal-evidence-rebuild** → **Push origin**。
6. **不要 Create pull request，不要 Merge into main，不要跑 V0.5.4 付費 Actions。**

## 可選：用 Python 自行重跑離線測試

須有 Python 3.10+，所有依賴只有 Python 標準函式庫。在 Repository 根目錄開啟 PowerShell：

```powershell
python -m unittest discover -s rebuild_r1 -p "test_*.py" -v
python -m unittest discover -s rebuild_r2 -p "test_*.py" -v
python -m unittest discover -s rebuild_r3 -p "test_*.py" -v
python -m unittest discover -s rebuild_r4 -p "test_*.py" -v
python rebuild_r4/binding_pipeline.py
```

若 Windows 使用 `py` 命令，將 `python` 改成 `py`。最後開啟 `rebuild_r4/out/offline_review.html`。

### 檔案說明

| 檔案 | 用途 |
|---|---|
| `binding_pipeline.py` | 重新讀取 R1/R2/R3 固定摘錄、整合事實、驗證模型選擇、產生報告 |
| `fixtures/mock_ai_selection.json` | 只含 ID、枚舉值與選項的模擬 AI 回傳資料 |
| `test_binding_pipeline.py` | 負面情境、防止數值幻覺與越權引用的離線測試 |
| `out/fact_catalog.json` | 16 筆統一規格事實，供程式與人工檢視 |
| `out/analysis_review.json` | 模擬選擇的結構化綁定結果，不是實際 API 回覆 |
| `out/offline_review.html` | 黑金風格人工審閱報告 |

## R4 驗收界線

本機測試可以證明：在這一組固定資料、限定的模型輸出形式下，模型不能透過契約捏造數值或跨來源挪用 ID。**不能證明**被引用的原始來源正確、模型的判斷重要性準確、因果假說有充分證據、或任何任意新聞可以用相同解析器處理。

### 下一步 R5

將 R4 的資料契約加入更全面的錯誤測試、來源版本漂移與結果重播；建立「錯誤回覆 → 拒絕／不付費 → 人工審核」的統一報告。在全部離線驗收完成以前，不接上真實 API。
