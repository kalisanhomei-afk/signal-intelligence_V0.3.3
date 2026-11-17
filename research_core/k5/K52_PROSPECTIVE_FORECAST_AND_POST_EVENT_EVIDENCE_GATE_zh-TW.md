# SIGNAL K5.2｜公告前外部預測快照與原始 EIA 公告後驗收（2026-11-17）

**驗收結論：** `SOURCE_PRE_EVENT_METADATA_PARTIAL`、`FROZEN_V0_INTACT`、`POST_EVENT_RAW_VALIDATOR_READY`、`EIA_2026-11-19_NOT_RELEASED`、`ANALYST_CONSENSUS_UNCERTIFIED`、`V1_ABSTAIN`、`NO_TRADING`。

## 1. 已封存的預測基準

- 美國 EIA WNGSR，預定 2026-11-19 15:30 UTC 發布 2026-11-13 週結束日的 Lower 48 working gas weekly net change，單位 Bcf。
- **SIGNAL 事前 V0 = +61 Bcf**（2026-11-17 已提交；完全沿用上一週 EIA 值），位於 `cases/2026-11-19-eia-frozen-v0-forecast.json`，原 Git blob SHA-1 `bacc82f549fb3bba74142139d89bec94e386d88e`。任何位元組修改皆被新評分程式拒絕。
- 前期 EIA 11/13 公布的 JSON 原始來源 **7,197 bytes**，SHA-256 `6eb6c699b789d7130d3f50dbe5681e835b57bc25dd118380398169dda63fe252`，當時已驗證為 11/06 週庫存 3,862 Bcf、前週 3,801 Bcf、淨增加 61 Bcf。原件和捕獲回執維持不變。

## 2. 11/19 公告前查到的第三方候選數值（不可混為市場共識）

**已真實由 GitHub Actions HTTP 取得且保留數據摘要：**

| 來源 | GitHub 2026-11-17 驗證 | 數值 | 性質 |
|---|---|---:|---|
| MetaTrader 經濟日曆 | HTML 151,191 bytes，SHA-256 `bd465faf5b3818a20a822960ce47c62ec2727f04eff8ff844df24e3e27e9919d`；11/17 03:24:50.774100Z 捕獲 | +69 Bcf | **日曆預測欄值**，來源未提供獨立的調查方法／首次發布時間，不能標成可靠分析師共識 |
| Arc Research Scorecard | 搜尋引擎／網頁閱讀器曾呈現 +13.4 Bcf、週截至 11/13；但 GitHub 實際 HTML 的當期數值與預設解析值**不一致**，驗收 `WEB_EXPECTED_NUMBER_DIFFERENT` | **不驗收** | 單一機構模型報價，即使成功也不是市場共識；不可追認為固定發布版本 |

