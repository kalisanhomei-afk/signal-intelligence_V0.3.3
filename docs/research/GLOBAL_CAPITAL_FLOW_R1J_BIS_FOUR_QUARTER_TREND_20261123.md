# SIGNAL R1j｜BIS 境外美元信用四季走勢與研究假說證據（2026-11-23）

**狀態：FOUR_QUARTER_EXTERNAL_REPORT_PASS / DESCRIPTIVE_ANALYSIS_ONLY / HISTORICAL_PIT_BLOCKED / GATE0_BLOCKED。** 本文件據使用者提供的 Antigravity 本機唯讀 CSV 解析紀錄；Antigravity 直接保存原始 ZIP/receipt、複核 SHA，ChatGPT 未取得原始 bytes，僅獨立重算貼文內的有限數值。沒有重新下載 BIS，未訓練正式模型、不付費、不交易。

## 1. 來源與證據身分

來源：Bank for International Settlements (BIS), Global Liquidity Indicators (GLI) / BIS WS_GLI 1.0, Table E2.1：https://data.bis.org/topics/GLI/tables-and-dashboards/BIS,GLI_E2_1,1.0 ；條款：https://data.bis.org/help/legal 。
- 同一原始 ZIP：https://data.bis.org/static/bulk/WS_GLI_csv_flat.zip
- Antigravity 當地原始 ZIP SHA-256：`87c8b99cca6043ae7737fb9c15159ad5920d0fdf260e9c9a68d03cec7cb95899`；內部 CSV SHA-256：`1bf5aff7ef3903da56ee0e6400a7390cfdb5dee397857625613233d14eaf7cdc`，與 R1i 一致（**外部回報，非本環境重算原檔**）。
- 擷取完成 2026-11-23T00:40:25.162908Z；HTTP Last-Modified 2026-11-18T12:44:16Z，**與官方 2026-10-29 發布日不同**。這是 2026-11-23 的 `LATEST_REVISED_SNAPSHOT`，不代表任何季度已通過當期 PIT。
- 四季 `2025-Q3`～`2026-Q2`、6 條序列共 **24/24 格齊全、0 缺值、OBS_STATUS 全為 A (Normal)**；4/4 的銀行放款＋國際債券＝總額，各用 Decimal 計算差額 0.000（Antigravity 核對，ChatGPT 另從報告數字核算）。
- 存量單位：`UNIT_MEASURE=USD`, `UNIT_MULT=6`（百萬美元），原始 CSV 有最多三位小數；官方年增率 `UNIT_MEASURE=771`（%）、`UNIT_MULT=0`。`3P` 表示**位於美國境外的非銀行借款人**，不是全球所有美元資金的流入。

## 2. 四季有限切片及單位

| 季度 | 信用總額 (百萬美元) | 銀行放款 (百萬美元) | 國際債券 (百萬美元) | BIS 總 YoY % | 放款 YoY % | 債券 YoY % |
|---|---:|---:|---:|---:|---:|---:|
| 2025-Q3 | 14,240,684.034 | 6,405,726.502 | 7,834,957.532 | 7.378 | 8.307 | 6.628 |
| 2025-Q4 | 14,264,166.940 | 6,337,422.386 | 7,926,744.554 | 8.671 | 10.416 | 7.314 |
| 2026-Q1 | 14,770,950.729 | 6,706,302.542 | 8,064,648.187 | 7.308 | 8.195 | 6.583 |
| 2026-Q2 | 15,132,723.957 | 6,936,280.678 | 8,196,443.279 | 8.030 | 9.622 | 6.720 |

SDMX keys（總信用／放款／國際債券）：
- Outstanding：`Q.USD.3P.N.A.I.B.USD` / `Q.USD.3P.N.B.I.G.USD` / `Q.USD.3P.N.A.I.D.USD`。
- 官方 YoY（對應各自最後欄由 `USD` 改成 `771`）：`Q.USD.3P.N.A.I.B.771` / `Q.USD.3P.N.B.I.G.771` / `Q.USD.3P.N.A.I.D.771`。
- CSV 1-indexed line 依 Q3→Q2 順序：總存量 9018..9021、放款 8199..8202、債券 7033..7036、總 YoY 19551..19554、放款 YoY 7245..7248、債券 YoY 17113..17116。

## 3. 可重現的最小分析（不等於因果或預測）

| 季度 | 總額較前季**名目存量差** (十億美元，未調整) | 官方 YoY % | 官方 YoY 相對前季 (百分點) |
|---|---:|---:|---:|
| 2025-Q3 | 未擷取更早一季 | 7.378 | 不計算 |
| 2025-Q4 | +23.482906 | 8.671 | +1.293 |
| 2026-Q1 | +506.783789 | 7.308 | −1.363 |
| 2026-Q2 | +361.773228 | 8.030 | +0.722 |

- 2026-Q2 YoY 回升 **+0.722 個百分點**（7.308%→8.030%），但仍比 2025-Q4 的 8.671% 低 **0.641 個百分點**：**並非連續加速**。
- 2026-Q2 放款 YoY 8.195%→9.622%（**+1.427 個百分點**），債券 6.583%→6.720%（**+0.137 個百分點**）：放款端年增率回升較顯著。
- 2026-Q1→Q2 未調整名目存量分別增加：銀行放款 **229.978136 十億美元**、國際債券 **131.795092 十億美元**，總合 **361.773228 十億美元**。**不得**把兩期存量差當成資金實際淨流入股市、美元或黃金。
- **方法關卡**：BIS 明確表示官方 YoY 是以**調整匯率及統計斷點後的季度變化複合四季**計算，與直接將名目未調整兩季餘額相除不同（官方：https://data.bis.org/topics/GLI ; https://data.bis.org/faq?stats-faqs=7）。資料亦非季節調整，不應過度解讀單一季度差。

## 4. 研究假說更新（H-GCF-USD-CREDIT-01，H0 不變）

現行快照支持「截至 2026-Q2 境外美元信用存量增加、YoY 較前一季回升，銀行端增速反彈較顯著」這項**描述性**命題。但無證據支持「信用增長使股票下月上漲」，亦不能排除股票價格、景氣與融資供需反向領先信用。BIS 官方 Q2 評論稱歐元外幣信用成長較美元快：https://www.bis.org/publications/202610-commentary-ibs-gli 。

正式問題仍是：M2 在固定 16:00 ET 可得的資料與相同樣本、執行假設下，是否能穩健超越 M1 的**下一月美股總報酬減可投資短券總報酬**；未驗證時不推測正負號、不提出 alpha 結論。

`M0/M1/M2=NOT_RUN`；`historical_pit_verified=false`；`accepted_for_model=false`；`Gate0=BLOCKED`。原始 bytes 只在 Antigravity 本機，不同步至 GitHub。

## 5. 下一個真正有辨識力的工作

只在**已保存的同一 BIS ZIP** 中，查核同定義季度的歐元／日圓境外非銀行信用 YoY 與美元是否呈現不同擴張速度：與 USD 的 E2.1 對照 E2.2/E2.3，避免形成單一貨幣敘事。需先對齊借款人「幣區外」定義、資料倍數與官方 771 增長率，且當作 current-vintage descriptive comparison，不作歷史 PIT、定量預測或新資料購買。若相對比較對研究無增量，則停止延伸，優先追來源 PIT 與可交易報酬標籤。
