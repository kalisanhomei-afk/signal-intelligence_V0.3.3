# SIGNAL K4｜數據取得可行性與停止／採購決策（2026-11-16）

**結論：GO 進入小範圍可得性驗證；NO-GO 對外宣稱歷史 PIT、回測勝率或可交易績效。**

## 1. 真正的研究瓶頸：市場共識不是唯一數字

2026-11-10 WASDE 第 677 期，美國玉米 2026/27 期末庫存 **1,758 百萬蒲式耳**。已有三個不同來源的市場預估：

| 來源分類 | 本次可查預估（百萬蒲式耳） | 實際−預估 | 文章頁面日期 | 來源可信度／時間驗證 |
|---|---:|---:|---|---|
| CME Group 的 Econoday 估計表 | 1,846 | **−88** | 2026-11-10 | CME 自有頁面可查，但當下頁面的真正首次上線與底層調查供應商/截點尚未經 PIT 稽核 |
| StoneX 11/05 市場預估文章 | 1,840 | **−82** | 2026-11-05 | StoneX 文章標示當日市場平均預估，但現在閱讀的頁面不是已驗證的11/05不可變快照 |
| DTN 11/06 報導 Dow Jones/Wall Street Journal 調查 | 1,826 | **−68** | 2026-11-06 | 與 StoneX/CME 可能是不同調查樣本，不可直接混合或宣稱其中一個「才是唯一正確共識」 |

來源：
- CME https://www.cmegroup.com/education/events/econoday/675955
- StoneX https://www.stonex.com/en-us/insights/nov-wasde-estimates/
- DTN https://www.dtnpf.com/agriculture/web/AG/news/article/2026/11/06/grain-prices-melt-can-usda-provide
- 2026/11 USDA 帳務數字與來源比對 https://tools.gotredas.com/nov-wasde/ 及官方 ESMIS https://esmis.nal.usda.gov/sites/default/release-files/796142/wasde1126.txt

**可確定的純數值結果：** 三個結果都是負向庫存意外，量值分別為 −88、−82、−68 百萬蒲式耳，跨來源幅度差20百萬蒲式耳。**不可確定：** 三份調查各自的有效發布前可取得瞬間；其中 CME 頁面是否由報告發布後編修；不同抽樣、截止時間、平均算法何者更能代表交易者資訊集合。**不應**選擇使交易策略最佳的一份後才宣布優勢。

在正式事件研究之前，逐筆保存：底層 poll vendor、調查對象/平均或中位數、截止時間、首次可用證據、當時內容指紋、來源授權。即便網頁標示11/05或11/06，仍需獨立歷史時間紀錄才能晉級 `PIT_VERIFIED`。

## 2. 同一期貨合約的盤中行情：三個方案

| 方案 | 能支援的第一步 | 成本型態／限制 | 結論 |
|---|---|---|---|
| **Databento 歷史資料用量計價** | CBOT/CME `GLBX.MDP3`，指定實際月份合約 `ZCZ6`，只取11/10美東報告前後約3小時的 `ohlcv-1m`，再評估是否有 `trades`/`TBBO` | 官方表列可以不訂月費按用量購買歷史資料，實際費用依查詢量與適用授權計算；資料**未購買**、未取得該合約當日任何盤中列。分鐘 OHLCV 不等於具備可成交 bid/ask 與滑價 | **首選低成本實測候選** |
| CME Group **DataMine** | 取得交易所官方歷史 Time & Sales、Top of Book，具備對應 CBOT 合約時間/成交價/量 | 正式歷史資料採購、授權及資料格式轉換需確認；無帳戶與報價，不要杜撰訂購價格 | 交叉驗證／當高精度需求出現 |
| CME 官網公開延遲報價與日資料 | 驗證合約規格、行情是否存在、日方向等粗略事實 | 公開網頁報價延遲至少10分鐘，非完整可回溯1分鐘檔，不可作為發布後可成交價的嚴格驗證 | 只作前期人工核對，不做正式策略回測 |

資料商官方：
- Databento https://databento.com/pricing 與 CME 交易所資料產品 https://databento.com/docs/knowledge-base/datasets/glbx-mdp3
- Databento 產品基礎 https://databento.com/futures
- CME https://www.cmegroup.com/market-data/real-time-and-historical-data.html
- CME 官方歷史訂購 https://datamine.new.cmegroup.com/
- CME 延遲報價限制 https://www.cmegroup.com/trading/about-quotes.html

CME 官方玉米期貨規格：https://www.cmegroup.com/markets/agriculture/grains/corn/specs
- 商品代碼 `ZC`，2026年12月 Globex 合約例 `ZCZ6`（不得與連續合約或2027年3月混用）。
- 合約5,000蒲式耳；最小變動 **0.25美分／蒲式耳 = 每份合約12.50美元**。
- 這是**合約機械規格**，不代表能以單一tick手續費/滑價成交。

### 2.1 先用公開來源測試報告後的價格時間問題（2026-11-16）

先不付費，就能用第三方文章取得**兩個描述性時間節點**：

