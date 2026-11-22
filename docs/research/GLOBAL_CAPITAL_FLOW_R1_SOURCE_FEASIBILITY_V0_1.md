# 視界 SIGNAL：R1 官方資料可行性與 PIT 矩陣 V0.1

日期：2026-11-22 Asia/Taipei
狀態：R1a SOURCE_METADATA_REVIEWED；R1b DATA/PIT/LICENSE NOT_TESTED；Gate 0 = BLOCKED。
範圍：唯讀官方頁面元資料核對，不下載原始數值、不執行研究模型、不改 K4/K5 預測。

## 1. 研究準則

「公開可見」不等於「在當時的投資決策截點已經可用」，也不等於「取得建模、儲存、重製或商業化授權」。
研究截點依 R0 章程為每月最後一個美股交易日 16:00 America/New_York。觀察期（observation date）、報告公布時點（release timestamp）、實際抓取時點（retrieval timestamp）、修訂版本（vintage）分別保存。
所有數值在尚未抓取來源原始 bytes 前，raw_sha256 和 actual_retrieval_utc 必須為 null。保守時間規則：如果剛好在 16:00 發布或發布的分鐘不確定，延至下一個可確認的合法截點使用。

資料狀態：
- SOURCE_CONFIRMED：官方頁面對頻率與意義有說明。
- HIST_ARCHIVE_EXISTS：有歷史公布版本入口，但尚未驗證實際每個檔案及完整歷史 PIT。
- PIT_PENDING：沒有逐期「當時已知版本」證據。
- LICENSE_PENDING：來源模型使用及/或資料再利用授權未確認。
- HOLD：不得直接納入正式預測模型。

## 2. 來源矩陣（官方頁面核對；非數值驗收）

| ID | 資料／模型用途 | 官方公布時點及已確認限制 | R1 決策 |
|---|---|---|---|
| F01 | Fed H.6 M2；M2 候選 | 每月第四個星期二通常 13:00 ET。2020 M1 口徑重劃；2026/07/28 起 M2 IRA/Keogh 扣除方法調整，季調歷史可能小幅修訂。官方 DDP 可下載當前長序列，但不能當作各期 vintage。 | P1 / PIT_PENDING |
| F02 | Fed H.15 國債長短天期殖利率；M1 | 工作日 16:15 ET 發布，晚於本研究 16:00 截點；殖利率不是實際交易報酬；不同期別須驗證各自歷史長度。 | P1 / PIT_PENDING |
| F03 | Treasury TIC 美國跨境證券交易；M2 | 約延後觀察期 1.5 個月、16:00 ET 發布；月度回修通常前三個月或一整年；交易保管地不是最終投資人所在地。官方存在按發布日期保留的月度 ZIP 歷史檔。2023 TIC S 表單停用/口徑變化需單獨處理。 | P1 / HIST_ARCHIVE_EXISTS / PIT_PENDING |
| F04 | CFTC COT 金融期貨部位；M2 | 通常週二持倉、週五 15:30 ET 公布。2026/10/27 宣布計畫於年底前每週發布兩次，但實際生效尚未驗證，不能直接套用。Legacy 歷史從 1986；Disaggregated/TFF 2006 起的部分早期分類為事後回填，無法視為當年當下已知。 | P2 / PIT_PENDING；2006–2009 回填分類 HOLD |
| F05 | ICI 共同基金淨流；M2 | 週度流量是估計，月度另計實際淨流；歷史週估計可能因基金重新分類及調整被修訂。資料不覆蓋全部股票與 ETF 市場。 | P2 / PIT_PENDING / LICENSE_PENDING |
| F06 | BIS GLI 外幣跨境信用；背景模型 | 季度發布，涵蓋三大國際貨幣的非居民非銀行借款人外幣信用；以銀行貸款/國際債券為主，並非「全球 M2」。官方允許依條款使用且提供 SDMX API；資料可回修。 | P3 / 低頻候選 / PIT_PENDING |
| F07 | NY Fed SOFR；M1 融資利率 | 約每天 08:00 ET；有同日修訂可能，官方序列起於 2018/04/02。不足 120 月訓練+60 月驗證的初步門檻；只能做近期子樣本或條件分析，不應取代主要長期基準。 | P2 / 近期子樣本 |
| F08 | FRED/ALFRED；歷史 vintage 服務 | ALFRED 提供歷史修訂版本，但日期不等於精確日內可見時刻。其現行授權明文限制以服務內容開發/訓練機器學習與軟體系統；API 另有限制儲存/歸檔。無明確權利許可前不利用 FRED/ALFRED 作模型資料管線。 | HOLD / LICENSE |
| F09 | Ken French 月度 Mkt-RF / RF；研究目標 | 美國市場超額報酬資料可追至 1926/07。2025/01 起 CRSP CIZ 來源格式變更；RF 自 2024/06 起改採 ICE BofA 1M T-bill 指數。提供部分歷史歸檔；適合研究性標籤，但不是可直接交易且已扣成本的 ETF 績效。 | P1 / exploratory label only / LICENSE_PENDING |
| F10 | State Street SPY ETF；可交易代理目標 | 發行人有 NAV 與股息再投入總報酬資訊；但 ETF 市場成交價、交易摩擦、歷史權息調整與完整可用資料權利須再驗證，發行人資訊亦有重製限制。不能用 NAV 績效替代可執行市場成交報酬。 | HOLD / tradability & license |

