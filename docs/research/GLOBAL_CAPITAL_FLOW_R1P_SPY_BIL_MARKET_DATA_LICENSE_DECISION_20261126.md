# SIGNAL R1p｜SPY/BIL 商業內部研究的價格資料供應商授權決策（2026-11-26）

**範圍：** 既有 PR #29 下游 SPY/BIL 最小市場報酬研究；只讀供應商**現行官網**與既有 Gmail 授權信之實際狀態，無訂閱、無 API Key、無原始行情下載、無數值回測、無寄信、無交易。

## 1. Twelve Data — 已發出詢問，尚未收到正式授權回信

- Gmail 已寄出信件主旨：`Licensing clarification request — internal SPY/BIL historical ETF research (no data access requested)`；2026-11-23 02:10:32（Gmail 回傳 timestamp 欄位，時區未明示）；thread `1a20624f31216889`。本次唯讀 Gmail thread 只找到原始寄出訊息，**沒有 Twelve Data 業務方回覆**。既有每日監控仍有效，不重複寄信。
- 官網 2026-01-01 Terms §2.2、§2.3(l)：資料內部使用/Non-Display 需視 tier，Free Tier 禁止商業用途；§3 的 exchange/third-party license 可能另加限制。聯繫銷售前，不能以 Business Basic 免費的頁面描述視同對本公司商業研究合法。
- Twelve Data 2026-04-01 價格公告：Business Basic 免費、Venture 自 **US$499/月**、Enterprise 自 **US$1,099/月**；實際授權、歷史 SPY/BIL 企業行動/總報酬、座席/留存及第三方成本**未取得供應商具體確認**。其官網價格表為公開標示，非本公司核准報價。
- 官方：https://twelvedata.com/terms ; https://twelvedata.com/news/march-2026-updates ; https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage 。

## 2. Tiingo — 2026-11-05 更新 Terms 的實質新風險

官網 `https://www.tiingo.com/tos/` 明示 **Last Updated 2026-11-05**；價格頁 `https://www.tiingo.com/about/pricing` 顯示：
- Individual Power **US$30/月或 US$300/年**，**不能推論適用本公司的法人商業使用**；
- Commercial Power 商業內部使用標示 **US$50/月或 US$499/年**（是否涵蓋 SPY/BIL 完整 2007 起 EOD/分紅/2017 BIL reverse split，仍需個別覆蓋驗證）。
- Terms §1.7(c)：有效 Power/Power Commercial 授權條件下，**內部、非生成式 Predictive Models**（包括回測、風險分析、投資訊號）原則可用；但**不得對第三方提供或銷售模型/預測輸出**。商業對外 SIGNAL 研究銷售需另考慮 Enterprise，不能用 US$50 確認對外授權。
- Terms §1.7(d)：生成式模型訓練、某些與 AI Developer 服務相關用法、面向第三方商業預測或第三方 Benchmarking 須 Enterprise。§1.7(b) 對純推論用途有 Approved Inference Provider/ZDR 或不訓練等約束；**直接將 Tiingo 原始市場資料傳入 ChatGPT/Gemini/Agent 並非自然合規，需先做個別條款及設定核准**。
- Terms §1.6(a)：**Starter/free/trial 不得永久保存 Tiingo Data 及 Derived Products**；§1.6(b)：付費方案結束時，除另有書面約定外，**必須從備份/封存等各處刪除 Tiingo 原始資料**。這與 SIGNAL 需長期保存可複核原始版本的 `immutable raw evidence` 需求直接衝突。§1.6(c) 部分不可逆推回原始行情的聚合績效指標可在符合條件時保留，但不能假定整段收益率時序或任何 hash 都符合。
- 部分資料另受第三方權利限制 §1.7(e)，價格不等於已完整涵蓋公司所在地、交易所與 ETF 全歷史。
- 官方：https://www.tiingo.com/tos/ ; https://www.tiingo.com/about/pricing ; https://www.tiingo.com/documentation/ 。

**關鍵建議：** Tiingo 價格比 Twelve Data Enterprise/Venture 起價更低，但在使用者重視「原始證據永久可驗證、模型跨 Agent、未來商業對外銷售」的情況下，**US$50/month 商用內部方案不能直接滿足全部最終需求**。考慮用作「隔離的內部研究候選」而不是永久唯一權威來源，直到授權例外書面確認。

## 3. Gate 決策與驗收條件

| 重要需求 | Twelve Data | Tiingo Commercial Power |
|---|---|---|
| 法人內部非展示 | 條款以適用 tier/交換所授權為前提，既有銷售信未回 | 官網有明確商用方案及 §1.7(c) 條件 |
| 2007-05-30 起 SPY/BIL 真實 EOD | **標的級未驗證** | **標的級未驗證**，30+ 年為平台廣告非兩檔覆蓋保證 |
| 現金股息、BIL 2017 反分割、總報酬 | 未驗證 | 未驗證 |
| 歷史原始行情 PIT/修訂版本 | 未驗證 | 未驗證 |
| 兩名研究人員、AI Agent 原始行情處理 | 未取得適用書面授權 | §1.7(b)/(d) 有明確限制，須個別判定 |
| 取消後稽核原始行情保存 | 未驗證，需書面回覆 | **一般條款要求刪除**，需更高方案書面例外 |
| 對外販售模型訊號／衍生報告 | 未驗證 | §1.7(d) **Enterprise required** |
| 本公司確定可用總成本 | **未確認** | **未確認**，頁面為起始標示價格 |

現階段：
`PROVIDER_SELECTED=false`；
`MARKET_DATA_PURCHASE_AUTHORIZED=false`；
`PRICE_HISTORY_SYMBOL_COVERAGE_VERIFIED=false`；
`RAW_ARCHIVE_AFTER_CANCELLATION_RIGHTS_VERIFIED=false`；
`AI_AGENT_RAW_DATA_ACCESS_AUTHORIZED=false`；
`HISTORICAL_POINT_IN_TIME_CERTIFIED=false`；
`R1_GATE0=BLOCKED`；
`R2_NOT_STARTED`；
`NO_TRADING`。

**下一個最小行動：** 等已寄出 Twelve Data 授權信實際回覆；Tiingo 僅保留官方條款比較，不替使用者發送新詢問信或啟用付費方案。若未來要發 Tiingo 授權詢問，需先起草讓 Owner 逐封核准。下游可先使用合成無授權數值測試時序對齊，但不以合成測試宣稱市場 alpha。