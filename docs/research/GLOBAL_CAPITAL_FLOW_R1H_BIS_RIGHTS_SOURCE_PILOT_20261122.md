# SIGNAL R1h｜從授權不明的研究因子轉為可用條款明確的官方全球流動性資料

> **2026-11-23 R1i 後續實測（取代下文尚未擷取的舊狀態）：**使用者提供 Antigravity 執行紀錄：BIS 官方 GLI ZIP HTTP 200，原始 ZIP SHA-256 由 Antigravity 回報為 `87c8b99cca6043ae7737fb9c15159ad5920d0fdf260e9c9a68d03cec7cb95899`，完成擷取 UTC `2026-11-23T00:40:25.162908Z`；內含 21 欄、24,603 列，已定位 E2.1 2000-Q1..2026-Q2 共 106 季資料。**CSV 結構與 2026-Q2 分項加總 PASS，但歷史 PIT/模型 Gate 0 BLOCKED。**詳見 `GLOBAL_CAPITAL_FLOW_R1I_BIS_RECEIPT_AND_HYPOTHESIS_20261123.md` 和相應 R1i JSON；原檔未交給 ChatGPT、未提交 GitHub。

日期：2026-11-22 Asia/Taipei（以下為試點前的歷史狀態）。**狀態：OFFICIAL_TERMS_AND_SOURCE_LINKS_VERIFIED / BIS_RAW_CAPTURE_BLOCKED_IN_CHATGPT / PIT_NOT_VERIFIED / GATE0_BLOCKED。**

本文件是既有 Draft PR #29 的研究來源決策；不是資料流或真實回測已完成。Kenneth French 企業資料權利在 R1g 後仍無明確許可，依 `AGENTS.md` 對同一阻塞超過兩輪應改變方法，本輪轉為 BIS GLI，**不要求重新下載 TIC/SSGA、不購買 Tiingo、也不啟動多 Agent 假分工**。

## 1. 重大進展：三個直接來源的實際使用權比較

| 原始機構 | 官方條款已明示 | 本輪最小可用研究用途 | 未放行原因 |
|---|---|---|---|
| **BIS** | https://data.bis.org/help/legal ：BIS 統計的使用在滿足六項條件時不受其他用途類型限制，含註明 BIS、禁止暗示背書、翻譯註記、若納入商業出版或產品不得因此向其訂戶/使用者增收費用，以及無保證/非投資建議。API 另有終止、版本及 IP 限制。 | **首選**追蹤外幣信用（美元、歐元、日圓）與國際融資條件，明確採用原站官方統計及必要引用。 | **有條件許可不等於**任意商業轉售、額外收費、資料正確性、歷史 PIT 或投資模型資格。需保留法條適用及使用方式。 |
| **Fed Board 原站 H.6** | https://www.federalreserve.gov/disclaimer.htm ：除非另有標示，Board 網站資訊為公共領域可複製/散布，須引述 Board；第三方/非 Board 內容須另確認。 | 美國貨幣、流動性與銀行信用候選；不用 FRED API 管制服務。 | 發表版本/修訂日期、PIT 和跨平台權利須再核對；本專案 R1c H.6 一個樣本不構成完整 PIT。 |
| **World Bank WDI** | https://www.worldbank.org/ext/en/legal/terms-conditions/datasets 與 WDI catalogue https://datacatalog.worldbank.org/infrastructure-data/search/dataset/0037712/world-development-indicators ：WDI dataset 標示 CC BY 4.0，原則可用於商業用途，須 attribution，第三方 indicator 可能例外且不可以暗示背書。 | 跨國長期人口、貿易、GDP、資本形成等**年度背景**變數。 | WDI 年度數據不是月度資金流，不能滿足股票下月報酬的必要標籤；各 indicator 權利、時點及修訂另驗。 |

**不採用的捷徑**：不能以 World Bank WDI 的 CC BY 4.0 遮蔽每條可能第三方原始權利，也不能以 BIS 資料 API 存在直接宣稱完整歷史免費 PIT。FRED/ALFRED 的特殊服務條款不因這些原站使用許可而改變。

## 2. 第一個具體候選：BIS E2.1（美元計價非銀行借款人信用）

