# SIGNAL R1q｜Public Data First 公開資料優先可行性 Gate（2026-11-26）

**本輪定位：跨專案重用證據之決策矩陣；不建立新的抓取器、不執行回測、不修改 R0 月末 16:00 ET 規則、不取得付費行情。**
主權威進度仍在 SIGNAL Draft PR #29 的 `docs/CURRENT_STATUS.md`。另一專案 `kalisanhomei-afk/real-world-strategy-system` 的 `AGENTS.md`、main `docs/CURRENT_STATUS.md` 及最新 PR/Issue 已唯讀核對；其主要任務為現實世界模型/水電人口，不應推定其 main 有任何 SIGNAL SPY/BIL 原始行情。跨專案僅引用可取得的研究證據，不複製未授權 ZIP/XLSX。

## 1. 三類 Gate 與資訊時點

- **SOURCE_FEASIBLE**：官方頁、欄位、資料期間、發布制度可確認；不等於已抓 raw bytes。
- **PIT_FEASIBLE**：有決策時真正可見的原始發布版本及發布/取得時刻；今日修訂版不能用於歷史月末 16:00 ET。
- **MODEL_ADMISSIBLE**：來源授權、欄位/單位一致、歷史版本/缺值、可交易報酬標籤全部通過；與交易安全門檻分開。

## 2. 唯一來源可行性矩陣（沿用既有成果，不重做）

| 來源/欄位 | 已存在的實際證據 | 現在足以做什麼 | 仍缺證據/否決條件 | 本輪判定 |
|---|---|---|---|---|
| Fed H.6 / M2 | SIGNAL R1c 既有 Antigravity 外部取得 H.6 2020-08-27 HTML、SHA/UTC 回執；文件核對值 2020-Jul SA M2 18,327.0 USD bn，**未由本次 runtime 獨立重算原始位元組** | 貨幣供給統計與描述性來源研究 | 月末 as-of 各期版本、2020/2026 定義改版、商業使用條件；**Fed DDP 2027 將下線，勿開發新 DDP 依賴** | `SOURCE_PARTIAL/PIT_HOLD` |
| Treasury TIC `npr_history.csv` | Antigravity 外部取得 2020-03-16 ZIP、單格 Jan2020 +122,883 USD million = 官方新聞稿約 +122.9 USD bn；現有 SHA 回執未在本次工具複驗；ZIP 有跨發布日 member timestamp 風險 | 資金流口徑/單期發布對照 | 歷史各期 first-public PIT、ZIP 內版本風險、取得及商業使用權 | `SOURCE_PARTIAL/PIT_HOLD` |
| Treasury Daily T-bill rates | 官方有日利率 CSV 歷史與 XML feed，現行提供可追溯的資料公開入口 | **利率與資金成本的描述性代理** | 利率不是實際 BIL 可交易、含息持有期總報酬；歷史交易日及可用時刻、使用權 | `SOURCE_ENTRY_CONFIRMED/RETURN_LABEL_NO_GO` |
| BIS GLI／跨境銀行信用 | 研究分支 R1h–R1m 已有官方發布頁/當前 ZIP 外部 SHA 及局部數值查核 | 季度國際信用背景、貨幣分布研究 | 季度發布延遲、當月 16:00 ET 精確 PIT、歷史修訂、用途權利；**不是股票或黃金之間的封閉資金流** | `SOURCE_PARTIAL/PIT_HOLD` |
| ICI 公開基金摘要 | 既有 H-ICI-WRAPPER-01 11/18 週 1/4 觀測、不同日期/修訂差異已記錄 | **少量公開摘要的解釋性研究** | 商用自動抓取、完整儲存、再散布、模型用途授權；感恩節的 11/24 MMF vs 11/25 Equity 不可錯配 | `DESCRIPTIVE_ONLY/MODEL_HOLD` |
| State Street SPY／BIL 公開 ETF 頁 | 本分支最新研究已確認 issuer NAV/download/股息相關連結、SEC 證實 BIL 2017 反分割事件；早前其他執行環境曾回報 NAV XLSX 可下載，**本分支尚無獨立 XLSX raw bytes、列驗收與授權** | ETF NAV 與權益事件的來源可得性檢查 | NAV 非下一交易時段成交價；2007 完整度、分紅/反分割調整、可下載授權、合規資料儲存與原始 SHA | `SOURCE_ENTRY_CONFIRMED/TRADABLE_RETURN_NO_GO` |
| FRED/ALFRED、Ken French | 已有研究文件確認 FRED/ALFRED vintage、French 學術因子/歷史候選；CRSP/ICE 等上游權利 | 學術比較/代理的**候選**，尚非已清權模型資料 | FRED Services/API 有 AI/軟體開發及重用限制；French 資料上游權利，Mkt-RF/RF 非 SPY/BIL 真實可執行報酬 | `RIGHTS_HOLD/EXPLORATORY_ONLY` |

