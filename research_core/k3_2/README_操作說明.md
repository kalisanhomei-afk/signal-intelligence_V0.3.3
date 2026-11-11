# 視界 SIGNAL — K3.2 實體供需平衡與歷史證據入口

**2026-11-11｜研究用途｜手動觸發｜預設離線｜Python 標準庫｜無付費 API｜無 Pages｜無交易訊號**

## 1. 真正完成／尚未完成

| 工作 | 狀態 |
|---|---|
| 2026/27 美國玉米 2026-10 與 2026-11 每月原始 USDA 供需表 | **已核對兩份官方發行當期的文字版表格** |
| 期初＋產量＋進口－國內用量－出口＝期末庫存 | **以程式驗算；每期殘差 = 0** |
| 期末庫存月度修正橋接 | **完成；10→11 月為 -91 百萬蒲式耳** |
| 與 K3.1 的 October/November ending stocks 交叉對照 | **完成，兩筆一致** |
| 2010 至今的 USDA 歷史 vintage CSV 匯入器 | **已實作嚴格 schema 及來源白名單，使用模擬 CSV 測試；未用官方大檔實際驗證** |
| >=3 年完整官方 vintage 與每週 NASS 全量資料 | **尚未完成** |
| 氣象→單產→產量的模型訓練／walk-forward | **未開始；不得宣稱已有預測力** |
| 交易績效、行情 surprise 訊號 | **未開始；不得輸出投資建議** |

官方原始來源：
- 2026/10/09 USDA WASDE 676 美國玉米項目：`https://www.usda.gov/oce/commodity/wasde/wasde1026.txt`（美國玉米，報告 page 12）
- 2026/11/10 USDA WASDE 677 美國玉米項目：`https://www.usda.gov/oce/commodity/wasde/wasde1126.txt`（美國玉米，報告 page 12）
- 官方歷史 WASDE consolidated CSV 入口：`https://www.usda.gov/historical-wasde-report-data-3`

## 2. 差異歸因（不是因果識別）

使用當月完整原始報表：

`期末庫存 = 期初庫存 + 產量 + 進口 - 國內使用 - 出口`

單位：**百萬蒲式耳 (million bushels)**，同一行中不可混入百萬公噸 (million metric tons)。

| 項目 | 2026-10-09 | 2026-11-10 | 變動 | 對期末庫存修正的貢獻 |
|---|---:|---:|---:|---:|
| 期初庫存 | 2,095 | 2,095 | 0 | 0 |
| 產量 | 16,034 | 15,893 | -141 | -141 |
| 進口 | 25 | 25 | 0 | 0 |
| 國內使用 | 13,005 | 12,980 | -25 | +25 |
| 出口 | 3,300 | 3,275 | -25 | +25 |
| 期末庫存 | 1,849 | 1,758 | **-91** | **-91** |

此外，單產 181.2→179.6 蒲式耳／英畝；收成面積 88.5 百萬英畝未變。產量 ≈ 收成面積×單產，但 USDA 公布的面積和單產已四捨五入，不能以乘積強行覆蓋 USDA 精確公布的產量；允許 12 百萬蒲式耳以下的四捨五入誤差，供需恆等式本身則要求完全相等。

**識別限制：**「庫存因產量下降而減少 141」是同一份供需表的帳面橋接，不代表降雨、良好率等指標在 WASDE 公布前已可預測產量；那仍是待測假說。

## 3. 安裝與 GitHub Actions 操作

### 安裝（增量更新、不覆蓋 K3.1）

從 ZIP 最外層，將下面路徑放到 Repository 根目錄：

```
research_core/k3_2/
.github/workflows/signal-k32-balance-audit.yml
```

於 `signal-evidence-rebuild` 分支 Commit / Push。不要建立 `research_core/research_core/k3_2/` 這種重複路徑，不要刪除 `research_core/k3_1/`。

### 第一次：**離線與既有 K3.1 對照**

