# SIGNAL R1e｜可交易報酬數據供應商授權預檢（2026-11-22）

**性質：對公開資料供應商文件與條款的唯讀研究，未註冊、未訂閱、未實際擷取 SPY/BIL 的任何 Tiingo/EODHD 行情、未訓練/回測模型。**
**判定：Tiingo Commercial = 最具成本效率的待核實候選；SOURCE_RIGHTS_AND_2007_HISTORY_UNCONFIRMED；Gate 0 BLOCKED。**
研究仍在原有 stacked Draft PR #29；不改動 R0 預註冊研究截點與 M0/M1/M2 問題、不新增 PR、不改 K4/K5。

## 1. 來源比較（官方頁面，2026-11-22）

| 供應商 / 方案 | 官方宣示費率 | 官方宣示欄位與歷史 | 使用權與限制 | 結論 |
|---|---|---|---|---|
| **Tiingo Power Commercial** | **US$50/月或 US$499/年**，企業內部使用，非一般 Power 個人方案 | EOD `open/high/low/close/volume`（未調整）、`adjOpen/adjClose` 等調整價格、`divCash`（除息日）、`splitFactor`；官網稱可涵蓋數十年，**非 SPY/BIL 專屬覆蓋驗收** | ToS 1.6/1.7：內部非生成式 Predictive Model 回測有條件允許；免費方案不得永久保存；付費終止時須刪除所有原始 Tiingo Data；外部商業化/再散布/生成式 AI 訓練/部分 benchmarking 需要額外條款；第三方資料保留權利另查 | **PRIORITY RIGHTS/PIT PREFLIGHT；不採購** |
| **EODHD Commercial Internal** | **US$399/月或 US$3,990/年**，企業伺服器下載公開另列 +US$200/月 | EOD raw OHLC（官方指為 regular session）、股息、拆分、adjusted close；宣稱 30+ 年 EOD，但個股/ETF 需核對 | 官網明示不提供歷史 PIT vintages，事後價格/除息資料可以更正；商用內部授權亦需確認具體應用/保留條款 | **BACKUP / 暫不購買** |
| **State Street SPY/BIL NAV XLSX** | 公開連結，未取得相應商用模型授權 | Antigravity 真正驗過：SPY 5,783 筆，BIL 4,905 筆，共同 4,905 日；但只有 Date/NAV/股份/淨資產 | 無交易 Open/Close、配息與拆分；工作簿附權利限制，已另存 R1d 證據 | **STANDALONE RETURN LABEL NO-GO** |
| **The Economist 一般數位訂閱** | 使用者已擁有（方案自述） | 新聞分析與假說線索，非 ETF 歷史交易行情 | 不因訂閱取得抓文、原文重製、資料探勘、生成式訓練或企業模型行情權利 | **僅作人工研究線索；非 Gate 0 答案** |

官方來源：
- Tiingo EOD 欄位/發布時間： https://www.tiingo.com/documentation/end-of-day
- Tiingo 官網定價： https://www.tiingo.com/about/pricing
- Tiingo 使用條款（注意目前版本會變動，尤其 1.6/1.7）： https://www.tiingo.com/tos/
- Tiingo 商業內部/不可再散布的簡述： https://www.tiingo.com/documentation/
- EODHD 價格： https://eodhd.com/commercial-pricing
- EODHD 調整/修訂與 PIT 版本限制： https://eodhd.com/help/methodology
- 既有 SPY/BIL NAV 測試報告： `docs/research/GLOBAL_CAPITAL_FLOW_R1D_LICENSE_AND_RETURN_DATA_GATE_20261122.md`

## 2. Tiingo 的特殊權利風險（不能只看 US$50 價格）

**現行 ToS 1.6(a)**：Starter/Trial 免費帳號**不得把原始資料或衍生資料寫入任何永久儲存**；只有暫存/記憶體計算可依條款使用。因此不建立免費帳戶來永久抓取 2007–2026 歷史、也不把免費方案資料提交 GitHub。

**ToS 1.6(b)**：Power Commercial 有效訂閱期間可依條款暫存/保留資料；**取消/到期須刪除 Tiingo 原始資料及備份/存檔**。獨立資料稽核要求保留可重算的原始證據，與此有長期衝突；若要長期保留原始來源、解約後復驗或讓獨立審查者長期取得，需詢問**另行書面許可**，不能把 US$50 訂閱當作永久資料所有權。

**ToS 1.6(c)**：某些完全不可反推原始價格的聚合統計與模型輸出可在有條件下保留；連續的單一標的價格／報酬序列、足以重建價格的 rebased 曲線、提供原資料替代品、用 Tiingo 校驗另一個資料庫等可能被限制或禁止。正式複核/報告必須設計為只傳遞非重建性的統計摘要；不能假定 `model validation` 允許向 GitHub 公開原始價量。

