# SIGNAL R1d｜資料使用權與可交易總報酬資料 Gate 0 審查（2026-11-22）

**狀態：PUBLIC_LICENSE_AND_SOURCE_LINKS_REVIEWED / DATA_FILE_NOT_CAPTURED / FULL_GATE0_BLOCKED**
研究分支：research/global-capital-flow-r1c-capture-pilot-20261122；更新既有 Draft PR #29，依附 R1b #28、R1a #27、R0 #26。沒有更動研究預註冊主要假說，沒有訂閱、交易、模型回測或部署。

## 1. 本輪關鍵決策

**首選探索方向：SPY (美股) − BIL (1–3月美國短期國庫券 ETF)。** 不代表建議買入。選同一發行人有利於降低不同基金資料處理差異，且兩檔是可上市交易的投資工具。SPY 成立 1993-01-22；BIL 成立 2007-05-25。若兩檔自 2007-06 至 2026-10 均有資料，最多約 233 個完整月的**理論共同樣本**；這只是日曆算術，**不是實際資料覆蓋驗證**，也尚未證明滿足 120 月訓練 + 60 月樣本外有效值門檻。

**不先購買行情。** 發現 State Street 官方兩個可點選的 NAV History XLSX 下載入口（下列精確 URL），但此環境直接下載未成功，檔案列數、欄位、歷史涵蓋期間、股息及授權均未核實。官網顯示 NAV 與 Market Value **分別**為不同報酬系列，不能拿 NAV 報酬冒充下一交易日成交後的績效。先做零成本兩檔 XLSX 的**有限欄位與期間覆蓋查核**；再用市場行情來源驗證買賣執行與股息計算；無商業使用權前不製作自動長期資料庫。

## 2. 權利、資料與可交易性矩陣

| 候選來源 / 角色 | 真正核對的官方公開證據 | 已確認能做什麼 | 不可假定、需補證據 | Gate 0 |
|---|---|---|---|---|
| **NY Fed SOFR 原站**；M1 候選融資因子 | https://www.newyorkfed.org/privacy/termsofuse.html ，Permissible Use 原則上明示允許 personal **or business** use、download/store/derivatives，附 attribution、不得誤認官方背書；Reference Rates 有專用 disclaimer；SOFR 有 DTCC 第三方輸入來源 | **GENERAL_SOURCE_LICENSE_POSITIVE_WITH_CONDITIONS**（限符合網站及各資料頁專用條款） | 不等於每份資料都無第三方限制；2018-04-02 才開始 SOFR，不能構成 2007 起長回測的唯一傳統融資因子；日內修訂與 PIT 尚未驗證 | RIGHTS_CONDITIONAL / PIT_PENDING |
| **Treasury TIC 原站**；M2 候選資金流 | 官方 2020-03-16 歷史 ZIP 指定 CSV 值 +122883 million 與當次新聞稿 +122.9 billion 對應及兩組加總均 **PASS_EXTERNAL_REPORT**，既有 PR #29 已留證；https://home.treasury.gov/archives-of-tic-monthly-data-releases | 原始發布頁、公告日期及一個具體欄位能重現 | 同時代 ZIP 全檔 PIT、部分 ZIP 成員 2020-04-10 延後時間戳、資料回修、在台灣商業／系統發佈再利用及可能第三方權利須查；美國聯邦政府工作一般著作權原則**不能代替**逐資料權利核對 | VALUE_MATCH_PASS / FULL_PIT_BLOCKED / LICENSE_REVIEW |
| **Fed H.6 / H.15 原站**；M1/M2 | https://www.federalreserve.gov/releases/h6/ ; https://www.federalreserve.gov/releases/h15/ | 歷史發布頁存在，R1b 確認 H.6 週報->月報 2021 時點差；Antigravity H.6 一份現時 bytes 回報 | 不是各時點 180 月 vintage coverage；Fed H.15 16:15 ET 晚於 16:00 截點；各資料使用權需原站核對而非引用 FRED 條款 | PIT_PENDING / LICENSE_REVIEW |
| **FRED/ALFRED** 資料聚合與 vintage | https://fred.stlouisfed.org/legal/ 明確限制利用 FRED Services/Content 開發或訓練 machine learning / software，API 也限制存取、儲存及歸檔 | 讀取條款及比對 metadata 的研究基礎 | **無許可不可**直接作模型特徵資料擷取、計算引擎儲存或 AI 模型輸入；改用原始統計機關，不是繞過原資料的其他附加權利 | **HOLD_RIGHTS** |
| **SPY** 可交易股票代理 | https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy ；成立 1993-01-22；官方有 ETF Historical Distributions、NAV History、月度 **NAV & Market Value performance**，後者用 4pm bid/ask midpoint，非實際下一時段成交價 | 適合作為**候選**美股總報酬標籤與可交易市場標的 | NAV History XLSX 可點選，但無實際檔案檢視；尚未確認可用 2007–2026 長度、全日收盤/開盤與配息序列、上市交易實際價格/PIT、價格/配息用途授權 | **CANDIDATE / NOT_ELIGIBLE** |
| **BIL** 短期國庫券 ETF 代理 | https://www.ssga.com/us/en/individual/etfs/state-street-spdr-bloomberg-1-3-month-t-bill-etf-bil ；成立 2007-05-25；持有 1–3 month U.S. Treasury bills，官方 NAV、Market Value（bid/ask midpoint）與配息入口，expense ratio 0.1352%（頁面時間戳為 2026-11 的**現行**值，不能倒灌舊費率） | 可上市交易的**美元短期國庫券部位代理**，但不是零風險或保證本金的存款現金 | 不等同「cash」原始定義或直接 T-bill 滾動投資；NAV/股息/成交價、資料完整性與授權待驗；2007-05 成立使樣本下界受限 | **CANDIDATE / NOT_ELIGIBLE** |
| **State Street 官網權利** | https://www.ssga.com/us/en/footer/terms-and-conditions §copyright/data use：可留個人印出、合理數量企業內部頁面複製；網站資料複製、衍生、商用、內部長期資料庫和第三方供應商資料用途有額外限制，不提供無條件授權 | 可在網站閱讀與進行有限人工來源審核 | **不要將可下載 XLSX 誤認為可以任意批次擷取、編成商業訊號或公開再散播**；須確認公司內研究建模、原始資料保留、重算和外部商業化的具體權利或購買合適資料授權 | **RIGHTS_PENDING / NO_BULK_INGEST** |
| **EODHD Commercial Internal Use**（備用行情授權） | https://eodhd.com/commercial-pricing ：截至本輪官方表列 Internal use 約 **US$399/月**（年繳折算約 US$332.50/月），企業伺服器下載選項另 +US$200/月；宣稱 EOD ETF EOD、配息與拆股歷史深度 30+ 年但依個別資料而異 | 可作**有成本且有商業方案**的替代選項 | **未採購、未確認 SPY/BIL 個別資料期間/精度/執行價格及授權附約**。單純為兩個 ETF 研究，現階段不建議花此固定月費 | **DEFER_PAID** |

