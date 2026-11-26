# SIGNAL R1u｜ICI 可修訂數值跨次公告差異檢查（2026-11-26）

**類型：** `SECONDARY_TRANSCRIPTION_VS_LIVE_OFFICIAL_TABLE`。本次只讀 ICI 最新的公開聚合表與私人研究 PR #29 先前 2026-11-23 的記錄；不重抓舊檔、不改既有事前規則、不開啟交易或模型。

## 1. 比較來源及證據界限

- 舊列：本 Repository 在 2026-11-23 已提交的 `docs/research/GLOBAL_CAPITAL_FLOW_R1U_ETF_MUTUAL_FUND_DIVERGENCE_PILOT_20261123.md`，整理自 ICI 2026-11-17 ETF、2026-11-18 Combined／Mutual 的公開網頁內容。**只是先前研究人員逐項摘錄，不是保存當期原始 HTML bytes 的獨立原件。**
- 新列：本次 2026-11-26 唯讀檢查 ICI 2026-11-24 ETF 與 2026-11-25 Combined／Mutual 當前網頁表格（顯示 11/11、11/04 等先前週數據）。
- URLs：
  - Combined: https://www.ici.org/research/stats/combined_flows
  - Mutual: https://www.ici.org/research/stats/flows
  - ETF: https://www.ici.org/research/stats/etf_flows
  - MMF: https://www.ici.org/research/stats/mmf

ICI 於官方頁面註明歷史週估計可能因重分類、資料調整及報告基金數變動而修訂。以下只對照 GitHub 舊摘錄和今天官網的可見數字，不能直接把網頁變化歸因於官方「修訂原因」或證明任一版本當天的真正 HTTP 原始位元組。

## 2. 實際比對的幾個欄位

單位：**USD million**；日期均為 observation week-end，非首次發布時間。

| 股權類別及週截至 | 舊研究摘要（11/23 已存） | 11/26 官方網頁顯示 | 差額：新−舊 |
|---|---:|---:|---:|
| Combined Equity，2026-11-11 | +37,020 | +37,022 | **+2** |
| Combined Equity，2026-11-04 | +17,434 | +17,432 | **−2** |
| ETF Equity，2026-11-11 | +45,219 | +45,222 | **+3** |
| ETF Equity，2026-11-04 | +35,541 | +35,539 | **−2** |
| Mutual Fund Total Equity，2026-11-11 | −8,200 | −8,200 | 0 |
| Mutual Fund Total Equity，2026-11-04 | −18,107 | −18,107 | 0 |

### 只做可證明的算術交叉核對

- 在較新的 11/11 欄位：+45,222 − 8,200 = **+37,022** USD million，與新版 Combined +37,022 一致；11/04：+35,539 − 18,107 = **+17,432**，亦一致。
- 舊摘錄中 11/11：+45,219 − 8,200 = **+37,019**，但舊 Combined 顯示 +37,020，差 **1 USD million**；ICI 本來就允許估計值的四捨五入誤差。
- 今天網頁顯示的是**較新研究版本**，不可在測試歷史 11/18 以前的決策時將新值不加區分回填。就算差額不大，時間版本紀律仍是先決條件。

## 3. 2026-11-24 特殊 MMF 截止日（不能當下個完整樣本）

ICI 2026-11-25《Money Market Fund Assets》顯示：
- `2026-11-24` MMF 總資產 **7,978.93 USD billion**；
- `2026-11-18` 總資產 **7,976.44 USD billion**；
- 11/18→11/24 **+2.49 USD billion**；這是一段 **6 天**期間，因美國感恩節改在星期二截止。
- 不等於 `2026-11-25` 的完整星期三觀察週，也不是同一定義的股票 ETF 或共同基金流量。先保持 `NEXT_EQUITY_WEEK_NOT_PUBLISHED` / `MMF_DATE_MISMATCH_POSSIBLE`，不算 H-ICI-WRAPPER-01 第二筆完整 3 欄樣本。
- 前一個 `2026-11-18` 觀察週已完成 **1/4**，不得因此提前提升為 **2/4**。

## 4. 驗收狀態

- `ICI_PUBLIC_DISPLAY_VALUES_CROSSCHECKED=TRUE`
- `REVISION_LIKE_DIFFERENCES_BETWEEN_RESEARCH_TRANSCRIPTION_AND_CURRENT_DISPLAY=TRUE`
- `OLD_HTTP_BYTES_ARCHIVED=FALSE`
- `NEW_HTTP_BYTES_ARCHIVED=FALSE`
- `INDEPENDENT_VINTAGE_BYTE_LEVEL_REVISION_CERTIFIED=FALSE`
- `H_ICI_WRAPPER_01_FULL_MATCHED_WEEKS=1_OF_4`
- `FORWARD_WEEK_NOV25_WRAPPER=NOT_YET_AVAILABLE`
- `PIT_VERIFIED=FALSE`、`DATA_LICENSE=UNVERIFIED`、`R1_GATE0=BLOCKED`、`NO_TRADING`。

**後續最小步驟：** 等下一筆 ICI **完整**股權 ETF／Mutual／Combined 官方週數據公佈，再按原固定規則核對觀測截止日，並在同一份檔案鏈中保留新舊可見版本，不使用今天的修訂結果假裝某個舊交易日已可取得。這次發現證明「更新的官方頁面不能被直接當作舊市場時點的已知資訊」是實際風險，未證明交易可用性或資訊領先力。
