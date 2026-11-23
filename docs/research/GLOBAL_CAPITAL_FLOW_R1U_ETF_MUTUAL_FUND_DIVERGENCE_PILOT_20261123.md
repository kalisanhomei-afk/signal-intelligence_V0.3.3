# SIGNAL R1u｜美國股票資金的 ETF／共同基金分化：四週實證與下一輪事前規則

- **日期**：2026-11-23 Asia/Taipei
- **分類**：PUBLIC_ISSUER_REPORT_SUMMARY / HISTORICAL_DESCRIPTIVE / SHORT_NOMINAL_SERIES / NOT_PIT_VERIFIED / NOT_RETURN_MODEL
- **範圍**：只檢查已公開 ICI 週報中四個**股權類**估計的符號及組成；不採購資料、不下載完整歷史 XLS、不訓練 AI 模型、不宣稱配置因果、不改 R0 M0/M1/M2／16:00 ET 凍結定義。

## 1. 新的實際檢查：四個連續週，不能只看 11/11 單週

使用 ICI 2026-11-18 *Combined Estimated Long-Term Flows and ETF Net Issuance* 公開摘要「Equity」欄（基金+ETF 合計），與 ICI 2026-11-17 *Estimated ETF Net Issuance* 和 2026-11-18 *Estimated Long-Term Mutual Fund Flows* 公開摘要對照。單位均為 **USD billions**，表中精度三位小數；上游原始欄位標記「millions of dollars」。下表為極少量、同一統計類別的重點數據及算術重建，**不是原始表格的重發**。

| 週截至 | 股票共同基金淨新現金流 | 股票 ETF 淨發行 | ICI 股票合計估計 | 驗算 |
| --- | ---: | ---: | ---: | --- |
| 2026-10-21 | -21.599 | +42.264 | +20.665 | exact |
| 2026-10-28 | -23.140 | +34.221 | +11.081 | exact |
| 2026-11-04 | -18.107 | +35.541 | +17.434 | exact |
| 2026-11-11 | -8.200 | +45.219 | +37.020 | difference US$0.001bn due to estimated rounding |
| **四週合計，非正式交易額** | **-71.046** | **+157.245** | **+86.200** | components +86.199bn ≈ reported +86.200bn |

**獨立 Decimal 四週重算**：4/4 股權共同基金淨流出（負值），4/4 股權 ETF 淨發行（正值），4/4 同類股票基金合計淨流入（正值）。這是**基金包裝形式的分化／需求異質性**，不是全體投資者撤離股票；也**沒有證據**能證實共同基金賣出者就是同一批 ETF 買入者。ETF 的 creation/redemption 並不等價於每筆二級市場成交的資金流。

**特殊週的排除**：ICI 表列 2026-10-14 股票合計 -US$476.423bn，並明確說明主要由 collective investment trusts 活動所致，不是一般散戶贖回。此審閱選取緊接其後四週是**事後挑選的描述性子樣本**，因此不得聲稱週期的平均流入具代表性、不得做正式顯著性檢定或升級證明 alpha。不能偷偷把 10/14 排除後把剩餘四週當作無偏歷史回測。

**原始公告頁與時點**：
- 2026-11-18：https://www.ici.org/research/stats/combined_flows
- 2026-11-18：https://www.ici.org/research/stats/flows
- 2026-11-17：https://www.ici.org/research/stats/etf_flows

ICI 明確表示前幾週的估計會因重分類、資料調整與回報基金數改變而**修訂**。本次是 2026-11-23 讀到的回顧文字，**不是**各週當日已知數據。原始報導 HTML bytes、伺服器初次發布精確 UTC、HTML SHA 未取得，不偽造。

## 2. 第二個現象：相同 11/11 截止週 MMF 方向不同，但尚未建立貨幣流向

ICI 2026-11-19 Money Market Fund Assets 的公開報告提供 2026-11-04 **US$8,015.74bn** 與 2026-11-11 **US$7,980.02bn**，按數值差為 **-US$35.72bn**。同週 ICI 股票合計 +US$37.020bn。ICI 說 MMF 資產變動**主要**由流量推動，可作淨新增現金流的近似代理，並未聲稱「每一分下降都流入 ETF」。這是*同日期方向共現*，不是 35.72bn → 37.02bn 的資金追蹤。沒有同一週、同樣統計口徑的多期 MMF 序列授權資料可供實證轉換機率；缺口明列，不補造。
- 官方來源 2026-11-19：https://www.ici.org/research/stats/mmf

## 3. 事前凍結下一小步，避免假說事後挑選

**Exploratory observation registration (NOT R0 formal M2 feature)：H-ICI-WRAPPER-01**