**ToS 1.7(c) / 1.7(d)**：Power/Power Commercial 可在條件下建立、驗證、回測**內部、非生成式統計預測模型**；同條款將「自有預測模型之驗證與回測」排除於需 Enterprise 的 benchmarking 定義之外。但是若對外提供研究商品、第三方服務、資料集、AI 基準評比，或用於訓練/改進生成式模型，**須另取 Enterprise License**。本研究應將 M0/M1/M2 保留在私人研究環境，不能因為 GPT/Agent 是開發助手，就將真實行情發送至未確認訓練/保留設定的生成式 AI。

**ToS 1.7(b)**：將資料提供給外部 AI 的引用式分析有額外 inference-provider、無訓練與輸出不重建等條件。**本輪不把 Tiingo 原始報價交給 ChatGPT、Gemini、GitHub 或其他第三方服務。** 先用無行情資料的公開 metadata 和檢查清單繼續。

**有待供應商確證**：台灣企業用戶的具體席位與內部團隊、可儲存或另行保存哪些研究原始證據、精確「AI 協作寫程式但本機跑非生成式模型」的界線，以及 BIL/SPY 個別 2007 起的上市交易 OHLC/股息/拆分完整性。**此處是公開條款解讀，不是 Tiingo 授權書或法律意見。**

## 3. 來源時間戳的前視偏誤風險

- Tiingo EOD 官方文件稱美股收盤日線資料**通常約 17:30 美東時區**可取得，交易所可更正至約 **20:00 ET**，且價格修訂可回寫。
- SIGNAL 研究章程明確定義每月最後交易日 **16:00 America/New_York** 作為訊號截止時間。**不得把 17:30/20:00 才可取得的當日 EOD 欄位做為同日 16:00 的預測特徵**，即使原資料的 `date` 標註當日。
- 不修改已預註冊 cutoff：**M1 需以 T-1（或其他具證據確知在 16:00 前可得之版本）作為價格特徵**。對未來實際交易標籤可使用次日市場交易價格，但此後驗值只能當 label，不能在發訊號時當 feature。
- Tiingo EOD 及 EODHD 的事後修訂/adjusted price 序列不構成歷史 16:00 版本/PIT 檔。若要嚴格引用信號當時版本，需保存當時實際擷取時間和取得原始 bytes，並保守地拒絕無證據的當期版本。

## 4. 不花錢的最小下一步與權限問題

先做**單一資料商的書面／官方支援確認**，只有查到可合法採用的狀態後，才考慮核准費用或 API 實測。需要確認六項：
1. **SPY/BIL**：API metadata 各自實際 `startDate`、`endDate` 是否包含 **2007-05-30～2026-11**，是否皆有 raw OHLC、`divCash`、`splitFactor` 和 BIL 2017-11-30 1:2 reverse split。
2. **每月 16:00 cutoff** 的來源時間：是否提供歷史可確定的 `available_at`、修訂通知或 immutable vintage？無則只能保守用 T-1 或正式快照；問清楚「當日收盤」何時可得。
3. **Power Commercial $50/月** 對本公司私有非生成式 M0/M1/M2 預測模型與歷史回測是否足夠；是否接受我們不公開原始價格、只公開不可重建的聚合統計。
4. **資料保留**：付費持續有效期間允許哪些 raw 原檔和 SHA/receipts；終止後能否保留最小審計證據、不提供價量的 metadata / 5-field secured hashes；若另需買 Enterprise 是否能書面提供精確選項/費率。
5. **AI 工作流**：使用 AI 協助寫程式但**不傳 raw quotes**、在私有執行環境內使用 Python 做一般統計預測是否可按 Power Commercial 進行；無生成式 LLM 訓練/再銷售。
6. **第三方權利**：SPY/BIL 日報價、配息/拆分各自是否由 Tiingo 可授權予台灣企業內部回測、團隊稽核，以及交易價適用的資料授權附約。

**不做的事情**：目前不建立 Tiingo 帳號、付費、使用 free key 大量抓行情、不下載 Tiingo raw data、不向 GitHub 上傳任何供應商數值、不訓練 AI、也不合併主線。

下一步**需要的是一份資料商回覆或可驗的產品許可文件**，不是再跑一次 GitHub Actions 或重抓 SSGA。若未能取得權利，保留 Gate 0 BLOCKED；無論如何不以文獻討論代替實際買賣價和 PIT 資料。

## 5. 交付與責任
- 完成：獨立確認 Tiingo $50/月內用方案、EOD 原始欄位/除息拆分、ToS 1.6/1.7 的免費儲存禁令/解約刪除/內部模型權利/生成式限制、17:30 ET 發布與 16:00 cutoff 差異；比較 EODHD 既有 $399 方案，並確定唯一優先查證候選 Tiingo。
- 未完成：供應商書面回覆、SPY/BIL 個別 API 查詢成功、原始行情+股息+分割合約與永久審計許可、歷史 PIT 回溯、前瞻研究、模型、交易。
- 多 Agent：不宣稱啟動任何獨立 Agent；本項少量文件與權利比對不值得增加多寫入者。
- 費用：本輪 **US$0**；任何後續採購須另行核准。