來源：
- <https://www.metatrader.com/en/economic-calendar/united-states/eia-natural-gas-storage-change>
- <https://www.getarcresearch.com/commodities/natural-gas/scorecard/>
- 第一次一次性實際擷取 GitHub Actions [#44010006480](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/44010006480)；本次對照原始來源只有網頁位元組 SHA 回執，**未將第三方完整 HTML 重新公開發布到 Repository**，因此網址後續更新時不保證可再從網站取得完全相同位元組。應以實際捕獲 UTC 和本次摘要為限。
- 緊縮版觀測證據：`cases/2026-11-19-pre-release-external-forecast-receipts.json`，保留 Arc 無法驗證原因與 MetaTrader 來源 SHA／捕獲 UTC；`market_analyst_consensus_certified=false`。
- **重要限制**：報告預估與市場調查可能在 11/19 正式公布前更新。來源頁面當前呈現預測值，不代表「首版發布時間」已獲獨立認證。

## 3. 公告後不可用人工數字／假 SHA 冒充真實回測

新增 `research_core/k5/official_event_score.py`。必須：
1. 從之前封存的 K5 V0 **原始 JSON 位元組**重算 Git Blob SHA-1，與事前的 `bacc82f5…` 一致；
2. 將已提交 EIA 11/13 原始 JSON 與 receipt 逐位元組驗證前次 3,862／3,801／+61；
3. 新增真正**11/19 公告後**官方 EIA JSON 原始位元組以及來源 URL／取得開始及結束 UTC／SHA-256；
4. 自原始 JSON 解析唯一的 `png.nw2_epg0_swo_r48_bcf.w`、`current_week=2026-11-13`、`week_ago=2026-11-06`、`net_change` 與本週／前週庫存；不能接受其他區域、前一週報告或只有一個人工輸入的數值；允許 EIA 對上週庫存修訂，但一定要列出修訂差額；
5. 僅在真實原始來源與回執驗證成功後計算 `abs(官方 11/19 net_change − 61)`，輸出**單事件描述性誤差**。不會宣稱預測能力或交易優勢。

新 `research_core/k5/eia_postrelease_capture.py` 提供「**公告後才可執行**」的一次性安全下載及證據配對流程：

```bash
# 僅供研究 Agent 在 EIA 真正公告後執行，2026-11-17 不要執行
python -B -m research_core.k5.eia_postrelease_capture \
  --output-dir k5-new-event-staging
```

若實際日期尚早於 2026-11-19 15:30 UTC，**不發送 EIA 網路請求**；若 EIA 官方端點尚未更新成 11/19 的資料，拒絕舊版，不產生新有效紀錄。若成功，輸出帶 SHA 的三份文件（原始 JSON／捕獲回執／V0 誤差結果），不覆寫已存在的證據。可再用以下程序獨立驗算：

```bash
python -B -m research_core.k5.official_event_score \
  --event-raw k5-new-event-staging/EIA_WNGSR_20261119_<sha16>_original.json \
  --event-receipt k5-new-event-staging/EIA_WNGSR_20261119_<sha16>_receipt.json \
  --output k5-new-event-staging/verified_score.json
```

*請以實際程式輸出的 SHA16 檔名代入，不是現在已存在的檔名。*

在 11/17 尚未有結果，故直接執行 `python -B -m research_core.k5.official_event_score --output local-score.json` 必須產生 `WAITING_FOR_NOV19_OFFICIAL_EIA_ORIGINAL`、`actual_net_change_bcf=null`、`v0_absolute_error_bcf=null`。

## 4. 驗收及停止條件

- [GitHub Actions #44010297195](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/44010297195)：**55/55 Python tests PASS**，全部未發布日的「EIA 數值」均只是明確標註的合成測試 fixture，不是 11/19 真值。後續 doc commit 另行驗收。
- 本次只保留外部候選來源的取得回執；一次性外部網路擷取 job **已移除**，避免每個 PR 更新重新擷取會改變的網站內容。
- 已在既有「SIGNAL K5 天然氣首輪驗收」排程安排台灣時間 **2026-11-19 21:00** 事前共識查核，**2026-11-20 09:00** 正式 EIA 結果查核。後續若能取得可靠更完整的分析師調查、可證明發布時序，再形成市場共識比較；本期不因 MetaTrader 日曆有值就宣布共識已認證。
- **不要**在 11/19 事後看到價格變動再調整 +61、事件定義、誤差規則或選擇性捨棄不同預測。
- 預測氣象模型 V1 仍欠 NOAA 事前預報版本與供需變數的獨立時序證據；暫停新增指標或開設第三條商品研究線。

**K5.2 工程判定：Go（來源及評分關卡可使用），預測與投資判定：No-Go（沒有 alpha 或交易驗證）。** 與 K4 PR #22 平行隔離；K5 PR #23 維持 Draft，不合併 main、不購買交易行情、不下單。

## 5. 2026-11-17 端到端預演與同日重試安排

公告前再次查核 EIA 官方 2026-11-19 10:30 ET（台灣 23:30）事件日期與前期原始 JSON。對新 `eia_postrelease_capture.py` 的原件落地程序修正為 **O_EXCL／獨占建立**，即使兩個 Worker 先後競爭取得相同檔名，也不會覆寫另一個 Worker 的原始檔；只回滾本次執行已建立的檔案。新 56 項 CI 測試包含「其他 Worker 先建立回執，保留原件且不刪除別人的回執」之反證。

原有 K5 自動任務改為三次：**11/19 21:00**（公告前共識）、**11/20 09:00**（公告後正式來源）、**11/20 21:00**（同事件備援）。如果上午成功，晚間不重複封存；若因 404、尚未更新或 GitHub 權限受阻，晚上重試**相同 11/19 報告**，不必等下一週新資料。

重要：GitHub 研究分支的 CI 通過，並不自動證明自動化任務執行時有 GitHub 寫入權限；任務被設定為每次回報真正完成／BLOCKED。正式下載仍以當時網路、EIA 公告和 GitHub 權限為準，不能宣稱零外部風險。
