# SIGNAL K4.7｜2017–2025 玉米 11→12 月官方修訂版本完整稽核（2026-11-17）

**決策：九年 USDA 官方「當時公布數值」修訂標籤 COMPLETE；獨立 FGIS 事前特徵 PIT 未驗收，V1 預測與交易 NO-GO。**

## 1. 已取得的真實資料

經 USDA 官方鏡像 `https://usda.azureedge.us/sites/default/files/documents/oce-wasde-report-data-2016-01-to-2020-12.zip` 實際下載並解壓；相較之下主站同一路徑在 GitHub Runner 回覆 403。

- 原始 ZIP 大小：2,419,809 bytes
- ZIP SHA-256：`1cffbc4aa0ec436c832afb306b19631eaac42c2aaf3fffbf8dd9923052bfefb5`
- ZIP 內唯一原始 CSV：`oce-wasde-report-data-2016-01-to-2020-12.csv`
- 原始 CSV 解壓大小：56,391,737 bytes
- CSV SHA-256：`4592a608708310a8cc92226f47eac5dacebcf4fad21cde879034a80c67efa89a`
- 完整提取回執（GitHub Actions）：https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/43998393195
- 2017–2020 已把各月 selected rows SHA 分別保存於 `cases/2017-2020-official-wasde-december-corn-revision-evidence.json`。**要區分原始 ZIP/CSV SHA 與衍生列集 SHA；不能互相冒用。**
- 2021–2025 從官方逐月 CSV 擷取並保存每份來源 SHA，見 `cases/2021-2025-official-wasde-december-corn-revision-evidence.json`。

## 2. 9 個行銷年度連續修訂標籤

固定篩選：`ReportTitle=U.S. Feed Grain and Corn Supply and Use`、`Commodity=Corn`、`Region=United States`、`MarketYear=當年/次年`、`ProjEstFlag=Proj.`、`Unit=Million Bushels`，使用個別報告當年 `ForecastYear/ForecastMonth/ReleaseDate`，不可混入 USDA「Reliability of ... Projections」統計或前一年 `Est.`。

| 行銷年度 | 11月出口 | 12月出口 | 出口修訂 | 11月庫存 | 12月庫存 | 庫存修訂 |
|---|---:|---:|---:|---:|---:|---:|
| 2017/18 | 1,925 | 1,925 | 0 | 2,487 | 2,437 | −50 |
| 2018/19 | 2,450 | 2,450 | 0 | 1,736 | 1,781 | +45 |
| 2019/20 | 1,850 | 1,850 | 0 | 1,910 | 1,910 | 0 |
| 2020/21 | 2,650 | 2,650 | 0 | 1,702 | 1,702 | 0 |
| 2021/22 | 2,500 | 2,500 | 0 | 1,493 | 1,493 | 0 |
| 2022/23 | 2,150 | 2,075 | −75 | 1,182 | 1,257 | +75 |
| 2023/24 | 2,075 | 2,100 | +25 | 2,156 | 2,131 | −25 |
| 2024/25 | 2,325 | 2,475 | +150 | 1,938 | 1,738 | −200 |
| 2025/26 | 3,075 | 3,200 | +125 | 2,154 | 2,029 | −125 |

單位：百萬蒲式耳；修訂為 12 月公布值減 11 月公布值。

- 出口有修訂：4/9 年（2022/23–2025/26）。
- 期末庫存有修訂：6/9 年。
- 期末庫存修訂非全由出口引起：2017/18、2018/19、2024/25 有非出口供需變動。
- 以上是**描述性計數**，不是策略勝率或模型表現；n=9 年仍不足以估計穩健多變量模型。

## 3. 現存證據缺口

1. USDA WASDE 報告版本可觀測的資料是 **答案標籤**。對 2017–2025 每年 12 月當時的出口檢驗特徵，還沒有逐週第一版與更正記錄的獨立 SHA／可信捕獲 UTC。
2. 現在從 USDA Socrata FGIS API 查歷史日期，可能含事後修訂，因此是 `RETROSPECTIVE_FEATURE_NOT_PIT_CERTIFIED`。不可直接稱作「無時間穿越的回測」。
3. AMS 官方搜尋指南說 dated report 與 rolling `mnreports` 不同，但本次直接從 MMN 動態報告庫查詢 dated 檔案 API 發生網路失敗；**不能宣稱已拿到 9 年原始 FGIS 週報**。官方指南：https://www.ams.usda.gov/market-news/search-tips
4. 公告前 2026/12 的市場共識尚待可稽核來源；既有基準 `USDA_PREVIOUS_WASDE_PERSISTENCE_V0=1,758` 百萬蒲式耳保持原封不動。

## 4. 可重現工程與驗收

- `research_core/k4/wasde_historical_zip_labels.py`：有界、單次遍歷官方 ZIP CSV，提取 2017–2020 年，不輸出原始 56MB 內容，不宣稱獨立交易 PIT。
- `research_core/k4/nine_year_revision_catalog.py`：離線合併 2017–2020 ZIP 標籤與 2021–2025 官方逐月 CSV 標籤，驗證 9 年連續、年度順序、修訂算式及非出口淨變動；明確禁止自動轉成模型特徵或交易資格。
- `research_core/k4/tests/test_wasde_historical_zip_labels.py`、`test_nine_year_revision_catalog.py`：未知格式拒絕、缺值不得當零、同一行銷年度、防止虛偽 PIT 等。
- 自動驗收：GitHub Actions [#43998763582](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/43998763582)，**149/149 Python tests PASS**、9 年 catalog PASS；原始官方來源下載成功，正式報告未公開含授權限制的 Databento 期貨原始資料。

## 5. 下一步決策

**先解決可時序驗證的出口檢驗資料來源，而不是使用九年答案標籤訓練並過度擬合。** 有希望的路線是 USDA AMS 歷史 `WA_GR101` 的按日期封存原始 TXT/PDF 與更正紀錄；若無法在合理成本取得，就應將歷史模型留在探索層，改走 K3.8 和當前 forward FGIS 的**未來資料捕獲實驗**，累積真正前瞻可用的 as-of 樣本。

**Gate:** `HISTORIC_USDA_OUTCOME_LABELS_9_PASS`、`FGIS_HISTORICAL_ASOF_UNVERIFIED`、`MODEL_V1_ABSTAIN`、`TRADING_NO_GO`。PR #22 繼續 Draft，禁止合併 `main`。
