# SIGNAL｜Evidence Rebuild R2（EIA 能源數據，隔離離線測試）

這是既有 `signal-evidence-rebuild` 分支的增量開發，不修改 R1，不合併 `main`，不執行 OpenAI API、GitHub Actions、RSS 擷取、正式網站發布或背景工作。

## 測試資料的來源與限制

本包 `fixtures/eia_yields_e2_e5.json` 僅由使用者上傳的 V0.5.4 Github Actions Artifact 內 `evidence.json` 取出 EIA 的 **E2、E5** 兩段摘錄，並保留該次執行保存的來源 URL、標題、發佈及擷取時間。這不是現在重新訪問 EIA 的結果；摘錄 hash 只提供一致性追溯，不代表官方資料已被獨立驗證。

R2 只處理這兩段特定格式，不是所有能源文章的通用擷取器。採硬式 fail-closed：URL／來源、摘錄內容或結構不符就拒絕輸出。

## 數字模型的重要區分

| ID | 文章中的表述 | 實際資料型別 | 禁止誤寫成 |
|---|---|---|---|
| EIA-F001 | gasoline yield 典型範圍下限 45% | 典型區間下界 | 2026 年每月觀測值 |
| EIA-F002 | gasoline yield 典型範圍上限 50% | 典型區間上界 | 2026 年每月觀測值 |
| EIA-F003 | jet fuel yield 2026 年 3 月首次超過 12% | **超過**門檻 | 3 月剛好等於 12% |
| EIA-F004 | jet fuel yield 至 2026 年 8 月仍至少 12% | **大於或等於**門檻 | 每月精確觀測值均為 12% |

完整指標口徑（分子／分母）、資料版本及修訂，仍須人工比對官方原文。不得由此推算未列出的燃料價格、產量、未來收益等結論。

## Windows 操作（從 GitHub Repository 根目錄執行）

請先確認 GitHub Desktop `Current branch = signal-evidence-rebuild`，把**整個** `rebuild_r2` 資料夾放在與 `rebuild_r1` 並列的位置，不覆蓋舊檔案。

以 PowerShell 或命令提示字元切換到 Repo 根目錄，執行：

```powershell
python -m unittest discover -s rebuild_r2 -p "test_*.py" -v
python rebuild_r2/eia_pipeline.py --input rebuild_r2/fixtures/eia_yields_e2_e5.json --output rebuild_r2/out/eia_facts.json --report rebuild_r2/out/eia_review.html
```

（若使用 Windows `py` 啟動器，可將 `python` 改成 `py`。）

執行後，開啟 `rebuild_r2/out/eia_review.html` 檢查數字、資料類型與來源。若只是先要在瀏覽器閱讀，可直接打開隨包附上的 HTML 範例；它不代表在使用者電腦成功跑過程式。

## GitHub Desktop 提交

1. 確認位於 `signal-evidence-rebuild`，而非 `main`。
2. Commit Summary：`Add offline EIA evidence fact R2 with guarded thresholds`。
3. 點選 `Commit to signal-evidence-rebuild` → `Push origin`。
4. **不要點 `Create pull request`，不要合併到 main。**
5. 不需要重新建立 API Key；也不要啟用舊 V0.5.4 的 `run_paid_ai`。

## 驗收界線

本次本地測試只驗證**固定摘錄的可重複解析、數值角色、來源校驗與拒絕篡改**。不是跨來源證實，不是 AI 分析成功，也未驗收所有不同格式的 EIA 報表。下一步 R3 才處理 arXiv 研究摘要；R4 才研究 AI 如何選擇既有 fact IDs。
