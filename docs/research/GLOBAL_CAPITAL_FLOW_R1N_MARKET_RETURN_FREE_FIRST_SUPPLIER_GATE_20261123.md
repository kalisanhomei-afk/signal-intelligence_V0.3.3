# SIGNAL R1n｜SPY/BIL 可交易總報酬：零費用來源與企業授權否決式審核（2026-11-23）

**狀態：OFFICIAL_PUBLIC_PRODUCT_TERMS_REVIEWED / TWELVE_BASIC_FREE_CANDIDATE_IDENTIFIED / COMPLETE_TOTAL_RETURN_NOT_CLEARED / GATE0_BLOCKED。** 本次研究在已有 Draft PR #29，繼承 R0/R1d/R1e/R1f 採購與研究門檻。不註冊新帳戶、不下載行情、不訂閱、不執行回測或交易。不重做 State Street NAV XLSX、BIS、TIC 既有實測。

## 1. 本輪決策實質進展

**發現重要的零月費候選：Twelve Data 商業頁 Basic = US$0／月。** 官方列出「Internal non-display usage」、美國股／ETF market data、8 credits/minute 及 800 credits/day。官方說明稱 Basic 可取得美股歷史/隔日 EOD，通常到標的首次交易日；真正 SPY/BIL 個別 2007 起 API 結果及 API keys 本輪未測。歷史 EOD 通常隔日 **00:00 ET 以後**才提供，不能拿同日 16:00 ET 信號使用；對 R0 隔日/後續持有期 outcome 須另查下一時段可交易 open 的定義。

官方：
- https://twelvedata.com/pricing-business
- https://support.twelvedata.com/en/articles/9935903-us-equities-market-data
- https://support.twelvedata.com/en/articles/5656039-how-to-get-historical-prices
- https://support.twelvedata.com/en/articles/5549842-twelve-data-quality-standards
- https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage

**正式門檻失敗點：Twelve Data Basic 不能獨立構造正式 SPY/BIL 含息可交易報酬。** 其 plan matrix 的 `/dividends` 與 `/splits` 是 **Grow (individual) 或 Venture (business) 起**才開放，不是 Basic。日線預設已拆分調整而**未必**配息調整；`adjust=all` 權利/實際回傳方式未測，不能把拆分調整後 OHLC 說成當時可成交的原始價，也不能把受益人後見調整的序列回填進發訊號時可見價格因子。R0 T+1 買入、股息資格/付息和 2017 BIL 反分割都要完整事件記錄。

另一項**實物可得性佐證（公開網頁，不是免費 API 授權）**：
- SPY 指定 NYSE product dividend listing includes 2007 payouts: https://twelvedata.com/markets/568728/etf/nyse/spy/historical-data/dividends
- BIL 指定 NYSE product dividend listing includes 2007 payouts: https://twelvedata.com/markets/407231/etf/nyse/bil/historical-data/dividends
- BIL 2017-11-30 1-for-2 reverse split explicitly listed: https://twelvedata.com/markets/407231/etf/nyse/bil/historical-data/splits
- These pages *prove display metadata exist*, not that a Basic key can access `/dividends`, `/splits`, archive prices, legally store raw or use in enterprise AI. Never automate scraping a human-facing webpage to evade access rights.
- https://support.twelvedata.com/en/articles/5179064-are-the-prices-adjusted

### R0 Gate0 逐來源：只根據已查證權利／商品結構，不打虛構分數

