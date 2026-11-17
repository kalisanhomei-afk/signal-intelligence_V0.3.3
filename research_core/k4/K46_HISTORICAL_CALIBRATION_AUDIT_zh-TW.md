# K4.6｜USDA 玉米歷史修訂標籤／FGIS 時間版本驗收（2026-11-17）

> **歷史狀態更新（2026-11-17）：** 本文件記錄 K4.6 當時尚未取得 2017–2020 舊資料包的階段性結果。K4.7 已在 USDA 官方鏡像成功下載並驗證該 ZIP、補齊四年，總計九年度標籤。請以 [K4.7 九年稽核](K47_NINE_YEAR_SOURCE_VINTAGE_AUDIT_zh-TW.md) 為最新進度。**只有官方答案標籤補齊，FGIS 當時可得特徵仍未完成 PIT 認證。**


**結論：歷史 WASDE「公告版本的修訂答案標籤」已取得 5 年；出口檢驗歷史 API 可讀，但獨立事前版本未認證。NO CALIBRATED V1 / NO BACKTEST / NO TRADE。**

## 實際交付
- `wasde_revision_labels.py`：從 USDA 官方當月歷史 CSV 限定 `ReportTitle = U.S. Feed Grain and Corn Supply and Use`、`Commodity = Corn`、`Region = United States`、`MarketYear = 當年/次年`、`ProjEstFlag=Proj.`、`Unit=Million Bushels`、`Attribute=Exports / Ending Stocks`。驗證 ForecastYear / ForecastMonth、公告日期與年度一致，拒絕重複或缺少資料；處理 USDA 2021 年 `MM/DD/YYYY` 與近年 `YYYY-MM-DD` 的實際格式差異。
- `cases/2021-2025-official-wasde-december-corn-revision-evidence.json`：保存五年度可核對的標籤、公布日期、官方原始 CSV URL 與每份取得時的 SHA-256；不公開重新分發原始 CSV 位元組。
- `historical_source_probe.py`：官方來源／欄位識別預檢；公開 FGIS Socrata API `https://agtransport.usda.gov/resource/sruw-w49i.json`，已驗證 `date`、`grain`、`mt` 等欄位及 2025/11 玉米每週彙總回覆。
- CI 驗證（2026/11/17）：[GitHub Actions #43996982886](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/43996982886)，**128/128 測試 PASS**；九年度批次嘗試，5 筆完成、4 年來源缺口，禁止將缺口填零。後續追加固定快照契約測試，CI 需另驗收。

## USDA 真實的月度修訂（單位：百萬蒲式耳）

| 當期行銷年度 | 11月出口 | 12月出口 | 出口變動 | 11月期末庫存 | 12月期末庫存 | 庫存變動 | 其他供需淨變動 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021/22 | 2,500 | 2,500 | 0 | 1,493 | 1,493 | 0 | 0 |
| 2022/23 | 2,150 | 2,075 | −75 | 1,182 | 1,257 | +75 | 0 |
| 2023/24 | 2,075 | 2,100 | +25 | 2,156 | 2,131 | −25 | 0 |
| 2024/25 | 2,325 | 2,475 | +150 | 1,938 | 1,738 | −200 | −50 |
| 2025/26 | 3,075 | 3,200 | +125 | 2,154 | 2,029 | −125 | 0 |

**重要**：2024/25 期末庫存 −200 不全是出口 +150 導致，尚有其他供需項目淨影響 −50。不能以 `Δstocks = −Δexports` 當作每年恆等式；真正的平衡式還包含產量、期初、其他使用／貿易變化。

## 來源實際發現／缺口
- USDA OCE 2010 年至今歷史原始報告資料索引：https://www.usda.gov/oce/commodity-markets/wasde/historical-wasde-report-data ；同官網索引鏡像亦可見 https://usda.azureedge.us/historical-wasde-report-data-3 。
- 2021–2025 逐月 CSV 的官方固定路徑 `https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-YYYY-MM.csv` 可下載，實際公告日期在資料列 `ReleaseDate`，但 **GitHub Runner 的 2026-11-17 事後取件時間不等於 2021–2025 事件發生前來源已被不可竄改封存**。
- 2017–2020 的 USDA 官方索引顯示集中 ZIP：`https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-2016-01-to-2020-12.zip`，**本次 Runner 直接取得 ZIP 遭 HTTPError**。此四年 `UNVERIFIED`，並不是修訂量為零；勿從相鄰年份插值。
- FGIS 歷史 API 已成功回傳 2025-11-06 / 11-13 / 11-20 / 11-27 的玉米週別檢驗彙總；但這是查詢**目前資料庫**的歷史紀錄，可能含後續更正，不提供獨立的當週首次公開 snapshot、as-of 時間。因此一律標記 `RETROSPECTIVE_FEATURE_NOT_PIT_CERTIFIED`，**禁止直接將其和 USDA 修訂標籤結合聲稱無前視偏差回測**。
- USDA FGIS Weekly Grain Inspections 是已檢驗出口（physical inspection），FAS Export Sales 是承諾／銷售，量測定義與時間不同。調校前須明確設定季節性、市場年度起始、週結束日、官方發布時點及必要控制。

## 下一階段必要條件（非功能清單）
1. 原始 **截至公告前**可得的 FGIS 每週資料首次版本封存或保守 as-of 規則與修訂歷史，連同原始 SHA-256。
2. 至少形成可分開測試的歷史「輸入特徵」與「次月出口修訂答案」。在獨立時間驗證與資料量不足前，不訓練聲稱可交易的模型。
3. 預先指定年度走向的 walk-forward 驗證、上期值延續基準、季節／出口進度控制與不同年度穩健性；明確承認 n=5 不足以可靠估計多變量模型。
4. 繼續保留 2026/12 已封存 V0 = 1,758 百萬蒲式耳；此處沒有新增 12 月 V1 點預測。市場共識追蹤另行運作（官方公告預定 2026-12-10 17:00 UTC）。

**Gate:** LABEL_SCHEMA_AND_SHA_RECEIPTS_PASS；FOUR_OLDER_YEARS_BLOCKED；FEATURE_ASOF_UNVERIFIED；V1_ABSTAIN；TRADING_NO_GO；PR #22 Draft isolated, no main merge.
