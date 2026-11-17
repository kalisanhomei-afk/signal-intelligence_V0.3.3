# SIGNAL K5.1｜公告前 EIA 原始來源取得與 V0 封存稽核

**日期：2026-11-17。狀態：`PRIOR_EIA_ORIGINAL_BYTES_CAPTURED_BEFORE_NEXT_EVENT`，未驗證 V1 或交易優勢。**

## 1. 這次真正取得的證據

GitHub Actions 於 2026-11-17T02:55:16.523381Z 開始、2026-11-17T02:55:16.841819Z 完成取得 EIA 官方 `https://ir.eia.gov/ngs/wngsr.json` 當時的原始 JSON，經 EIA 官方 `/secure/ngs/wngsr.json` 簽名轉址。為避免將短期有效的簽名 query 寫進 Repository，回執只保存來源 host/path，未保存轉址簽名。

- 原始檔：`research_core/k5/evidence/eia/EIA_WNGSR_20261113_6eb6c699b789d713_original.json`。
- 原始 byte 長度：**7,197 bytes**，含原始 UTF-8 BOM，提交後保留不做重新序列化。
- 原始 SHA-256：`6eb6c699b789d7130d3f50dbe5681e835b57bc25dd118380398169dda63fe252`。
- 來源報告文字標示 `release_date=2026-Nov-13 00:00:00`，沒有證實此欄位時區；EIA 公告網頁另外標示 **2026-11-13 10:30 ET**，不能把 JSON 無時區欄位當成實際發送 UTC。
- HTTP `Last-Modified` 聲稱 `Fri, 13 Nov 2026 14:39:08 GMT`，**甚至早於官方公告 15:30 UTC**，因此不能使用此檔案儲存時間充當首次對市場公開的時間。SHA-256 證明內容完整性，不證明原始首次公布的時間。
- 真正**捕獲 UTC** 屬於我們的 GitHub Runner 時鐘；GitHub commit 提供公開可查的公告前存在證據，但不等於獨立可信時間戳或完整的歷史更正認證。
- JSON 完整捕獲回執：`research_core/k5/evidence/eia/EIA_WNGSR_20261113_6eb6c699b789d713_receipt.json`。

## 2. 從取得的位元組重新核對的官方數值

| EIA WNGSR Lower 48 weekly working gas | 官方數值 |
|---|---:|
| 報告公布日期（EIA 網頁） | 2026-11-13 |
| 當期資料所屬週 | 2026-11-06 |
| 當期總庫存 | 3,862 Bcf |
| 前週（2026-10-30）總庫存 | 3,801 Bcf |
| 淨變動 | **+61 Bcf** |
| 五年同期平均庫存 | 3,787 Bcf |
| 一年前同期庫存 | 3,954 Bcf |

精確資料身分：`series_id=png.nw2_epg0_swo_r48_bcf.w`；需具唯一匹配、`name=total lower 48 states`、`unitsshort=bcf`，並滿足 `3862−3801=61`。不得從其他地區、其他時間或存量欄位冒充變動量。

## 3. K5 V0 持平預測**不可回填、不可改寫**

已在取得原始 JSON 之前，於 PR #23 提交：
- `cases/2026-11-19-eia-prior-week-input.json`：來源當時仍無 raw hash，欄位 `source_raw_sha256=null`，保留原狀；
- `cases/2026-11-19-eia-frozen-v0-forecast.json`：下次 11/19 EIA 週淨變動 V0 **+61 Bcf**，`source_raw_sha256=null`、`actual_next_release_net_change_bcf=null`、`market_consensus_bcf=null`，保留原狀；
- **新證據另行提交**，不可把稍後取得的原始 SHA 塞回先前的事前預測檔，否則會破壞事前凍結的版本。

11/19 預定美東 10:30（15:30 UTC）公布截至 11/13 當週的庫存淨變動。至 11/17 本次驗收，**下一次的官方數值仍尚未公布**。新事件真正公告後才能用官方原件、UTC、SHA 以及正確 WNGSR date/week 身分計算 V0 絕對誤差。

## 4. 工程保證與限制

- `research_core/k5/eia_prior_original_capture.py`：僅接收官方 JSON、核對時段與 Lower48 欄位，拒絕超出事件截止的捕獲、數值變更與檔案覆寫；不需要 API Key。
- `research_core/k5/tests/test_eia_prior_original_capture.py`：原始檔解析、時序與拒絕重複覆寫測試。
- `research_core/k5/tests/test_committed_eia_original_evidence.py`：預期 byte 長度、SHA-256、原始 BOM、報告值、取得時序及凍結預測沒有被改寫。
- 原始來源擷取 GitHub Actions [#44006444342](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/44006444342) PASS；提交原件後 [#44006599442](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/44006599442) **27/27 Python unit tests PASS**。
- 一次性擷取 job 已移除，未來 PR 日常測試只需讀取 repo 中的真實原始位元組；降低重複網路請求及來源被更新後造成的混亂。

## 5. 下一個真正的價值關卡

不要再優化 **+61 Bcf**。11/19 完成官方結果的首次事件評分，並核對**公告前**市場對同一週 `Lower48 net change` 的具名共識（若無則 NULL），不能用 11/13 的共識值代替。NOAA 需求預測要進入 V1，必須先保存早於資料預測時點的天氣 forecast vintage 及其模型有效期，不能把 11/19 後 NOAA 的實際 HDD/CDD 當成 11/17 已可用的預測。

**決策：SOURCE_RAW_INTEGRITY_PASS；NEXT_EVENT_OUTCOME_WAITING；CONSENSUS_PIT_UNVERIFIED；NOAA_FORECAST_PIT_UNVERIFIED；V1_ABSTAIN；NO_TRADING。** 不合併 PR #23／PR #22 到 `main`，不購買市場行情或下單。

## 6. 使用既有排程，避免超過自動化額度

帳號目前的自動化工作數量已達上限，沒有新增重複任務；已將原有「SIGNAL K5 天然氣首輪驗收」排程（ID `6afbc01d50f881919100ca338242f4f8`）調整為 **2026-11-19 21:00 台灣時間公告前共識查核**及 **2026-11-20 09:00 台灣時間公告後結果驗收**。此排程為嘗試取得證據，不代表成功封存；每次必須核對真正來源及 GitHub 提交。不會因事後找到有發布日期的市場評論就自動賦予獨立 PIT 認證。