**證據來源：**
- 本 Repo `docs/research/GLOBAL_CAPITAL_FLOW_R1_SOURCE_FEASIBILITY_V0_1.md`、`GLOBAL_CAPITAL_FLOW_R1C_TIC_RECEIPT_PIT_AUDIT_20261122.md`、`GLOBAL_CAPITAL_FLOW_R1M_BIS_RELEASE_TIME_AND_GATE0_DECISION_20261123.md`、`GLOBAL_CAPITAL_FLOW_R1N_MARKET_RETURN_FREE_FIRST_SUPPLIER_GATE_20261123.md`、`GLOBAL_CAPITAL_FLOW_R1P_SPY_BIL_MARKET_DATA_LICENSE_DECISION_20261126.md`。
- Fed 原站：https://www.federalreserve.gov/releases/h6/ ; https://www.federalreserve.gov/data/ddp-retirement-frequently-asked-questions.htm （2026-11-26 再查證 DDP BYP 已於 11 月移除，預製檔 2027-03-31 停、頁面 2027-07-01 移除）。
- Treasury 官方：https://home.treasury.gov/archives-of-tic-monthly-data-releases ; https://home.treasury.gov/interest-rates-data-csv-archive/ ; https://home.treasury.gov/treasury-daily-interest-rate-xml-feed
- BIS：https://data.bis.org/topics/GLI ; ICI：https://www.ici.org/research/stats/combined_flows ; FRED：https://fred.stlouisfed.org/legal/

## 3. 最小可執行公開資料驗證（零新訂閱）

**先研究可行性，不重定義現有 R0 的正式 ETF 投資績效目標。**

1. 以既有 H.6、TIC、BIS **已封存外部回執**為取樣基準，建立 source→observation period→release date→capture UTC→vintage→rights→as-of 月末截點的映射；已核查的 2020 TIC 單欄不可重抓當成新工作。缺失時間戳填 null，不能補猜。
2. Treasury 官方日 T-bill 利率可先作「資金成本條件」描述性背景來源，不將利率直接當 BIL 實際總報酬；不得為了湊完整回測而自行更改 outcome。
3. 如跨專案有原始 State Street NAV XLSX，**先核對原始檔存取位置、歷史涵蓋與授權**（本次未取得），但不把 NAV 變成 SPY/BIL 下單成交標籤。
4. 保留 K4/K5 前瞻 official-only 驗收和 R1u 四週固定規則，不因新資料出現而回填預測或增擴超過四週的樣本範圍。

## 4. 不購買資訊商的門檻與明確停止規則

- **現階段新增資料訂閱：US$0**；Twelve Data 業務信已有自動回信監控，勿重寄；Tiingo/EODHD/Massive 只維持候選，不進行採購。
- 若公開資料只能支援宏觀描述或探索性關係，**不對其宣稱金融商品可交易 alpha**，停止開發新市場數據抓取器。
- 只有在已清楚證明特定標的的交易價格／股息／反分割／使用權／歷史資訊時點是必需且公開管道無法合法取得時，才提出一份明確欄位缺口及書面權利要求，交由 Owner 批准單月試點。
- 不得讓正在驗證的公開資料規格變動，默默擴張為新系統/新資料庫。整合使用**一份矩陣+既有 receipt 文件**。

**本輪狀態：`PUBLIC_DATA_FIRST_DECISION=GO`; `PUBLIC_MACRO_SOURCE_FEASIBILITY=PARTIAL`; `R1_FORMAL_GATE0=BLOCKED`; `SPY_BIL_EXECUTABLE_RETURN=NOT_VERIFIED`; `LICENSED_MODEL_INGEST=NO_GO`; `R2_NOT_STARTED`; `NO_TRADING`。**
