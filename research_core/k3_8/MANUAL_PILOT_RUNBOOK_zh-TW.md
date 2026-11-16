# K3.8 手動擷取驗收卡（僅第一次兩份官方報告）

目前 **PR #20 已合併**：GitHub Actions 有 K3.8 手動入口。此卡以 2026-11-16 所確認的官方日期為準，若 USDA 更改時程，必須先重新核對。**請勿**在預定公開時間前按 Run workflow，亦不可選 main 擷取。main 的註冊檔會故意失敗，不會取得資料。

## 入口與選擇

1. 開啟 [SIGNAL K3.8 GitHub Actions](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/workflows/signal-k38-manual-capture.yml)。
2. 點 `Run workflow`，**Branch 選 `codex/k38-forward-pit-capture`（絕不可選 main）**。
3. 按下表填寫欄位；`direct_txt_url` 輸入 `AUTO`，程式從 ESMIS 官方發布頁查找該日唯一 TXT，無須人工複製完整網址。
4. 點 `Run workflow`，確認兩個工作：`K3.8 no-network validation...` 為 Success、`Manual one-report official capture...` 為 Success；接著在同一 Actions Run 的 Artifacts 核對 `signal-k38-manual-...`。
5. 完成後在對話中貼出 GitHub Actions Run 連結，便於獨立檢查摘要、UTC、雜湊與結果；不需要下載／上傳 ZIP。

| 輸入欄位 | NASS 第一次 | WASDE 第一次 |
|---|---|---|
| source | `NASS` | `WASDE` |
| release_date | `2026-11-16` | `2026-12-10` |
| direct_txt_url | `AUTO` | `AUTO` |
| not_before_utc | `2026-11-16T21:00:00Z` | `2026-12-10T17:00:00Z` |
| latency_seconds | `120` | `120` |
| **最早執行（台灣）** | **2026/11/17 05:00 之後** | **2026/12/11 01:00 之後** |

建議發布後 5～10 分鐘再手動觸發，避免官方網站尚未更新。這不是自動排程；如果較晚執行，紀錄的 `first_observed_at_utc` 就是這次系統實際下載完成時間，不可回填至預定發布時間。

## 失敗處理

- `EXACT_RELEASE_DATE_OFFICIAL_TXT_NOT_LISTED`：官方列表尚未出現該日 TXT，**不能退回上一期**。稍後再手動重試，不要修改日期。
- `WRONG_RELEASE_DATE_STALE_OR_OTHER_EDITION`：官方來源不符合指定日期，維持失敗並保留 log。
- `OFFICIAL_HTTP_403/404`、逾時、內容長度不符、來源網域錯誤：維持失敗，不要改用非官方複製網站。
- 若新版本的 WASDE TXT 仍只有月份年份，驗收顯示 `release_date_precision_from_body=MONTH`，不冒稱檔案內含完整發布日。
- 成功擷取仍只能標為 **SYSTEM_OBSERVATION_READY**；沒有自動證實個別玉米指標、最早原始公開時刻、全球首次取得、跨 Run 不重複或任何投資交易績效。
- Artifacts 保留 90 天，並非永久封存；正式保存方案由 Issue #14 管理。

**資料來源：** [NASS 官方發布日曆](https://www.nass.usda.gov/Publications/Calendar/reports_by_date.php?month=11&year=2026&view=l)、[ESMIS Crop Progress](https://esmis.nal.usda.gov/publication/crop-progress)、[USDA WASDE 官方頁](https://usda.azureedge.us/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report)。

現在仍是 Code Ready、正式新報告 System Observation **0/2**，且尚未啟用任何自動排程。
