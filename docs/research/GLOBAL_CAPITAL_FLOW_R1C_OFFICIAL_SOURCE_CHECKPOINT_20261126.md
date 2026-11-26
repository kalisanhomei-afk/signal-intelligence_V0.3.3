# SIGNAL R1c｜官方來源路徑與原始位元組取得阻塞紀錄（2026-11-26）

研究範圍：只驗證聯準會 H.6 與美國財政部 TIC 的官方來源頁是否存在、資料發布時間與可用的研究前提。**沒有取得原始 HTTP response bytes**，本紀錄不授予 PIT、模型或交易資格。

## 一、官方來源實際觀察

| 來源 | 官方頁面（固定 URL） | 本次可以確認 | 本次不能證明 |
|---|---|---|---|
| Federal Reserve H.6 vintage | https://www.federalreserve.gov/releases/h6/20200827/ | 官網的 2020-08-27 版次頁，公告時間列示 16:30 ET；2020 年 7 月季節調整後 M2 為 18,327.0 billion USD。 | 未取得 HTML 原始 bytes / SHA-256；不能認證該內容在 2020 年公布當時的實際 byte vintage。 |
| Treasury TIC September 2026 | https://home.treasury.gov/news/press-releases/sb0693/ | 官網新聞稿日期 2026-11-18；公布 2026 年 9 月 TIC 淨流入 261.0 billion USD，其中私人淨流入 267.0、官方淨流出 6.0 billion USD。下一個 2026 年 10 月觀測資料預計 2026-12-15 公布。 | 未取得官方原始 ZIP；未取得原始 bytes / SHA-256；未獨立認證首次發布的準確 UTC。 |
| Treasury TIC archival index | https://home.treasury.gov/archives-of-tic-monthly-data-releases | 官網清楚區分月度觀測期間與實際報告發布日期；歷史月份列有逐次 release ZIP 項目。 | 不得假設每一個 ZIP 都仍可取得，也不得將最新修訂值視為當時發布版本。 |

### 資料時間陷阱

- 2026 年 9 月 TIC 是 **2026-11-18 才發布**，不可放入 2026 年 9、10 月任何事前模型輸入。
- 2026-12-15 尚未發布的 10 月 TIC 必須保持未知。
- 2020-08-27 H.6 的資料數值屬於其頁面所標示的版次；**目前重新讀取官方網站不能證明歷史首次發布位元組**。
- TIC 的淨流入是不同交易與金融流量口徑的合計，不可直接斷言是資金由股票流往黃金、債券或某個單一資產。

## 二、可實際驗證的阻塞

2026-11-26 本次新的隔離執行環境，以 Python urllib 嘗試對 `https://www.federalreserve.gov/releases/h6/20200827/` 做 HTTP 讀取，得到 `URLError: [Errno -3] Temporary failure in name resolution`。**本次無原始位元組、無有效 SHA-256、無可重放 raw receipt**。頁面文字透過另一路公共網頁查核確認，不可冒稱完整 HTTP 原始封存。

## 三、最小下一步

1. 沿用 PR #29 的 `scripts/capture_official_research.py`，在已有授權及網路的隔離執行環境擷取 **一份**固定的 H.6 HTML；只在真的拿到原始 bytes 時保存 SHA、取得 UTC。
2. 其次從 TIC 官網逐次 release 目錄核對 **一個真實 ZIP URL**，確認屬於目標日期、符合政府官方 host 白名單後，再擷取單一 ZIP。ZIP 成功取得之前不假裝已完成。
3. 無授權結果不得直接把上述來源用於自動模型、投資回測、訂閱授權判斷或實際交易；R1 Gate 0 維持 **BLOCKED**。
4. **不重做 PR #29 已經完成的 11/11 mock 單元測試**；只有新增程式變更時才按修改範圍安排必要驗證。

本紀錄只在私人/受控研究 Draft 分支使用，不含任何私人原始證據庫內容。No paid API / No deploy / No main merge / No trade.