- 官方定義與資料頁：https://data.bis.org/topics/GLI
- E2.1 Table：https://data.bis.org/topics/GLI/tables-and-dashboards/BIS,GLI_E2_1,1.0
- 官方 ZIP 下載列表：https://data.bis.org/bulkdownload
- 官方 `CSV, flat` 連結實際指向：**https://data.bis.org/static/bulk/WS_GLI_csv_flat.zip**（由官方 bulk download 表內超連結直接取得，不猜測檔名）。
- BIS SDMX API 官方說明：https://stats.bis.org/api-doc/v2/
- 2026-11-22 官方 GLI 頁核對：**上一份發布日期 2026-10-29，下一次排定 2026-12-07**。日期僅是官方頁所列，**逐件 UTC 分秒未知**；不得預先填 12 月內容。
- 資料頻率為 **quarterly, non-seasonally adjusted**；追蹤銀行放款及國際債券對非銀行借款人的**存量信用**及成長，美元/歐元/日圓。E2.1「Borrowers outside the United States」尤其與境外美元信用相關。**不是全球 M2、不是觀測到的股票／黃金資金去向，也不是月度直接淨現金流。**
- 官方說明：GLI 上游為 BIS 銀行地理統計及國際債券統計，投入資料修訂會造成歷史 GLI 修訂；當期最新序列不可直接當成過去每一個月投資訊號已知版本。

### 真實 ZIP 的取得狀態

本次從官方頁面核對到 ZIP 真正的點擊 URL；但 ChatGPT 工作容器對該檔的單次下載**失敗**，並未取得檔案。故資料實測：
`raw_sha256=null`、`retrieved_utc=null`、`extracted_series_schema=NOT_INSPECTED`、`BIS_OFFICIAL_RAW_CAPTURE=BLOCKED_IN_THIS_RUNTIME`。
不能用超連結可見或網頁索引顯示 release date 代替位元組已取得。

### 下一個最小一次性外部動作（可由已有 Antigravity 網路環境執行）

1. 唯讀確認 BIS 官方 bulk CSV flat 是上述網址，**下載一次**至既有 Git 忽略的 `research_raw/`。記錄 UTC 開始/完成、HTTP code、最終 URL、Content-Type/Length/Last-Modified/ETag、真實 bytes 大小、SHA-256、ZIP member names+declared sizes+dates，不把 raw 寫進 GitHub。
2. **只讀取會員目錄/CSV header**，先定位 E2.1 (USD credit to nonbank borrowers outside US) 的 series identifiers, units, frequency, publication reference。若 CSV/ZIP 內容過大、格式不清或官方來源不符，停止標記 BLOCKED；不要自行猜列或製造數值。
3. 本次目的僅為 **source_format_and_rights_pilot**；不需擷取整份股市資料、任何交易、付費 API、R2 模型，或一次下載多種官方資料。
4. 必須連同 BIS attribution 與合約條件記錄到 receipt。即使下載成功，也需另有 release-vintage 時點證據才可能提升 PIT 狀態。
5. 不重跑 R1c 舊測試，不擴張 SSGA/Tiingo，禁止人工觸發非必要 GitHub Actions。

## 3. 三種已完成與未完成的層級

- **SOURCE_DISCOVERY DONE**：BIS E2.1 原站表單、GLI 分析定義、單一官方 ZIP URL、公開條款與 API 入口已取得；Fed 原站公共領域條款、WDI dataset CC BY 4.0 與例外已比對。
- **PIT / RAW BLOCKED**：BIS 原始 ZIP 尚未到此執行環境；未取得原始數值、可復現 bytes hash、逐期歷史版本、時間精度、模型預測樣本。
- **FORMAL GATE0 BLOCKED**：尚缺可交易股票相對現金的合法總報酬標籤、資金流量完整 PIT 及正式授權矩陣。R1g 合成資料防呆程式保留，**不需要重寫**；既有 TIC 單欄值一致性 PASS 不重做。

下一輪完成單一 BIS ZIP schema 試點後，再選擇一個合法且可用歷史版本的 GLI 原始資料序列，**先做一張經濟性趨勢與因果假說卡**（明示為現時封存視圖，不虛構投資 alpha），避免又花數週建立只有授權文件的架構。

GitHub 交付：本文件與 `docs/research/global_capital_flow_r1h_official_rights_matrix_20261122.json`、`docs/CURRENT_STATUS.md`。無主線修改、無合併、無付費、無真實數值資料納入 Git。