| 來源及資料類型 | 2026-11-09 日價格 | 2026-11-10 發布後 | 可說明／不可說明 |
|---|---:|---:|---|
| Tredas 事後市場報告所列 ZCZ6 報價 | 439.25美分／蒲式耳（前一日結算） | 11:01:05 CT：450.75；11:06:12 CT：452.50 | 同一篇報告所述兩時點差 **+1.75美分**；沒有原始逐筆撮合、交易所Bid/Ask或不可變當時快照 |
| Barchart 合約 `ZCZ26` 公開歷史日資料 | 439.25 | 11/10日價449.00 | 日價相差 **+9.75美分**，但並非公布後五分鐘反應、並非精確收盤成交成本 |

來源：
- https://tools.gotredas.com/nov-wasde/
- https://mnbl.websol.barchart.com/?1_selected=futureQuote&module=futureDetail&popup=1&region=US&symbol=ZCZ26
- https://finance.yahoo.com/quote/ZC%3DF/history/ (日資料交叉查核，連續期貨代碼不得代替歷史逐月期約身分)。

**絕不能用 450.75 − 439.25 = +11.50美分直接說「USDA 報告造成首分鐘上漲11.50美分」！** 分母是**前一日結算**，中間含夜盤與報告前交易；我們尚未取得 16:59 UTC 的同合約價格。因此目前甚至無法正確識別「新聞公布瞬間的增量價格反應」。

另外，公開行情網站不同查詢 URL/合約識別碼出現不同價格結果。當年期約、連續合約、CFD、不同站點的可選日行情不得互相填補。Barchart 的 `ZCZ26` 與申購資料預定使用的 `ZCZ6` 需以原始供應商 instrument definition 驗證對應關係，不能只靠代碼形式假設。

這些參考值已納入 `cases/2026-11-10-zcz6-public-price-scout.json`、`public_price_scout.py` 和獨立拒絕測試；僅產出 `price_scout_research_only.json`，`actual_trade_bid_ask_rows_acquired=0`、`trade_eligible=false`。**不用額外購買資料即可先取得「是否值得查證盤中時間」的研究線索，但無法做正式事件研究。**

### 2.2 採購預算前先查官方費率、確定單日實際價格

Databento [Pricing](https://databento.com/pricing) 目前列示 **US$125 新客戶歷史資料試用額度**與按用量計價選項；但依授權／客戶身份仍可能有不同費用，不表示使用者可以保證免費下載。

官方歷史 API 可用 `Historical.metadata.get_cost(...)` 查詢成本。這是**已文件化的 API 能力，不是本系統已執行查詢或拿到的報價**：[get_cost 官方說明](https://databento.com/docs/api-historical)。

向供應商帳戶查價時，範圍固定為 `dataset=GLBX.MDP3`、`symbols=["ZCZ6"]`、`stype_in="raw_symbol"`、`schema="ohlcv-1m"`、`start=2026-11-10T16:30:00Z`、`end=2026-11-10T19:30:00Z`，其後再對 `trades`、`tbbo` 分別詢價，且先確認該 symbol 真存在於歷史定義。**未經帳戶真實回傳，不提供任意估算的美元成本。** 不建議因一個實驗就訂每月US$199標準版或其它長約。

## 3. 事前確定的最小資料購置／驗收清單

**第一筆市場數據只需單一日 × 單一合約 × 180分鐘左右。** 不要直接採購十年成交資料，因成本與授權風險遠高於驗證效益。

1. 購買前先確認 `ZCZ6` 當日有 `2026-11-10T16:30:00Z` 到 `19:30:00Z` 的真實 `ohlcv-1m`；取得實際報價與授權後再決定。先做資料可得性測試，不下單。
2. 下載完記錄原始資料授權、供應商、資料集代碼、原始檔SHA256、合約完整名稱、每一列UTC與價格單位（美元或美分／蒲式耳）、事件時刻。
3. 對缺少的分鐘、休市、時區、合約換月以及價格倍率做原始資料交叉驗證，不得插值製造交易價。
4. 對比公告後5、30、180分鐘的描述性反應，**必須分開**：(a) 公布前已知共識數值與其證據；(b) 公告後SIGNAL實際取得 USDA 時刻；(c) 實際可交易的行情時刻與成交成本。
5. 未購得可驗證的原始盤中資料前，`historical_intraday_price_rows_acquired=0`、`event_study_eligible=false`、`trade_eligible=false`。

## 4. 目前停止規則與下一步

現在不是已完成投資模型；這個 MVP 的成效是**發現了同一研究問題對共識定義的敏感性**，並找到了可低成本驗證行情資料的途徑。

- 保留三個市場調查版本，不合併、不回填各自發布前時間證據。
- 不花時間建立完整行情資料倉庫，先驗證一次合法、低用量的CBOT分鐘資料取得。
- 若成本／授權不合理，改先做同月事件研究的描述性資料來源評估；**不能**降級成無法支持交易時點的免費日收盤資料還宣稱可交易優勢。
- 任何可能的價格方向只屬研究機制，並非收益預測、投資建議或買賣訊號。

**採購與連結帳號是另一步獨立授權；目前尚未使用付費行情服務，也未要求使用者承諾訂閱。**
