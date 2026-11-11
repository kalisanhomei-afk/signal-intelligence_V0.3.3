# SIGNAL K2｜雙引擎離線研究原型

> **合成資料，非 USDA 實測資料、非價格預測、非交易訊號。** 此增量模組使用已上傳的 K1 `research_core`，無外部套件、無 OpenAI API 呼叫、不更新正式網站。

## K2 如何運作

**引擎 B（正向）**：鎖定 K1 提供的 `as_of` 研究時點，以事先聲明的假設衝擊改變存量流量驅動變數（`beginning_stocks`, `production`, `imports`, `domestic_use`, `exports`），由程式重新計算期末庫存。直接修改 `ending_stocks` 被拒絕。結果是敏感度分析，不是校準過的預測。

**引擎 A（反向）**：在後續資料修訂真正可用之後，比較兩個 K1 資料版本，分解「哪些變數的會計修訂貢獻了期末庫存變動」，並保留多項**未驗證上游假說**（單產、面積、方法修訂）；不得反向認定已證實因果。

**閉環**：將事先凍結的合成情境和事後可得的修訂相比，計算誤差／殘差，保留後續研究任務。單一虛構案例的殘差不是模型績效證據。

## 安裝（增量）

保留你已安裝的 `research_core` 全部原有檔案，只新增 `research_core/k2` 這個資料夾。**不要把整份 K1 ZIP 再覆蓋既有 Repository**。

## Windows 驗收（Python 3.11 以上）

在 Repository 根目錄開啟 PowerShell：

```powershell
py -3 -m unittest discover -s research_core/k2/tests -v
py -3 -m research_core.k2.demo
```

或在檔案總管雙擊 `research_core/k2/執行K2離線驗收.bat`。如果尚未安裝 Python，可直接開啟本包內的 `research_core/k2/out/k2_review.html`，但那代表的是**打包環境的測試結果**，不是你本機重新執行的結果。

## 驗收產物

- `out/k2_forward_scenarios.json`：正向假設與會計結果（無預測機率）。
- `out/k2_reverse_hypotheses.json`：資料修訂分解與未驗證候選因果。
- `out/k2_closed_loop.json`：事先情境 vs 後續修訂差額。
- `out/k2_qa.json`：機器可讀驗收條件。
- `out/k2_review.html`：黑金介面、可讀驗收報告。

## 完成邊界與下一關 K3

K2 目前驗證的是**雙引擎資料流與會計推演安全性**，不是有預測能力的模型。K3 應從 USDA 等官方資料建立多期、具真正發布時點的基準比較；然後才考慮期貨市場預期、模擬報酬及風控。若 K3 無法優於簡單基準，不得宣稱「投資優勢」。
