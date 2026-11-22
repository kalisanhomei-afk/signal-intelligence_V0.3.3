# 視界 SIGNAL｜全球貨幣、信用與資產價格研究章程 V0.1
> 日期：2026-11-22（Asia/Taipei）｜狀態：PROPOSAL / RESEARCH_NOT_STARTED｜文件性質：候選研究路線，不改變已凍結 K4/K5 假說、主線產品或交易權限。

## 0. 研究的真正目標
以可合法、持續、按歷史時間取得的可靠資料，使用經濟學、財務金融、計量經濟學與可重現統計方法，檢驗是否能改善資產未來報酬及風險的預測，最後才評估扣除交易成本後的風險調整報酬。

「全球資金流向」是**待驗證的候選解釋變數**，不是已確立的 alpha、不等於可追蹤全球每一元貨幣，也不是強制導向的產品架構。若其他模型優於資金流模型，採用較優方法；若無可交易增益，停止擴大投資。

## 1. 可確認的理論事實 vs. 待驗證推論
**經濟與會計基礎（可從官方文獻支持）**
1. 廣義貨幣含銀行存款，銀行放款可創造存款，償還本金可消滅存款；不能假設除中央銀行操作外總貨幣數量固定。官方概述：[Bank of England](https://www.bankofengland.co.uk/explainers/how-is-money-created)。
2. 買賣既有證券的款項由買方移至賣方；不能把成交量、基金申贖、市值變動、淨國際資本交易視為相同數量。金融資產期末存量變化可拆為「交易 + 重估 + 其他數量變動」：[Federal Reserve Z.1](https://www.federalreserve.gov/RELEASES/z1/current/introductory_text.htm)。
3. 市場價格由邊際定價決定；市值波動可以遠超過同期成交現金金額。價格重估可能經抵押品、保證金與去槓桿管道影響後續交易。
4. M2、跨境信用、基金流量、期貨持倉各有不一致的定義及覆蓋範圍，**不可直接加總成全球可用資金，也不可將不同市場的「淨流入」機械地相互抵銷**。
5. 價格變動也可能影響資金流；相關性不等於因果性。公開可見的資金流資訊可能已被市場定價，也可能滯後於價格。

**尚未驗證的假說**：可觀察的資金、貨幣與信用變數是否提供超越價格、利率與傳統金融變數的增量樣本外預測能力？它是否帶來扣除成本後可用的投資效益？這兩項答案目前均為 UNKNOWN，不得宣稱有 alpha。

**反對證據／研究警訊**：[Welch & Goyal (2008), Review of Financial Studies](https://doi.org/10.1093/rfs/hhm014) 對多種股票溢酬預測因子發現歷史樣本外表現不穩定；[Campbell & Thompson (2008), RFS](https://doi.org/10.1093/rfs/hhm055) 指出理論限制與合理約束可能改善比較結果。不能只選支持某一立場的文獻。預測模型選擇本身也有資料探勘偏誤風險。

## 2. 第一期唯一主要研究問題（Primary Question）
**公開貨幣、信用與資金流資料，能否增加「未來約一個月美國股票相對可投資短期美元現金部位」的超額總報酬預測能力？**

- 決策頻率：每月一次。訊號截點為當月最後一個美股交易日 16:00 America/New_York（需正確處理 DST）；只允許此截點前已公布的資料。
- 交易可行性：不允許假設可以在 16:00 看到收盤價後又以同一收盤價成交。經濟性模擬預設在下一個交易時段可執行的價格建倉（具體執行時點需在資料稽核後凍結）。
- 結果變數：下一持有月份的股票**含股息總報酬**減去同期短期美元現金／國庫券**可投資總報酬**。資料與代理標的（含股息、費用、滑價及完整歷史）需完成授權、可用性與 PIT 查核後才正式凍結；不可事後選擇較漂亮的 proxy。
- 美股大盤價格指數、ETF 市價、指數總報酬、期貨連續價格不能混為一談。若無合法、可驗證歷史總報酬序列，第一輪量化研究標記 BLOCKED，不以價格指數硬充總報酬。
- 其他市場（美債、黃金、台股、巴西、商品）留待第一輪 Go 後擴展，不得在看到結果後納入或排除主要檢驗樣本。

### 預先登錄的競爭模型
- **M0：基準**。歷史已實現股票超額報酬的擴展樣本均值（只用截點前資料）；另列零超額報酬/100%現金為投資基準。基準不可省略。
- **M1：傳統金融**。M0 加入事前固定的價格動能、波動率、利率期限差、信用利差等候選，先採低維度、具懲罰的線性模型；需事前確定資料取得方式與變數轉換。
- **M2：增量資金流**。在完全相同 M1 的樣本、切分、交易假設上加入已通過資料門檻的貨幣、信用、跨境交易/基金流或持倉訊號；對比 M1 的增量表現，不允許改變其他條件。

**零假說 H0**：M2 相對 M1 沒有可重複、扣除成本後的樣本外改善。研究不能以「假定資金必有去處」作為拒絕 H0 的理由。

## 3. 候選資料清冊（僅確認來源概念；尚未驗證完整資料與可交易用途）
| 層次 | 首選來源 | 頻率/注意事項 | 第一輪用途 |
|---|---|---|---|
| 貨幣存量 | [Fed H.6](https://www.federalreserve.gov/RELEASES/H6/About.HTM)；[ALFRED](https://fred.stlouisfed.org/docs/api/fred/alfred.html) | 月度、口徑及修訂需記錄；不得直接全球 M2 加總 | M2候選 |
| 金融體系資產負債表 | [Fed Z.1](https://www.federalreserve.gov/RELEASES/z1/current/introductory_text.htm) | 季度且延遲；交易/重估/其他變化分開 | 概念與低頻驗證 |
| 跨境信用 | [BIS Global Liquidity Indicators](https://data.bis.org/topics/GLI) | 季度；各貨幣信用及銀行貸款/國際債券覆蓋範圍有限；修訂存在 | 次階段或月度低頻候選 |
| 美國跨境證券交易 | [US Treasury TIC](https://home.treasury.gov/data/treasury-international-capital-tic-system/)；[統計定義](https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/ticsecd) | 月度且有公布延遲、交易地/保管地偏差；「買賣」不等於股市資金總流 | M2候選 |
| 投資者部位 | [CFTC COT](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm) | 報告日 ≠ 持倉日；發布頻率可能變更；未平倉量≠現金流 | M2候選 |
| 基金申贖 | [ICI flows](https://www.ici.org/research/stats/flows) | 週資料可能是估計值，月資料與週估值不一致；需分基金類型 | M2候選 |
| 融資與利率 | [NY Fed SOFR](https://www.newyorkfed.org/markets/reference-rates/sofr)；FRED/ALFRED | 利率與實際放款額不同；須合併期限利差/信用利差 | M1候選 |
| 可投資總報酬 | 交易所/基金發行人/合法授權歷史資料，待選 | 需權息調整、執行可得性、價格時間戳、資料權利 | 結果與基準 |

所有變數逐一記錄：定義、單位、季調/名目實質、地區、原始發布 UTC、實際抓取 UTC、最新修訂 vintage、已知歷史變更、可用樣本期、缺漏比例、授權、來源 URL；只有拿到原始位元組才填原始 SHA-256。FRED/ALFRED 的 vintage 日期不一定證明日內幾點可得：日內時間無法確認時，保守延後至**下一個可確證交易截點**使用。價格資料也須檢查除權息生效與實際可見時間。

## 4. 研究方法與事前防作弊
1. **資料門檻先於建模**：先核對來源、API/下載權利、歷史版本、公布延遲和樣本長度，再決定某變數能否入模。若主要資料不可得，不能以事後補值偽造 PIT；可進行明確標示的探索性研究但不能作為正式 Go 證據。
2. **時間序列樣本外**：採擴展式或滾動式起點（walk-forward），每個預測只使用當時可得資料。正式起訖、訓練期、模型調參規則、缺值規則與特徵定義在看到保留樣本結果前凍結。初步可行性參考：至少約 120 個月訓練、60 個月獨立檢驗；不足則列資料限制，不以低樣本宣稱成功。
3. **避免重疊標籤／洩漏**：採月度再平衡、各期實際持有區間；若區間或資料頻率導致重疊，使用適當分組、封鎖/間隔或自相關穩健推論；標準化、填補與超參數僅可在每個訓練視窗內估計。
4. **模型數量治理**：M0/M1/M2 為預設主比較，不因結果差就擴大搜尋。後續任何特徵、回測區間與優化只能標記探索性，另立研究登錄，不能回填原先的驗證主張。
5. **度量**：報酬預測的 out-of-sample R² / MSE 相對 M0 及 M1、校準/方向指標（次要）、時間序列穩健信賴區間、各市場狀態結果；無統計可信度時不強述正效果。若做方向機率預測，須先定義並檢查 Brier/校準，不能將方向正確率當獲利。
6. **經濟性檢驗**：以事前固定、具可執行價格與不同比率交易成本/滑價、週轉率、融資/ETF費用、最大回撤、波動與簡單現金/股市被動持有策略比較。限制槓桿，避免使用未確認的放空或衍生產品。經濟表現與統計預測能力分開呈現。
7. **可反駁與反向因果**：比較「價格變動先於資金流」的替代模型；區分預期變化與出乎預期的新資訊；對市場極端期、資料修訂、不同交易成本和樣本期間進行事先指定的敏感度測試。
8. **獨立審查**：由未參與特徵挑選的審查者核查時間戳、樣本外切分、來源權利、多重比較與後見之明。多 Agent 僅在任務可真正拆分時使用；分工計畫不代表已啟動。

## 5. Gate / Stop 規則（不把探索性結果升級為投資資格）
- **Gate 0 DATA**：至少有完整可合法使用的股票與現金總報酬、歷史訊號、各自發佈時點與可保守重建的歷史資料版本；不滿足 → BLOCKED 或修小範圍。
- **Gate 1 REPRODUCIBLE**：固定程式、資料版本、參數、環境與隨機種子；他人可重算 → 才能進入 Gate 2。
- **Gate 2 INCREMENTAL**：M2 是否在預留/滾動樣本外**穩定**優於 M1（以及 M0）？報告效應大小、不確定區間與多重嘗試修正；沒有足夠證據 → NO-GO（停止增加資金流特徵），但可保留其他模型。
- **Gate 3 ECONOMIC**：扣除不同合理成本假設後是否有持續風險調整報酬改善、可承受回撤、可重現交易信號？不滿足 → 不升級交易應用。
- **Gate 4 FORWARD PAPER**：只有前面通過後才進行事先登錄的前瞻紙上追蹤；歷史回測成功≠前瞻成功≠可直接用真實資金交易。
- 研究每次呈現 **PASS / FAIL / BLOCKED / NOT_TESTED** 與原因，不能用主觀「看起來有用」取代。正效果也不能保證未來獲利。

## 6. 分階段交付、責任與成本
| 工作 | 主要交付 | 初步工期（不保證） | 停止條件 |
|---|---|---|---|
| R0 研究章程 | 本文件，對立假說、主檢驗、門檻 | 本輪 | 不納入程式/抓取/部署 |
| R1 資料審核 | 具來源版本與延遲的資料清冊、許可檢核、可行樣本矩陣 | 第1–2週 | 無可靠 PIT/權利 -> BLOCKED |
| R2 基準實驗 | M0/M1/M2 可重現回測、凍結設定、來源清單 | 第2–3週 | 無法固定回測則不做績效報告 |
| R3 獨立驗證 | 樣本外與風險/成本報告、獨立反證 | 第3–5週 | 无增量證據 -> NO-GO |
| R4 Go/No-Go | 是否投入後續前瞻研究之決策 | 第5–6週 | 無效就停止擴大開發 |

時程僅是**規劃估計**，不表示已執行 Agent、已取得資料、已驗證模型。先沿用 SIGNAL 既有研究證據與日期/版本規範，避免建立第二套資料管線。僅在正式授權後新增代碼、排程、付費資料或交易執行。

## 7. 適用範圍／不變更宣告
- 不更改 SIGNAL K4 玉米、K5 天然氣事前預測、發布時間、既有研究 PR、已凍結來源資料。
- 不合併 main、不部署、不交易、不接券商、不採購付費資料、不修改 secrets。
- 本文件的引用確認來源**存在且描述符合**，不等於已下載原始資料、驗證最新數值、驗證權利或證明可重現回測。
- Agent A 資料/PIT、B 競爭模型、C 反證 QA、D 投資可行性：**PROPOSED，不得稱已啟動**。
- 下個明確行動：R1 唯讀 source feasibility + PIT matrix。需先以小量核心來源做否決式評估，不擴張到全球所有市場。

## 8. 參考依據（已檢查官方定義／學術摘要，尚未進行全文系統性回顧）
- Bank of England, *How is money created?* https://www.bankofengland.co.uk/explainers/how-is-money-created
- Federal Reserve, *Z.1 Financial Accounts Introductory Text*. https://www.federalreserve.gov/RELEASES/z1/current/introductory_text.htm
- Federal Reserve, *Money Stock Measures H.6*. https://www.federalreserve.gov/RELEASES/H6/About.HTM
- Federal Reserve Bank of St. Louis, *ALFRED API*. https://fred.stlouisfed.org/docs/api/fred/alfred.html
- BIS, *Global liquidity indicators*. https://data.bis.org/topics/GLI
- U.S. Treasury, *TIC system*. https://home.treasury.gov/data/treasury-international-capital-tic-system/
- CFTC, *Commitments of Traders*. https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
- ICI, *Estimated long-term mutual fund flows*. https://www.ici.org/research/stats/flows
- Federal Reserve Bank of New York, *SOFR*. https://www.newyorkfed.org/markets/reference-rates/sofr
- Welch & Goyal (2008), *A Comprehensive Look at the Empirical Performance of Equity Premium Prediction*, RFS. https://doi.org/10.1093/rfs/hhm014
- Campbell & Thompson (2008), *Predicting Excess Stock Returns Out of Sample*, RFS. https://doi.org/10.1093/rfs/hhm055
- Newey & West (1987), *HAC covariance estimation*, NBER. https://www.nber.org/papers/t0055

