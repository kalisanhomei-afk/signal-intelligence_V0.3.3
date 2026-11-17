# SIGNAL K4.8｜第一次真正公告前 FGIS 原始報告封存（2026-11-17）

**研究狀態：`FORWARD_RAW_CAPTURE_PASS`、`SOURCE_BYTE_INTEGRITY_PASS`、`SOURCE_ORIGINAL_PUBLICATION_TIME_NOT_INDEPENDENT_PIT_CERTIFIED`、`HISTORICAL_9_YEARS_FEATURE_PIT_UNVERIFIED`、`V1_ABSTAIN`、`TRADE_ELIGIBLE=false`。**

## 1. 已完成的實際觀測

- USDA AMS FGIS 官方每週原始文字報告：`WA_GR101`，報告日期 2026-11-16；檢驗所屬週截至 2026-11-12。
- **真正已取得原始位元組的端點**：https://www.ams.usda.gov/mnreports/wa_gr101.txt （此網址為滾動更新的最新版，不能當成固定歷史版本；本次趁仍顯示 Nov16 版本時完整下載）。
- USDA My Market News **同日固定版本檔案網址**（另透過官方網站連結查得，內容欄位吻合，但 GitHub Runner 從此端點讀取逾時，未獨立核對兩端點的位元組相等）：https://mymarketnews.ams.usda.gov/filerepo/sites/default/files/3071/2026-11-16/1365706/ams_3071_00353.txt 。
- 原始報告長度：**18,499 bytes**；SHA-256：`4555c478b09d2507d042de55c6d5042e095f37b13d05185fcf889433c52802e5`。
- 原始位元組 Git Blob SHA-1：`9102c9c4e66dd0239d043a5c2c756ecb678bfffe`，GitHub Contents API 已重新核對，一致。GitHub commit（原始內容）：[`63d0bc9`](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/commit/63d0bc930285b4dbbd73a02bd0adf6b35add8db6)；取得回執 commit：[`92a68e1`](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/commit/92a68e16108c2e78e1ab91669bd7a589d96fb854)。
- 當次預測研究捕獲回執（UTC）從 `2026-11-17T02:05:28...` 完成；官方回應 `Last-Modified: Mon, 16 Nov 2026 15:56:14 GMT` 為**來源主張**，非經第三方不可竄改認證的首次發布時間；官方報告庫顯示 11/16 的報告 09:56 am，亦不可自行認定其時區和首版狀態。
- 研究標的是 2026-12-10 17:00 UTC 預定 WASDE；觀測明確早於下次公布。

### 11/16 官方原始週報摘要（公噸）

| 指標 | 數值 |
|---|---:|
| 11/12 當週玉米出口檢驗量 | 865,503 |
| 11/05 前週玉米檢驗量（本週報回列值） | 908,378 |
| 上年同期週檢驗量 | 2,066,210 |
| 2026/27 本年度累計出口檢驗量 | 12,463,023 |
| 上年同期累計出口檢驗量 | 15,851,319 |

**注意：官方原文標示「CORRECTIONS AT BOTTOM OF REPORT ARE INCLUDED IN CURRENT MARKET YEAR TO DATE」**，表示公告本身會列示先前資料的更正。這是判斷 as-of 的核心理由：不能將今天查得到的每週累計值倒填成各週首次公布時的歷史資料。

## 2. 交付的可重現檔案

- `research_core/k4/evidence/fgis/WA_GR101_20261116_official_raw.txt`：從當週原始官方來源下載的**完整原始 bytes**，保留 CRLF、報表原有段落及修訂資訊。
- `research_core/k4/evidence/fgis/WA_GR101_20261116_capture_receipt.json`：實際 URL、取得開始／結束 UTC、官方回應 headers 聲稱、來源大小 SHA-256、玉米檢驗五欄、版本侷限；不含私人 API Key。
- `research_core/k4/fgis_forward_capture.py`：只能接受兩項驗證過的端點及固定報告日期／週別；若報告已被覆蓋、數值變動或擷取時點超過 WASDE，拒絕虛假的第一次原始版封存。
- `research_core/k4/tests/test_committed_fgis_forward_evidence.py`：每次 PR CI 都從 GitHub 已提交的公開 USDA 原始文字 bytes 重算 SHA、確認內容與回執，驗證取得時間先於 WASDE，拒絕宣稱已獨立 PIT 認證。
- 原始資料首筆捕獲 GitHub Actions [#44000050793](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/44000050793)，固定版本優先測試 [#44000118410](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/44000118410)，實際 raw 檔案已進入 GitHub 研究分支。

## 3. 這次完成了什麼／沒有完成什麼

- **完成**：第一個具有真實原始報告位元組、觀察 UTC 與可再驗證 SHA-256，且早於 12 月 WASDE 的 FGIS forward snapshot。即使官方 `mnreports` 後續更新，GitHub 仍留原始內容。
- **未完成**：2017–2025 各週的第一版 FGIS 取得 UTC、歷史更正完整鏈；公告前市場共識仍尚未封存；不能據此推算經校準的 `H-CORN-001` V1 點預測或交易優勢。
- **處理原則**：保存固定歷史網址與 raw 對照；日期型 URL 不保證官方不可竄改，GitHub commit timestamp 也不是獨立第三方的法律時間證明。保留 `PIT_UNVERIFIED`。
- **下一個最小事件**：2026/11/23 公布 FGIS 週報後，在 2026/11/24 再實際捕獲當週 raw、驗證 SHA 與 UTC，直到 12/10 WASDE 前至少形成三次額外真實前瞻觀測。每週可用於研究，不能先宣稱足夠訓練 alpha 模型。

**保持研究分支 PR #22 Draft，不合併 `main`，不購買 Databento、不下單。**
