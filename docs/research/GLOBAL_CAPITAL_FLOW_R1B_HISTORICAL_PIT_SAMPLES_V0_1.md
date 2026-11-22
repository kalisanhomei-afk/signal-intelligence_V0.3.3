# 視界 SIGNAL｜R1b 歷史發布版本抽查與 PIT 風險證據 V0.1

**2026-11-22（Asia/Taipei）**。研究級別：`HISTORICAL_PUBLISHED_PAGE_SAMPLES`；非完整 PIT 連續序列。此文件是 R1a（Draft PR #27）的延伸，不動 R0、K4、K5 或正式部署。

## 摘要與判決
已直接在官方歷史網頁核對 **H.6 2015 / 2020 / 2021 / 2026**、**TIC 2010 / 2015 / 2020 / 2025** 的歷史發布日期、部分頁面公布時間和其所展示的數值；亦核對了 H.15 當前發布時間、2016 年歷史月平均發布制度變化及 Ken French 歷史報酬重編規則。

**R1b 局部完成：PUBLISHED_PAGE_CHECK=PASS；RAW_BYTES/PERIODIC_VINTAGE/PIT_COVERAGE/LICENSE/TRADABLE_TOTAL_RETURN=BLOCKED。Gate 0 仍 BLOCKED。** 已閱讀官方歷史 HTML 頁面，不能自稱已取得原始檔案的 bytes；無原始 SHA-256。官方網頁的可讀文字快照也不等於已取得當年各期可校驗的原始檔。

## A. Fed H.6：實際不同公布時段（已核對官方舊版）

| 官方發布頁 | 實際頁面宣告 | 證據 | 判斷 |
|---|---|---|---|
| 2015-01-22 | 16:30 EST；年度修訂 | https://www.federalreserve.gov/releases/h6/20150122/ | 在 16:00 截點當日**不可用** |
| 2020-08-27 | 16:30 ET；舊制週報 | https://www.federalreserve.gov/releases/h6/20200827/ | 當日 16:00 **不可用** |
| 2021-02-11 | 16:30 ET；**最後一次週報**，宣告 2021-02-23 第一次月報為 13:00 | https://www.federalreserve.gov/releases/h6/20210211/ | 明確制度轉換 |
| 2021-03-23 | 13:00 ET；月報含季節調整修訂表 | https://www.federalreserve.gov/releases/h6/20210323/ | 當日 16:00 前可能可用，但仍需確認原始發布時點及實際可用性 |
| 2026-10-27 | 最新 H.6 月報（主頁公告第四個週二通常 13:00 ET） | https://www.federalreserve.gov/releases/h6/20261027/ + https://www.federalreserve.gov/releases/h6/ | 不可倒套舊週報 |

### 實際數值的 vintage 範例：2020/07 季調 M2（單位：十億美元）
- **2020-08-27 當時發布頁**：**18,327.0**（H.6 Table 1，July 2020 SA M2）https://www.federalreserve.gov/releases/h6/20200827/
- **2021-02-11 後續公布頁**：**18,328.8**（同一觀察月份 July 2020 SA M2）https://www.federalreserve.gov/releases/h6/20210211/
- **2021-03-23 再修訂版本**：**18,321.5**（Appendix Table 2 Revised M2，July 2020）https://www.federalreserve.gov/releases/h6/20210323/
  - 同一 2021-03-23 表格中「Old M2」**18,330.3** 是該次修訂的舊序列比較值，不必等於 2021-02-11 先前頁面中的 18,328.8，因為可能另有中間修訂。不可把「Old」誤解為第一次公布值。

本例不表示經濟實際上發生 1.8/7.3 十億美元的貨幣移轉；這只是同一觀測期統計資料在不同公布版本下的差異。回測若把 2021/03 的數據套入 2020/08 以前就有後見之明。**版本證據 = 部分頁面證據；不是歷史連續資料可驗收。**

## B. Treasury TIC：發布日與資料所屬月份分離

| reference period | official release | 可核對的當次官方來源 | 注意 |
|---|---|---|---|
| 2010-04 | **2010-06-15** | https://home.treasury.gov/news/press-releases/tg744 | 2014 前的 TIC 通常 09:00 ET 公布；該頁僅提供日期，不能把政策習慣時間冒充該次分鐘級時間戳。|
| 2015-09 | **2015-11-17** | https://home.treasury.gov/news/press-releases/jl0277 | 2014-09-16 起月度 TIC 一般 16:00 ET 公布，正好等於本研究 16:00 截點，不能假定立即可執行。|
| 2020-01 | **2020-03-16** | https://home.treasury.gov/news/press-releases/sm943 | 不能因 reference month 為 January 就在 2020-01 的訊號內使用。|
| 2025-08 | **2025-11-18**（受聯邦政府部分停擺延遲） | https://home.treasury.gov/news/press-releases/sb0317 | 檔案索引仍有 `10/17/2025 TIC Data for August 2025 (released 11-18-2025)` 的原定日期欄；必須使用真實日期。當次新聞稿也明說部分 August 數據已修訂，原始 August 版本存於檔案。|
| 2025-09 | **2025-11-18**（同日公布） | https://home.treasury.gov/news/press-releases/sb0317 | 因停擺造成不尋常雙月發布；使用固定 1.5 月機械延遲會錯誤。|