1. Actions → **SIGNAL K3.2 corn stock-flow audit (manual, offline-by-default)**。
2. Run workflow → Branch `signal-evidence-rebuild`。
3. `official_historical_csv_url` **留白**。
4. 下載 `signal-k32-balance-audit` Artifact，打開 `review.html` 和 `review.json`。
5. 驗收：**13 個測試成功、`RESEARCH_ONLY_NO_TRAINED_MODEL`、兩個官方月份平衡殘差為 0、-91 庫存修正、K3.1 MAE=149。**

本 Workflow 不更新既有網站、不呼叫模型、不部署 Pages、不消耗付費 API。執行權限只有 `contents: read`。

### 第二次：**選擇性下載 USDA 官方歷史 consolidated CSV**

Run workflow 同樣選 `signal-evidence-rebuild`，在 `official_historical_csv_url` 貼入：

```
https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-2026-10.csv
```

**來源提醒：**此 USDA 歷史頁在 2026-11-11 仍列出 2026/10 的 CSV；它是當時可見的最新 consolidated 歷史大檔，但其更新落後 November 2026 最新當月報告。因此，本包以個別官方 October/November 原文核對最近兩期，避免混用更新時點不同的數據。

此步會保留 Artifact：`official_historical_raw.csv`（未改動下載內容）、`historical_intake_audit.json`、`review.json`、`review.html`。歷史匯入只使用 `release_at`、`marketing_year`、`Ending Stocks`，不從後續修訂的最新靜態數列反推過去預測。

**目前限制**：此匯入器的欄位名稱依官方 consolidated 結構的公開描述設計，只以合成樣本完成單元測試，尚未直接取得 2026-10 下載位元組實測。遠端回傳若欄位／表名改變會 fail-closed：Action 紅色，不會補寫估計值。看到失敗請提供 `Optional one-time official USDA historical CSV intake` 的完整 log。不要自行改成寬鬆比對。即使匯入成功，也須逐期抽核個別 WASDE 原始發布、報表同一年度與單位。

**追溯性**：歷史 CSV 每期報告發布時點依 USDA 12:00 ET 常規記錄，已處理美東夏令／冬令時間。這仍不同於驗證來源實際可取得的毫秒級時間；在 timestamp 驗收完成前，不得訓練宣稱無未來資訊的交易模型。

### Windows 本機（即使 Actions 沒顯示）

在已複製好的 Repository 中，雙擊 `research_core/k3_2/run_windows.bat`，或執行：

```powershell
python research_core/k3_2/pipeline.py --output k32-review
python -m unittest discover -s research_core/k3_2/tests -v
```

K3.1 的 `research_core/k3_1/inputs/wasde_vintages.csv` 缺少時，K3.2 可以算供需表，但會明確顯示 `MISSING_K31_INPUT`，這種情況不算整體整合驗收通過。

## 4. K3.2 研究與 K3.3 的交界（應避免提前建模）

- **資料門檻（僅代表準備度）**：至少 24 次同收成年度修正、至少 3 個收成年度。資料過門檻不等於模型有效。
- **假說**：天氣影響作物生長／壓力，影響單產及產量；進口、國內消費、出口變動與預測同樣重要。
- **模型順序**：A. 同期 USDA 延續基準 / 季節性基準 → B. yield revision model（需有 as-of weekly NASS + climate）→ C. accounting stock bridge → D. 留出期資料 walk-forward → E. 是否有市場預期差異及交易成本下的增益。
- **禁止混淆**：用 WASDE 報告發布後才出現的產量、單產去預測同一份 WASDE 的期末庫存，會產生嚴重資料穿越；本版把它們用於「公布後歸因」而非「公布前預測」。
- **本期沒有可採用的 forecast model、沒有投資訊號。**

## 5. 變更與覆寫防護

所有功能隔離在 K3.2 新目錄與一個新 workflow，不修改 K3、K3.1、既有 SIGNAL Pages 或任何 production 程式。程式不使用外部 Python 依賴；選擇性網路讀取只允許 `www.usda.gov` 或 `usda.azureedge.us` 及嚴格 `/sites/default/files/documents/oce-wasde-report-data-YYYY-MM.csv` 檔案路徑。

故障時提供 Actions 的具體 step log 或 `review.json`，以方便定位，不需提供 API Key。