| 資料管道 | 商業使用/儲存現況 | 長期日行情 | Dividend & splits | 明確缺口／採購判定 |
|---|---|---|---|---|
| **Twelve Data Business Basic US$0** | 方案明示 internal non-display；**長期原始行情存儲及停用後稽核未證實** | 官方 generic 「每日到首次交易日」+ Basic EOD 可用；SPY/BIL 2007 個別 coverage 尚未實測 | Basic `/dividends` `/splits` **不含**；公開網頁列出早期配息與 BIL 反分割 | **最優先免付費候選，只做覆蓋/權利預檢**，正式含息 Gate0 BLOCKED |
| **Twelve Data Business Venture** | $149/mo 起，按年繳起 $124/mo；商業內部使用有條件允許；衍生資料不得可反推原始 | 官方一般深度充分，但每檔、PIT 待問 | Venture 類別有兩個事件 API；過往 2007-BIL 需 symbol-level 核實 | **若 Basic 不足，再評估**，報價級距最低不保證特定歷史/權利 |
| **Tiingo Power Commercial** | $50/mo / $499/yr；有效期內可依條款保存，**終止時須刪原始/備份**，用 Tiingo 核對另一資料集，可能須刪**被驗證的資料集**；AI Developer/benchmarking 條款限制更嚴 | 30+ years generic EOD；SPY/BIL 實際長歷史未測 | EOD divCash/splitFactor 官方 schema、完整性未檢測 | **不能只因最便宜就選用**，審計/退出授權恐成一票否決 |
| **Massive Stocks Business** | 該公司明示商業用途、20+ 年 SIP 股票市場彙總、公司行動，**價格須詢價** | 官方 archive US listed stock/ETF bars back 2003-09-10；各標的自上市後起 | Corporate actions endpoints：dividend historical since Jan-2000，BIL full splits needs sample | **資料/長期完整性候選**，需要議價＋具體留存授權與標的測試 |
| **EODHD Commercial Internal** | $399/mo 或 $3,990/yr；來源 R1e 條款與歷史修訂已查 | 標示長期 EOD、實際 BIL/SPY 不明 | EOD raw、事件 API 可用性需真實樣本 | **高價備用**，無需先付費 |
| **Databento US equities** | 已有資料商潛在點數不是永久權利。部分平台歷史美股自 2018 起、reference adjustment factors 需另訂閱 | **官方美股主頁：up to 7 yrs / since 2018**，未覆蓋 2007 起 R0 樣本 | Official adjustment factor dataset 月費 $225 起另購 | 不滿足完整 R0 2007～，**保留其他策略研究**，不為花已有額度縮短已凍結樣本 |
| **Alpha Vantage free** | 官方 terms 把投資分析、研究、測試與法人使用列為「commercial」，需另外書面約定 | adjusted OHLC 有長歷史的產品說明 | /daily_adjusted 有分割和股息欄位但屬 premium/商用須另確認 | **免費不具本公司直接商用授權**，不匯入正式系統 |
| **Stooq free / Yahoo webpage** | 未取得官方直接、可核實的法人建模長期資料保存許可；Stooq 第三方報告指出非商用限制 | 有部分日線可看，不保證完整 | 不得假定權息或可交易原始報酬 | **不以爬蟲迴避權利問題** |
| **IBKR TWS historical** | 若用戶**已有合法帳戶**且相應行情權利才可查 | 官方 `ADJUSTED_LAST` 支持 ETF、股息拆分調整；`TRADES` 拆分調整但未調整股息 | 服務按期限逐段查／權利與端點不等於研究儲存授權 | **既有帳戶才值得調查**；無本人帳號/市場訂閱證據，非已通過免費來源 |
| **State Street NAV XLSX** | R1d 實驗已結案 | SPY/BIL 2007+ overlapping NAV | **沒有下一可成交開盤及逐日全事件** | **STANDALONE_LABEL NO-GO**，不可重抓舊 XLSX |

官方參考：
- https://www.tiingo.com/tos/ 、https://www.tiingo.com/about/pricing 、https://www.tiingo.com/documentation/end-of-day
- https://massive.com/business-stocks 、https://massive.com/knowledge-base/article/how-much-historical-stock-data-does-massive-have 、https://massive.com/docs/rest/stocks/corporate-actions/dividends
- https://databento.com/stocks 、https://databento.com/blog/adjustment-factors
- https://www.alphavantage.co/terms_of_service/ 、https://www.alphavantage.co/documentation/
- https://www.interactivebrokers.com/docs/tws-api/doc/md/historical-bars
- https://eodhd.com/commercial-pricing

## 2. 正式使用前的同一份 RFI（對所有候選採相同要求）