TIC 官方條款與時刻規則：https://home.treasury.gov/data/treasury-international-capital-tic-system/release-dates-of-tic-data ：**2014-09-16 起**月度 TIC 通常 16:00 ET，之前通常 09:00 ET。自 2021-03-15 起證券持有資料延遲定義改變；前三月、前一年與重大更久修訂規則須分別處理。官方歷史 ZIP 按「實際發布版本」封存：https://home.treasury.gov/archives-of-tic-monthly-data-releases ，索引含 2006–2026 歷史，並說明 **2023-04-17 前後檔案格式不同**。此輪沒有抓取 ZIP 或逐檔解壓，故只有「封存存在的官方文字確認」，沒有 ZIP 原始證據核驗。

### 時間來源標記
新聞稿能核對的當次**日期**與來源中公布的制度**一般時刻**要分開標示：
- `release_date_verified=true`（所選官方新聞稿頁）。
- `exact_per_release_utc_minute_verified=false`，除非該次官方頁有時刻明示；不能拿制度規則直接填成當次實測 timestamp。
- `retrieved_raw_at_utc=null`、`raw_sha256=null`：沒有取得原始 bytes，禁止自行合成。

## C. Fed H.15 與研究結果標籤（負面發現）
- H.15 當前一般工作日 16:15 ET，晚於 16:00 信號；官方：https://www.federalreserve.gov/releases/h15/ 。
- 官方 H.15 Technical Q&A 確認 2016-11-03 起月平均由「每月結束後首個週一」改為「首個營業日」；且 2016-10-11 起不再更新部分利率項目：https://www.federalreserve.gov/releases/h15/h15_technical_qa.htm 。
- 嘗試存取 H.15 的舊日期型網頁（例如 `/releases/h15/20151231/`、`/releases/h15/20200827/`）未成功；**不能聲稱已恢復舊版 H.15 原始發布值**。不得以今日 DDP 回填值替代。
- Ken French 研究庫：https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html 明示市場報酬構造方法與原始 CRSP 資料可能修訂，2012 年市場基準改寫、2015 年股票資料修訂、2025 年 CIZ 計算方法切換；只有部分每年 7 月截點歷史因子封存，未證明每月 PIT。這是研究指標，**不是經濟性回測所需的可成交 ETF 淨報酬**。
- 股市與現金代理：**授權、逐期可交易總報酬、分紅時點、交易成本與可靠行情來源均未完成**；本輪不開始 M0/M1/M2。

## D. 接下來需要的最小工作（不擴大系統）
1. 先解決原始資料取得：在具官方網站連線與合法使用權的執行環境，選 H.6 2020-08-27 與 2021-03-23 的原始 HTML/XML 各一份、TIC 2010-06-15 / 2015-11-17 / 2020-03-16 / 2025-11-18 原始版本 ZIP 各一份，才可計算 bytes SHA256、實際 UTC、驗證內容欄位；若 zip 過大先選兩份。當前 web 純文字讀取不保證原始位元組，不能以網頁可讀內容假裝原檔。
2. 如果資料端點或版權無法滿足，應優先**縮小到官方 H.6 + TIC** 或替代使用來源，而非改成 FRED/ALFRED 繞過其授權限制。
3. 設計不可變 `source_date / observation_period / publish_utc_exact_or_date_only / raw_captured_utc / sha / vintage / license / accepted` schema。未確認精確發布分鐘時強制日期後保守 lag。
4. 進入 R2 前，先凍結合法的 **股票含息總報酬 / 短期現金含息總報酬**、交易價格／成本與 120+60 月樣本可用性。無此證據 Gate 0 維持 BLOCKED。

## E. 實際執行紀錄與限制
- 官方頁面可讀歷史記錄：H.6 四個時間段及 M2 三個版本、TIC 四個年月代表性案例與 2025 關閉延後案例、H.15 技術說明、Ken French 方法說明。
- 網頁正文核對 = **WEB_TEXT_VERIFIED**；原始 bytes = **NOT_ACQUIRED**。測試從容器直接存取 Fed HTML 下載遭到拒絕，容器一般網路連線也失敗；沒有可用的位元組資料，因此沒有 sha256。禁止回填 hash。
- 結果：`R1b_PARTIAL`；`GATE0_BLOCKED`；`PIT_COMPLETE=false`；`LICENSE_CLEAR=false`；`TRADABLE_RETURN_VERIFIED=false`；`BACKTEST_RUNS=0`；`AGENTS_LAUNCHED=0`。
- 本次僅建立文件化候選研究證據，未執行真實交易、部署、付費 API、模型訓練；無新 GitHub 手動 Workflow 執行。因本文件 PR 是從既有 R1a 分支建立，GitHub **可能自動觸發現有的非部署專案連續性 CI**，該 CI 不等於資料 PIT 或模型驗收。
