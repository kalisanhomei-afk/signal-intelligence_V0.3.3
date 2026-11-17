# SIGNAL K4.9｜可重用的 FGIS 每週原始資料與修訂封存

**定義：** 將 K4.8 的 2026-11-16 一次性硬編碼捕獲，改為可重複執行的「預定日期驗證 → 完整官方原件 → SHA-256 → 實際 UTC → 前週修訂比較 → 不可覆寫版本封存」。**這是前瞻證據蒐集管線，不是 PIT 的獨立第三方認證，也不會自動交易。**

## 目前已核實的證據

- 2026-11-16 FGIS `WA_GR101`、截至 11/12：原始檔 18,499 bytes，SHA-256 `4555c478b09d2507d042de55c6d5042e095f37b13d05185fcf889433c52802e5`，原件與取得回執仍位於 `research_core/k4/evidence/fgis/`。
- 官方報告清單：<https://mymarketnews.ams.usda.gov/viewReport/3071>；有日期的 MMN `filerepo` 版本**須先核對精確完整 URL**，不能只靠猜測編號。
- 官方可被覆寫最新版：<https://www.ams.usda.gov/mnreports/wa_gr101.txt>。若已變成下一週或格式不符，程式一定拒絕當作指定週的報告。
- 2026 年 12 月 WASDE 預定 2026-12-10T17:00:00Z；所有 2026 年 12 月之前的數據捕獲均必須早於此 UTC。未來年度研究須另指定對應發布截止 UTC。

## 三次前瞻擷取（尚未有新資料，須在各報告真正公布後）

| 預計核對報告 | 所屬週結束日 | 台灣排程檢查 | 前一週原始資料 |
|---|---|---|---|
| 2026-11-23 | 2026-11-19 | 2026-11-24 | 已封存 11/16 原件 |
| 2026-11-30 | 2026-11-26 | 2026-12-01 | 新封存的 11/23 原件 |
| 2026-12-07 | 2026-12-03 | 2026-12-08 | 新封存的 11/30 原件 |

**報告日期是預定核對對象，非保證實際公布日期。** 如果因假期延後或沒有資料，維持 `BLOCKED` 並記錄真實發布日期，絕不把其他週數值移用或把空值填零。這些工作由既有 SIGNAL FGIS 週報追蹤任務通知與嘗試，實際執行／提交均以 GitHub 來源與驗收紀錄為準。

## 直接可執行的命令（研究 Agent／GitHub 隔離工作環境）

先從 PR #22 的 `codex/k4-corn-hypothesis-mvp` 分支取得程式，在官方 11/23 週報真正可讀後執行：

```bash
python -B -m research_core.k4.fgis_weekly_vintage \
  --report-date 2026-11-23 \
  --week-end 2026-11-19 \
  --wasde-cutoff-utc 2026-12-10T17:00:00Z \
  --prior-raw research_core/k4/evidence/fgis/WA_GR101_20261116_official_raw.txt \
  --prior-receipt research_core/k4/evidence/fgis/WA_GR101_20261116_capture_receipt.json \
  --output-dir k49-staging
```

如果已取得 **USDA 官方報告庫確認過**的固定日期 `filerepo` TXT，可加 `--historical-url "<exact full official dated TXT URL>"`。程式會先嘗試該 URL，失敗時再嘗試官方 rolling TXT，但**必須驗證實際回應的報告日期和週別**；不接受來源換成任意網站。

執行後會輸出摘要 `status, sha256, raw_filename, receipt_filename, attempts`，原始報告位元組不列印到 CI 日誌。

- `CAPTURED_PRE_WASDE_NOT_INDEPENDENT_PIT_CERTIFIED`：已取得指定週原始完整資料及原始捕獲回執，需正式核對再提交研究分支。
- `ALREADY_ARCHIVED_IDENTICAL_BYTES`：相同 SHA 原始檔已存在，不變更第一次取得的回執。
- `BLOCKED_NO_VALID_OFFICIAL_REPORT`：失敗並列出每個官方來源的錯誤，不產生新原始檔。
- 相同報告日期但來源真正改版：生成不同的 `WA_GR101_YYYYMMDD_<sha16>_official_raw.txt` 及配套 JSON，保留先前版本，不覆寫。
- 已封存的前週數字與新報告回列數字不同：`PREVIOUS_WEEK_REVISED`，分開保留差額 `previous_week_revision_delta_mt`。跨週市場年度累計差只列為「隱含先前週期修訂」供檢查，不能假設都是前週修訂。

### 正式進 GitHub 前的關卡

只在成功取得報告後，將 staging 裡生成的 **兩份原件**（原始 TXT 與 receipt JSON）以完整位元組提交到 `research_core/k4/evidence/fgis/`；不得上傳 Databento 或任何付費期貨原始資料。不將 `BLOCKED` 的回執冒充已成功封存。

每次提交 PR 即觸發**純離線** CI。以下程序會從 GitHub 已保存的所有真實原始檔重算 SHA、核對 UTC、日期、內容與前週關聯；新增週數不必修改測試程式：

```bash
python -B -m unittest discover -s research_core/k4/tests -p 'test_*.py' -v
python -B -m research_core.k4.fgis_archive_audit \
  --evidence-dir research_core/k4/evidence/fgis \
  --output k4-review/fgis_forward_version_audit.json
```

**限制**：網址包含日期、機器所讀的 UTC、GitHub commit 或 SHA-256 都不能單獨證明首次公布時間不可竄改。FGIS 文本包含歷史更正聲明，必須保留不同版次。所有驗收均標記 `independent_historical_pit_certified=false`、`trade_eligible=false`；2026-12 WASDE V0 庫存 1,758 百萬蒲式耳不改寫，11/23 等數值尚不存在時不作預測。

## 降低反覆作業

這次已將重複工作壓縮到同一條命令；每週只有參數日期與上一份回執路徑不同。可以由研究 Agent 執行取得、核對及提交，但**排程發出通知並不等於已提交成功**。不要在 `main` 新增定時 workflow，也不要在 PR 程式內硬塞當週特定數值或擷取時間。

**研究 Gate：** `K49_REUSABLE_CAPTURE_AND_ARCHIVE_AUDIT_ENGINE`（待 CI 驗收）；未來新週版數字以實際來源為準，保持 `NO_TRADING`。
