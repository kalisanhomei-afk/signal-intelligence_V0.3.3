# SIGNAL R1q | BIL 2008 配息日期錯置：原始來源搜尋及獨立年度績效錨點

**日期**：2026-11-26（Asia/Taipei）。**範圍**：只為既有 2008-03-03 BIL 異常找發行人/SEC contemporaneous 原件，或新增不需購買資料的可重現性驗證錨點；不重新執行已完成的 28 項 SPY/BIL NAV 績效比較，不重新下載三個原始工作簿，不變更來源數值、不進行模型回測。

## 1. 保留原始異常，不能自行改值

已驗收 State Street 歷史配息 XLSX 中，BIL ex-date **2008-03-03** 的 record **2008-02-05**、payable **2008-02-11**，在時間上發生在 ex-date 之前；與 2008-02-01 BIL 分配列的 record/payable 日期相同。此情況是 **SOURCE_DOCUMENT_INTERNAL_CONFLICT**；不得因推測為複製錯誤而改寫 issuer 原始檔。

公開**次級**網站（如 https://www.financecharts.com/etfs/BIL/dividends/dividends 、https://www.marketlog.com/symbol/bil-arcx/dividends 、https://www.slickcharts.com/symbol/BIL/dividend ）一致列出同一 2008-03-03 ex-date 的 **2008-03-05 record** 和／或 **2008-03-11 payable**。但三個網站可能來自同一資料提供商，且今日顯示無法證明 2008 年當期公告來源及其原始位元組；**三網站一致不等於三個獨立一手證據**。

**本輪針對 2008-03-03/05/11 BIL 在 State Street 與 SEC 一手網站進行定向來源搜尋，沒有查得包含這三日期、且可驗證為當次 BIL 原始宣告之公告。** 保持 `PRIMARY_2008_03_BIL_PAYOUT_NOTICE=NOT_LOCATED`，不能把網站列示候選改成發行人認證的勘誤。

## 2. 新的正式年度績效錨點（不等於配息日期正式勘誤）

發現 2015 與 2018 年 SEC 基金公告存檔包含 SPDR Barclays/Bloomberg 1-3 Month T-Bill ETF（BIL）**2008 calendar-year annual return 1.77%**。這個 2008 年度績效對比有助於未來檢查早年含息 NAV 複算是否出現明顯偏差，但此處**尚未執行 2008 年完整 NAV 報酬重算**，也尚未從二手搜尋結果自行推定 1.77% 必然對應哪個具體 before/after-tax 或 NAV/market 欄位：正式作數值驗收前必須打開該 SEC 文件的表格欄名及 footnote，確認申報人的基金級 return 類型。

官方存檔：
- https://www.sec.gov/Archives/edgar/data/1064642/000119312515383378/R271.htm
- https://www.sec.gov/Archives/edgar/data/1064642/000119312518331964/R313.htm

**證據強度**：SEC 官方存檔之搜尋索引可確認 2008 return cell 與 BIL 基金名稱之關聯；本次打開 SEC HTML 時網頁工具回報 cache miss，**未直接檢視頁面完整欄位與附註**。因此先標記 `SEC_2008_ANNUAL_RETURN=SEARCH_INDEX_CANDIDATE`，不能將其作為獨立驗收 PASS 或直接覆寫本地試算。

## 3. 停止規則

- 2008-03-03 付款日保持 `QUARANTINE_SOURCE_DATE_CONFLICT`。若用戶要求完整 2007 起 NAV payable-date reinvestment 研究，這一筆仍屬必要待證項目，不能以猜測補齊。
- 現有 2026 H1 三段及 28 項 issuer NAV scorecard 已驗收，不要為了等 2008 改錯重算同一結果。
- 如取得 issuer 2008 原始分配公告或 SEC 可核實基金年報表格，僅做**一次**日期交叉核對及 2008 年度錨點方法對照；如無授權及交易價格，正式 R2 仍保持 NO-GO。
- 本次沒有任何原始工作簿/完整配息資料集公開提交 GitHub，亦沒有付費、API、CI 手動重新執行、發信或交易。

`SOURCE_2008_03_PAYDATE_PRIMARY=BLOCKED` · `SEC_2008_RETURN=UNCONFIRMED_CANDIDATE` · `R1_GATE0=BLOCKED` · `R2_NOT_STARTED` · `NO_TRADING`
