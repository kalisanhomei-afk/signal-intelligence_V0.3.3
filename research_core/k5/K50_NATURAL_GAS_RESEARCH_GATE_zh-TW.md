# SIGNAL K5.0｜第二個獨立投資假說：美國天然氣庫存與天氣需求

> **狀態更新（2026-11-17）：** 下文的「尚未取得 EIA JSON 原始 bytes」是 K5.0 當時的狀態，**已由 K5.1 補齊**。官方 11/13 原始 JSON 7,197 bytes、SHA-256 `6eb6c699b789d7130d3f50dbe5681e835b57bc25dd118380398169dda63fe252`，提前於 11/19 公告保存，實際捕獲時間及 GitHub 原始來源見 [K5.1 來源稽核](K51_EIA_ORIGINAL_SOURCE_CAPTURE_AUDIT_zh-TW.md)。K5.0 事前凍結的 V0 +61 Bcf 與其空白 source SHA **不回填、不改寫**；新證據另存。


**研究決策（2026-11-17）**：選擇 H-NG-001 作為玉米以外的最小平行研究；僅驗證公告前預測及來源可用性，保留 K4.10 的既有獨立驗收。不得以本文件宣稱 alpha、實際交易可行性或執行任何訂單。

## 為何優先天然氣，而不是無限制擴充商品

- **可否頻繁驗證**：EIA 每週發布 Weekly Natural Gas Storage Report，通常美東週四 10:30，但節假日會更改；比玉米每月 WASDE 能更快取得獨立事件。
- **具備解釋性因果變數**：地下工作氣庫存由供給、發電／住商需求、天氣、LNG 出口與管線進出口共同決定。NOAA CPC 公開加權供熱／供冷度日（HDD/CDD）與七天天氣預報；但「資料現在可查」不等於有歷史預報的可驗證首版。
- **金融商品**：CME Henry Hub NG 期貨為 10,000 MMBtu／口、最小跳動 US$0.001/MMBtu（US$10／tick），價格波動可能大、非專業使用者不宜直接交易。
- **難點**：EIA 正式發布的資料往往已被市場迅速消化。EIA 自己說明一般 API 的 WNGSR 更新可能比專用公告伺服器晚**最多兩小時**，因此不應追逐公告後反應；研究重點應是公告前供需預測能否優於事前市場共識。

資料來源：
- EIA WNGSR 正式報告：https://www.eia.gov/naturalgas/storage/
- EIA 公告檔案入口：https://ir.eia.gov/ngs/wngsr.json （官網固定檔名、每週更新），同路徑另有 `wngsr.csv`；EIA 公告存取注意事項：https://ir.eia.gov/ngs/notice.html
- EIA API 更新說明：https://www.eia.gov/opendata/faqs.php
- NOAA CPC Degree Days：https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/cdus/degree_days/
- CME 天然氣期貨說明：https://www.cmegroup.com/education/courses/introduction-to-natural-gas/nat-gas-product-overview

## 已完成的**公告前**首次基準

**2026-11-13 EIA WNGSR 正式公開、截至 11/06** 的 Lower 48 working gas inventory：
- 2026-11-06：**3,862 Bcf**
- 2026-10-30：**3,801 Bcf**
- 當週 `net_change=+61 Bcf`；五年同期庫存平均 `3,787 Bcf`，所以庫存比平均高 `+75 Bcf`。
- 一年前同期 `3,954 Bcf`。
- 此數值與來源身分已由 EIA 正式 JSON/CSV 的網站展示互相核對；**本次代理沒有取得 JSON 原始位元組，因此 source_raw_sha256=NULL，不能聲稱原始檔驗證完成**。
- 11/13 當週公告已在 2026-11-17 查詢時可取得；官網公告標示美東 `2026-11-13 10:30`，可換算 `2026-11-13T15:30:00Z`，但這是發行機關公告時間，非獨立捕獲時間。

**將要驗證的事件**：EIA `2026-11-19T15:30:00Z` 預定發布 2026-11-13 週結束日的庫存（台灣 2026-11-19 23:30）。這個時間是公告預定時間，不是新的資料已公布。

**事先保留、無需估計參數的 V0：下一週庫存變動預測 = 上次已公布的庫存變動 `+61 Bcf`。** 這是易於被打敗的 *persistence baseline*，不是 NOAA／供需機制產生的 V1。對照資料 `cases/2026-11-19-eia-prior-week-input.json`、事前預測 `cases/2026-11-19-eia-frozen-v0-forecast.json`，另有 `cases/2026-11-19-eia-outcome-pending.json`，將真正尚未發行的官方結果記為 NULL。GitHub 提交紀錄提供事前版本存證；不是外部可信時間認證。

## 預先定義驗收／反證

1. 公告後取得 EIA 官方來源**實際原始位元組、SHA-256、取得 UTC**，核對正確 target (Lower 48)、units Bcf、正式週別及 `net_change`，不從 11 月 19 日之外的週報取值。
2. 計算 `V0_absolute_error_Bcf=abs(actual_2026-11-13_net_change - 61)`；未取得有實證的官方結果時，程式 `WAITING_FOR_REAL_POST_RELEASE_EIA_OUTCOME`，不得推算。
3. 另外封存真正公告前的分析師「庫存變動」共識（而不是現有庫存總量、期貨價格或公告後新聞），記錄來源版本、發布 UTC、可驗證封存與方法。不滿足則不報市場共識的勝負。
4. 在取得 NOAA 公告**之前**的預測 HDD/CDD 版本、實際時段和需求／產量／LNG 來源之前，V1 `ABSTAIN`，不得把本次 +61 推算成 AI 的獨立預測。
5. 單一事件 V0 誤差只是管線 smoke test；跨數十個獨立週次並保留季節性、來源修訂、異常天氣和出場成本後，才能檢驗預測是否有超越季節與共識的增量價值。

## 執行

```bash
python -B -m unittest discover -s research_core/k5/tests -p 'test_*.py' -v
python -B -m research_core.k5.ng_baseline \
  --case research_core/k5/cases/2026-11-19-eia-prior-week-input.json \
  --output local-k5/k5_first_frozen_baseline_recomputed.json
```

本程式不使用 API Key、不買交易行情、無外部網路讀取，也不下單。若要進一步檢查 11/19 來源，應在確定公告實際發布後做**一次**有限抓取，依 EIA 的機器存取／節流規定操作，避免高頻輪詢。

## 隔離與停止條件

K5 是獨立分支 `codex/k5-natural-gas-scout`，**以 K3.7 研究分支為基礎**，不包含或合併玉米 K4 PR #22，亦不動 `main`。預計開獨立 Draft PR。

- **K5.0 Go**：官方數據身份可核對、下次預定事件可核對、公告前固定 V0 可重現、fail-closed 測試通過。
- **K5.1 No-Go**：若無法取得可信的公告前 NOAA 需求預測及共識／官方結果版本，停止進一步 AI 或交易程式開發。
- 即便事前模型優於共識一次，也不能自動取得投資或交易資格。

**Gate：RESEARCH_SCOUT_ONLY / V0_PERSISTENCE_FROZEN / RAW_EIA_SHA_UNAVAILABLE / PIT_UNVERIFIED / V1_ABSTAIN / TRADE_ELIGIBLE=false。**