### 官方兩檔 NAV History 可點擊 XLSX URL（已由發行人頁面連結解析取得）

- **SPY**: https://www.ssga.com/library-content/products/fund-data/etfs/us/navhist-us-en-spy.xlsx
- **BIL**: https://www.ssga.com/library-content/products/fund-data/etfs/us/navhist-us-en-bil.xlsx
- **產品資料 workbook**（全產品彙總，**不得當成歷史日 NAV**）：https://www.ssga.com/library-content/products/fund-data/etfs/us/spdr-product-data-us-en.xlsx

本輪嘗試在 ChatGPT 原始檔執行環境下載 SPY 官方 XLSX **失敗**（network/download failure），故 **未**開檔、未得原始位元組/SHA、未驗證欄名/起訖日期/缺值比例；沒有把下載連結存在誤寫成資料已通過 Gate 0。

## 3. 股市與現金可執行總報酬的定義（尚待資料）

至少需在批准來源後固定：
1. 同一天的 **SPY、BIL next executable trade** 市場價（下一交易時段的實際可成交價代理；例如下一交易日開盤，需查實際行情），不得在看完 16:00 收盤價後又用同一日收盤價成交。
2. 除權日前後拆分/配息修正與當期持有資格、配息投入時間規則、基金費用是否已在 NAV 內，不可重複扣除。
3. 適用帳戶交易佣金、保守買賣價差及滑價，BIL 不能視為 0% 交易風險、不能把 1–3 月 T-bill 指數報酬當成 ETF 可得收益。
4. 2007-06–2026-10 **最多約 233 個完整月** 是日曆候選，正式樣本須至少 120 個月訓練 + 60 個月不重疊獨立樣本外；若可用月數不足就縮小範圍並標記有限驗證，禁止調整年份以美化效果。
5. M0/M1/M2 模型使用同一共同資料樣本、完全相同持有期及時間滯後；M2 額外加入經 PIT 通過的資料，不能以最新修訂 M2/TIC 回填當年。

## 4. 預設路線與費用 Gate（節省時間/避免過度工程）

- **目前最佳路線**：官方 TIC/H.6 研究原始發行人與明確授權的 NY Fed 資料；美股及短券投資代理先做 State Street SPY/BIL **僅兩檔** XLSX 來源元資料核對，避免擴張至其他市場或購買昂貴資料。
- **短期下一個可驗證動作**：在已能對外連線的 Antigravity 工作環境，對 **兩份官方 NAV History XLSX 只做一次授權允許範圍的來源/結構驗證**（HTTP、檔案原始 bytes SHA256、第一與最後有效日期、欄名、行數、實際涵蓋年數、是否含 Market/Closing 或只有 NAV；資料本身不要提交 GitHub）。如果網站提示無法下載/限權，記錄 BLOCKED。
- **若兩檔只有 NAV**，其結果只可作研究性 NAV total-return 來源候選；不能作實際可成交報酬證據。保留下一階段行情/股息資料授權判定，先核對成本可控的授權方案，避免自動導入月費 US$399 的企業方案。
- **明確停止條件**：兩份 XLSX 缺少必要歷史期間、授權不允許所需目的，或沒有可交易價格/除權息證據 → Gate 0 繼續 BLOCKED；不重跑 R1c 8 項測試、不重抓舊 TIC ZIP、不先訓練模型。
- 使用權限制與資料引用風險屬研究合規問題，本文件不是法律意見；正式商業資料用途需要授權文件或法律確認。

## 5. 事實與執行紀錄

- **完成**：來源網址/官方產品上市日期/收益顯示定義/公開授權條款/商業供應商公開價核查；資料用途風險分級；兩檔研究代理建議。
- **未完成**：原始 SPY/BIL XLSX 檔案擷取、真實每月總報酬、日開盤價、配息資料完整性及權利、資料 PIT 逐月追溯；完整 Gate 0；M0/M1/M2；正式部署或紙上交易。
- **真實 AI Agent 啟動**：無；沒有將規劃中的多角色寫成已經在執行。
- **CI**：本文件僅修改研究文件/狀態檔，任何自動觸發 GitHub Project continuity 工作流並不構成真正資料或研究模型驗收；不手動觸發 Actions。