### 每項官方來源（完整網址）

- H.6 release: https://www.federalreserve.gov/releases/h6/
- H.6 2026 方法變更: https://www.federalreserve.gov/feeds/h6.html
- H.6 DDP: https://www.federalreserve.gov/datadownload/Choose.aspx?rel=H6
- H.15 release: https://www.federalreserve.gov/releases/h15/
- H.15 DDP: https://www.federalreserve.gov/datadownload/Choose.aspx?rel=H15
- TIC release dates & revisions: https://home.treasury.gov/data/treasury-international-capital-tic-system/release-dates-of-tic-data
- TIC official historical release ZIP archives: https://home.treasury.gov/archives-of-tic-monthly-data-releases
- TIC FAQ: https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/frequently-asked-questions-regarding/ticfaq2
- CFTC COT: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
- CFTC frequency announcement (2026/10/27): https://www.cftc.gov/PressRoom/PressReleases/9316-26
- CFTC historical backcast note: https://www.cftc.gov/MarketReports/CommitmentsofTraders/DisaggregatedExplanatoryNotes/index.htm
- ICI flows: https://www.ici.org/research/stats/flows
- BIS GLI: https://data.bis.org/topics/GLI
- BIS license: https://data.bis.org/help/legal
- NY Fed SOFR: https://www.newyorkfed.org/markets/reference-rates/sofr
- ALFRED vintage definitions: https://alfred.stlouisfed.org/help/downloaddata
- FRED license: https://fred.stlouisfed.org/legal/
- FRED 2024 terms notice: https://fred.stlouisfed.org/news/2024/06/weve-updated-our-terms-of-use-action-requested
- French research library: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
- French factor description: https://mba.tuck.dartmouth.edu/pages/faculty/Ken.French/Data_Library/f-f_factors.html
- SPY issuer: https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy

## 3. 研究結論與修正建議

1. 核心研究應先檢驗傳統金融模型 M1 與基準 M0，再檢驗資金流 M2 的增量效益；不因某資金流資料容易取得就先將其納入。
2. 原先以 FRED/ALFRED 作預設資料倉的隱含方法必須更改：在當前授權限制未釐清時，改以 Fed 原站、Treasury 原站、CFTC 原站與其他有明確使用條款的來源直接建構 PIT 研究資料。
3. TIC 有月度按發布日歷史封存，可優先核驗原始檔案並建立「當時版本」證據；不能將今日最新版與歷史交易截點混用。
4. 以 Ken French 市場因子做探索性學術標籤可降低先期研究障礙；投資經濟性報告則需另找合乎權利及可交易的含股息價格與成本，缺少即維持 BLOCKED。
5. 定義不一致、口徑重劃、低頻發布、事後補算及衍生金融資產與貨幣存量重複計數都須在公式編碼前隔離。

## 4. 下一輪 R1b（尚未開始）與 Gate 0 退出標準

進行小規模唯讀樣本核對：Fed H.15/H.6 各選 2010、2015、2020、2026 等舊公布頁樣本；TIC ZIP 選跨時期四期；對照 release timestamp / observation date / series definition / raw byte availability / use rights。嚴禁把新口徑歷史值冒充當時原版。並檢驗可合法使用的含股息結果標籤、短期國庫券現金代理及交易可執行報酬。

R1b 每筆必須有：source_id、reference_period、release_timestamp_utc、actual_retrieval_timestamp_utc（有抓到才填）、raw_sha256（有原始 bytes 才填）、vintage_id、license_status、accepted_for_model。不得虛構缺失項。

**本輪檢查統計**
- 官方來源頁面查核：10 類
- 實際下載原始研究數值位元組：0
- 原始 SHA256：null
- 完整歷史 PIT 覆蓋：未驗證
- 歷史樣本外預測／交易回測：0
- Agent 真實啟動：0
- Gate 0：BLOCKED（只是元資料可行，未完成資料與授權入模驗收）

不建立排程、模型、交易連線、額外 CI；不更動 K4/K5、main 或已凍結事前假說。