所有選擇**先否決式審核，再比價**；不請供應商提供免費試用原始價量到 ChatGPT／GitHub。
1. **標的覆蓋**：NYSE/US listing `SPY`、`BIL` 2007-05-30 至今，每日 regular-session 實際下一日 open／close、完整交易日，是否有系統性缺漏與修正紀錄；回覆每個 symbol `first_available_day`。
2. **公司行動**：SPY/BIL 每次現金股息宣告日、除息日、登記日、付款日、每股現金、特殊配息，以及 2017-11-30 BIL 1-for-2 reverse split（與其他 split），是否都能自 2007 起依法 API 取得；是否能驗證 **未調整**實際開盤價及持股數變化。
3. **回測方式**：公司/台灣私有研究、月末 16:00 America/New_York 定義的下一交易時段建倉（不以收盤已知資料假設同價成交）、歷史 T+1 OHLC 和現金權息處理，可否按現行 license 進行。
4. **時點/版本**：價量和 corporate actions 首次 availability 及後續 correction/methodology history；即使沒有不可變歷史 PIT，是否可提供日期、最新修訂與保守處理政策。**Outcome label 與 feature 的 PIT 必須區分**：已實現 outcome 可在持有期後計算；同日價量若晚於當月 16:00 ET 發布不得當成同期 feature。
5. **明確權利**：准許法人使用，內部非生成式模型及統計回測、agent 只生成程式但**不發送任何原始授權行情**，存儲及異地備份、稽核使用、兩名內部研究員、可保留的摘要／5-field hashes。
6. **終止契約**：終止時須刪哪些原始行情、經稽核資料、歷史 adjusted returns、derived features、歷史預測、對來源的比對結果？可否取得**書面持續性稽核例外**？費率與 legal text。
7. **完整總價**：一個月探索價、12 個月持續使用價、上游交易所 EOD 及 corporate actions、内部 non-display license、額外席次、資料驗證/保留/保固、API 支援、稅費及取消條件。
8. **最低通過證據**：交付相同欄位的 2007 端、2017 反分割前後、2026 端**非原始重新分發**樣本 coverage/rights matrix（或用明確官方文件和驗證範本）；不取得授權前不得用來源 API 跑整份 19 年行情。

目前判定：**沒有供應商被選為正式來源**；Twelve Data Basic = 第一個可以零現金開始的 **覆蓋與法律預檢**，而非 Gate0 通過；Massive = 完整歷史與審計能力值得作為商業替代；Tiingo = 價格最低但取消刪除/資料集核對限制是必須解決的一票否決項目。

## 3. 是否需要今天就申請免費帳戶／開始寄信？

**不需要今天購買、不需要註冊付費試用或下載資料。** 先取得 Twelve Data Basic 對企業模型權利、`/earliest_timestamp` SPY/BIL coverage、`adjust=none/splits/all` 在 Basic 是否可用，以及 `/dividends` 和 `/splits` 是否僅 Venture 才合法提供的明確官方答覆。若不能導入完整含息總報酬，轉向最低合規的其他來源，或持續 BLOCKED；不應自動支付 Tiingo。

**來源仍未驗證**：尚無任何 provider-specific SPY/BIL 2007 原始下一時段價格實際取得；無合法 corporate actions 全史及複算證據；無長期退場後繼續稽核的明確供應商授權。已凍結 R0 / K4 / K5 不改。

## 4. 成本與結果

- 本輪新增費用：**US$0**；現有資料原始檔未搬移或下載，無新 API key/帳號，無商業行情至 AI/外部研究平台。
- **最低月現金成本候選：Twelve Basic US$0**（但不是完整 Gate0）；Tiingo $50；Twelve Business Venture $149 起；EODHD Commercial Internal $399；Massive Business 詢價。公開價格不是帳戶報價。
- **技術推薦**：不要再開發額外來源轉接器、不要重寫回測引擎。下一個權利/覆蓋問題明確前，用既有合成資料只保持 Gate0 阻塞而非新增 CI。若已確認 Basic 的企業用戶資料留存與長期覆蓋，又找到合規公司行動，才可能形成零行情訂閱的正式可交易標籤；否則停在免費前期驗證。
