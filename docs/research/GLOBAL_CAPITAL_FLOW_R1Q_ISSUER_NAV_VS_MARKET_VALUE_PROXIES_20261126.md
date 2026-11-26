# SIGNAL R1q | State Street NAV 與 Market Value：2026-06-30 雙標的公開績效的獨立比較

**日期 2026-11-26 / 證據分類 OFFICIAL_PUBLIC_AGGREGATE_COMPARISON / 非 API 歷史原始價格 / 非 PIT 模型准入。** 繼前次 SPY/BIL 三本 XLSX 的 NAV 含息重建 28/28 issuer NAV 抽查通過之後，本次不重算既有結果、不下載或提交受限原始工作簿；改用發行人**另列的 Market Value 報酬**，直接檢查「NAV 能否代理真實市場價格」的誤差。

## 1. 同一 as-of 日期、同一基金、同一績效種類

**日期 2026-06-30；百分比為發行人表列至小數點後兩位**。所有差額定義 = **Market Value − NAV，單位 basis point（bp）**，不能等同「實際滑價」，亦不能拿不同期間的值相加。

| 標的 | 期間 | NAV total return | Market Value total return | Market minus NAV |
|---|---|---:|---:|---:|
| SPY | 1 Month | -0.96% | -1.07% | **-11 bp** |
| SPY | QTD | +15.17% | +15.08% | **-9 bp** |
| SPY | YTD | +10.13% | +10.02% | **-11 bp** |
| SPY | 1 Year | +22.15% | +22.08% | **-7 bp** |
| BIL | 1 Month | +0.29% | +0.28% | **-1 bp** |
| BIL | QTD | +0.88% | +0.88% | **0 bp** |
| BIL | YTD | +1.74% | +1.74% | **0 bp** |
| BIL | 1 Year | +3.83% | +3.82% | **-1 bp** |

第一手公開來源：
- SPY：https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy （`Fund Performance / Fund Before Tax / NAV` 與 `Market Value`；截至 2026-06-30）。
- BIL：https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-bloomberg-1-3-month-t-bill-etf-bil （相同欄位及 as-of）。

**關鍵新事實**：先前的三本 XLSX 成功重建 28 個 NAV 觀察，卻**沒有**證明那就是以市場價格投資所能實現的報酬。對本次同一官方表格，SPY NAV 與 Market Value 差額可達 11bp，BIL 也可達 1bp。當研究要判定細微 alpha，單憑 NAV 代理可能改變優劣判斷。

## 2. 為何 Market Value 仍不是可執行報酬

State Street 在產品頁載明 Market Value return 依基金計算 NAV 當時之**交易所最佳買賣報價中點（bid/ask midpoint）**估算。該點位並非必然可於指定交易時段實際成交的價，也不包含個別投資人之訂單方向、spread paid、佣金、滑價、稅務及下單可得性；若研究策略規則是在月末 **16:00 ET** 才決定持倉，不能假設已能於該時刻的 midpoint 或 NAV 成交。表中顯示值亦僅有 0.01 percentage point 精度；例如列 0bp 不代表兩系列未四捨五入的報酬完全相同。

因此：
- `NAV_TOTAL_RETURN_PROXY=DESCRIPTIVE_PUBLIC_FEASIBILITY_ONLY`。
- `ISSUER_MARKET_VALUE_TOTAL_RETURN=AGGREGATE_INDEPENDENT_BENCHMARK_ONLY`。
- `NEXT_TRADABLE_SESSION_EXECUTION=NOT_VERIFIED`。
- `HISTORICAL_MONTHLY_MARKET_VALUE_SERIES=NOT_ACQUIRED`。
- `PIT_SOURCE_VINTAGES=NOT_VERIFIED`。
- `COMMERCIAL_DATA_RIGHTS=NOT_VERIFIED`。
- `FORMAL_R1_GATE0=BLOCKED`; `R2_NOT_STARTED`; `NO_TRADING`。

## 3. 低成本研究決策（避免過度延伸）

1. **探索性關聯研究**可把已有 NAV 資料視作具限制的「基金價值變化代理」，但僅在符合資料使用條款及 PIT 閘門後，才准許訓練/回測模型；目前**不可自行將它升級成正式 M2 因子回測**。
2. **正式可交易 SPY 相對 BIL 報酬驗證**不能單憑兩檔 NAV Excel 或上表的八組匯總值。仍需下一交易時段的合法市場成交價格、股息/分割完整方法及費用模型；若之後確認實際有不可替代資料缺口，再評估供應商，不要現在購買。
3. 本次已驗證差額，**不為了追求極小精度重跑既有 28 個 NAV 對照**；也不需要重試未獲一手證實之 BIL 2008 原始配息日期。等待新證據可取得時再解除個別隔離。

**本次真實新增：** 8 個相同 as-of 的 issuer NAV vs issuer Market Value **公開匯總績效差異**，並明確區分「已能研究 NAV」與「已證明可交易 alpha」。沒有產生任何原始價格檔案、實際交易回測、供應商採購或出站郵件。