- **決策問題**：上述 4/4 ETF+、共同基金−、股票合計+ 是否於**之後已發布資料**繼續發生？與 MMF 資產下降是否能在**相同觀察截止日**反覆共現？
- **起點及不可變篩選**：只用未來首四個在 2026-11-11 **之後**的完整 ICI 公告「股票共同基金、股票 ETF、股權合計」均可取得、且可匹配 MMF 觀察截止日的**連續可比**週，不跳過負例；若碰到休市/感恩節而觀察日偏移，標示 **INCOMPARABLE**，不強行將 Tuesday 11/24 vs Wednesday 11/25 配成同週。最終收集的四個可比觀察日必須先後相接；不具可比性時列缺失、報告樣本不足，不延長窗口暗中挑選較佳結果。
- **首批候選日期**：11/18、11/25（可能休市導致非 11/25，先標「須查」）、12/02、12/09；**只在其官方公告實際公布後讀取**，不可填入預期數值。若四週中僅三週具有可比的 MMF 日期，則 MMF 驗證為 **INSUFFICIENT_COVERAGE**。
- **狀態定義**：股票合計>0、股票 ETF>0、共同基金<0，三條同時成立記 `WRAPPER_DIVERGENCE`；符合 3/4 次僅稱 **DESCRIPTIVE_PERSISTENCE_IN_SELECTED_WINDOW**，≤2/4 則 **NOT_PERSISTENT_IN_SELECTED_WINDOW**，低於四個匹配觀測則 **INSUFFICIENT_COVERAGE**。同週 MMF 下降僅作獨立方向標記，**即使四週全數同向也不稱資金從 MMF 流到股票**。任何預註冊觀察都不能建立有統計效力的預測因果或替代交易驗收。
- **獨立反例與風險**：a) ICI 註腳與分類調整，b) 假期造成截止日不同，c) mutual fund→ETF wrapper migration 並非股票/現金再配置，d) 10/14 CIT 異常，e) MMF 資產變化不等於封閉資金流，f) ICI 的歷史數值後來修訂。保留估計與發布日並註記，禁止前視偏誤。
- **資料權利**：僅記官方公開摘要的少量數值與來源/公告日，不抓完整受限歷史表、不把 ICI 統計內容當無限制可供模型儲存的資料集；若任何使用需商用/機器重用的額外授權，維持 HOLD。

## 4. 明確決策與下一步

- `R1U_FOUR_WEEK_WRAPPER_DECOMPOSITION_VERIFIED`（公開修訂資料之描述性結果）。
- `R1U_OFFLINE_DECIMAL_4_OF_4_ARITHMETIC_CHECK_PASS`（現有公開摘要的算術，不是 CI）。
- `H_ICI_WRAPPER_01_PROTOCOL_FROZEN_EXPLORATORY`（只准描述，正式 R0 未改）。
- `ROTATION_CAUSAL_LINK_UNVERIFIED`; `FUTURE_MATCHED_REPORTS_NOT_YET_CAPTURED`; `FORMAL_GATE0=BLOCKED`; `R2_NOT_STARTED`.
- **下一個真正工作**：待 11/18 截止週的 ICI 股票合計公報實際出現後，對它與既有 11/18 MMF 同截止日記下首個預註冊樣本；先查當日假期規則。為避免檔案/排程膨脹，現不新增程式、另開 PR、發信、付費、CI 或自動監測工作。正式資料權利仍由現有 Twelve Data 回信自動任務追蹤。
- **資產去向的對應結論**：股票基金正淨流入**可與**股票共同基金負流量同時成立；不能把淨流入和淨流出簡單相加宣稱資金由某市場流向另一市場。正式 SPY/BIL 可交易報酬需等待原有授權與 PIT Gate，不能以本次數字替代。

## 5. 2026-11-23 live independent publication crosscheck — R1v
**Actual source check (public-only, no new source files):** the ICI official combined/mutual/ETF publications still show week ended **2026-11-11** (combined release Nov18, ETF Nov17). As of **2026-11-23**, **ICI's week ended 2026-11-18 combined stock + mutual/ETF breakdown has NOT yet appeared on the official combined release page**. 2026-11-25 is **estimated upcoming**, not a confirmed actual release or measured values: https://www.ici.org/research/stats/combined_flows .

However **independent LSEG Lipper reporting**, published by **Reuters on 2026-11-20**, reports week ended **2026-11-18**:
- **US equity funds net subscriptions +US$45.71bn**, third consecutive week positive in *its own US equity fund series*: https://www.reuters.com/legal/transactional/us-equity-funds-draw-inflows-third-straight-week-2026-11-20/
- **Global equity funds +US$59.23bn**, *global* money market funds **-US$13.89bn**: https://www.reuters.com/world/china/global-markets-flows-graphic-2026-11-20/
- Same first Reuters US-focused report says **money-market funds -US$19.12bn**. Do NOT equate this with ICI's **US mutual MMF total-assets change -US$3.58bn** for week ended 2026-11-18: definitions, fund coverage, direct net flow versus asset change differ and no bridging documentation has been verified. ICI source: https://www.ici.org/research/stats/mmf . Lipper original underlying history is NOT downloaded or license-cleared. The global -13.89bn and US -19.12bn belong to separate aggregation categories, not a conservation ledger.

**Important temporal discovery**: the 2026-11-19 ICI MMF release explicitly notes due to **2026-11-26 Thanksgiving**, the upcoming **MMF** report will cover **week ending Tuesday Nov24**, published **Wednesday Nov25**. This means the registered ICI combined weekly Wednesday Nov25 observation and MMF Tuesday Nov24 could fail exact endpoint alignment. Preserve `INCOMPARABLE` rather than alter the pre-registered weekly join. Source https://www.ici.org/research/stats/mmf .

**Decision**: `LIPPER_NOV18_DIRECTION_EXTERNALLY_REPORTED_NOT_ICI_SAMPLE`. Independent Lipper is useful *descriptive context* on continuing US/global equity demand and price/flow divergence, but **cannot** be substituted into `H-ICI-WRAPPER-01`'s pre-registered ICI three-part sample; Lipper has no checked mutual/ETF wrapper split for this week. `NOV18_ICI_WRAPPER_NOT_YET_PUBLISHED`, `TWO_MMF_SERIES_NOT_COMPARABLE`, `PIT_AND_LICENSE_BLOCKED`. No source bytes, official original SHA, backtest, claims of causality, or new paid data.
