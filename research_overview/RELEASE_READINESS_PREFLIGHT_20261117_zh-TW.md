# SIGNAL｜2026-11-17 公告前系統總檢查與端到端預演紀錄

**範圍**：K5 2026-11-19 EIA 公告、K4 FGIS 11/23～12/07 三週、K4 2026-12-10 USDA WASDE，以及 PR #24 共通研究總覽。**截至報告時，未公布的未來數值一律沒有填入。**

## 一、驗收摘要

| 研究／環節 | 修補／預演成果 | 目前證據 |
|---|---|---|
| K5 天然氣 PR #23 | 11/19 正式週別／單位／原始 SHA／前週來源配對；原始檔寫入修正為獨占建立，只刪除本次寫入檔案 | [GitHub Actions #44033908598](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/44033908598)：**56／56 通過** |
| K4 玉米 PR #22 | 新增 K4.11 官方原件獨立評分，**不再被缺乏市場共識卡住 V0 誤差**；嚴格只辨識 USDA 美國 CORN、2026/27、million bushels 和 Nov／Dec 欄位 | [GitHub Actions #44034410087](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/44034410087)：**214／214 通過** |
| K4 真實公開資料版面預演 | 用 GitHub runner 取得 **11 月** `wasde1126.txt` 原件 122,379 bytes，解析正確取得 Oct 1849、Nov 1758 百萬蒲式耳；不是 12 月未來數據 | [GitHub Actions #44034187733](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/44034187733)：官方網路源解析成功；一次性工作已移除 |
| 共同研究總覽 PR #24 | 驗證模擬後發事件卡片可接受官方結果及誤差，研究 PR HEAD 前進時**原始 V0 連結不隨之更改** | [GitHub Actions #44034880435](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/44034880435)：**38／38 通過** |
| 來源時間與摘要 | EIA 官方 11/19 10:30 ET、感恩節週 11/25 12:00 ET；USDA WASDE 12/10 12:00 ET | [EIA 官方時間表](https://ir.eia.gov/ngs/schedule.html)；[USDA 官方 WASDE 日期](https://usda.azureedge.us/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report) |
| 自動化排程及隔日備援 | 保留既有 K5、FGIS、WASDE 工作而未增加總任務；K5 11/20 加入晚間同事件備援，FGIS 改為每週二／三查核 | 依 ChatGPT Automations 已啟用的排程和下一次啟動時間查核 |

## 二、修補的五個具體風險

**P0｜K4 官方資料已出但共識缺漏，V0 無法評分：已修補。**

新 `research_core/k4/wasde_official_outcome_capture.py` 以真實 USDA 12 月原始 bytes 為必要條件，獨立輸出 V0 官方誤差；`consensus=null` 不阻塞。先前 K4.10 保留為「有可靠共識之後」的完整比較器；不改寫其事前凍結預測。測試包含缺共識仍計分、報告月份／單位錯誤、來源非法、未到發布時間禁止下載與禁止覆寫。

**P0｜K5 來源擷取可能競爭覆寫：已修補。**

`research_core/k5/eia_postrelease_capture.py` 寫入原始 JSON 及兩份回執全部改用排他開檔；如果其他 Worker 搶先產生某個檔案，本次只回滾自己建立的檔案，不會清掉另一 Worker 的正式證據。CI 使用模擬競爭驗證，真實下一期數據依然未知。

**P0｜PR #24 只有公告前空結果的驗證，未來加新原件可能 CI 失敗：已預演並修正。**

`research_overview/validate.py` 將 **原始事前預測 commit** 與 **研究 PR 最新 HEAD** 分離；即使後者未來因新原件提交而移動，原來的預測原始 commit 仍保持固定。以明確標示 synthetic 的 11/19 官方結果，測試驗收卡片、來源連結、V0 誤差與投資 No-Go，不將合成值寫入任何正式卡片。

**P1｜K5 擷取日遇網路或 GitHub 故障：已配置同事件晚間重試。**

既有「SIGNAL K5 天然氣首輪驗收」查核時點為台灣 **2026-11-19 21:00、11-20 09:00、11-20 21:00**。晚間若已成功，必須停止重複上傳；若上午失敗，只重試同一 11/19 報告。

**P1｜FGIS rolling 檔被下週覆寫：已配置每週兩次查核。**

既有「SIGNAL FGIS 週報封存」檢查台灣 **11/24、11/25、12/01、12/02、12/08、12/09 上午 08:00**。第二次只補抓未成功或官方修訂的當週檔，優先核對 USDA MMN 已知日期的固定報告原件；不得把更新後的下一週 rolling 檔當成上一週。

## 三、仍無法消除的外部風險（請正確理解「系統無誤」）

1. **12 月官方原件尚未存在**：K4.11 預期 ESMIS 路徑 `wasde1226.txt` 必須在 12/10 真正公告後確認。如果 USDA 改變 URL／文字格式，程式應 `BLOCKED`，不會抓錯數據。真實 11 月格式檢查只能降低風險，不等於保證未來同格式。
2. **Automations 環境的 GitHub 寫入權限尚無獨立驗證**：已查核任務啟用及排程，但當前環境資訊顯示 `environment_selection=inherited` 且具體執行電腦設定未知。通知執行成功不等於 GitHub source bytes 已寫入；排程須逐次回報真實 GitHub commit／CI，沒有則明確 `BLOCKED`。不宣稱推播一定送達手機。
3. **官方供應商及網路可用性**：EIA rolling JSON 只保留最新版、FGIS rolling TXT 每週更新；即使我們設隔日備援，仍無法保證官方 100% 正常。失敗可先檢查同一期官方歷史檔與 GitHub 證據，無需直接等下一次資料；但沒有來源時不可假造歷史首版 SHA。
4. **研究 CI 不是完全獨立 PIT 認證**：SHA 和時間戳能追蹤現已取得的來源完整性，不足以證明其首版公開時間不可竄改。K4／K5 V1 仍處於 abstain、交易資格未通過。

## 四、正式公布時各代理必須遵守的最低順序

```text
(1) 確認當前真實 UTC，未到發布時間不得抓新值
(2) 確認官方來源是本事件正確資料週、月份、單位、版本
(3) 取得真實原始 bytes，計算 SHA-256 和擷取 UTC
(4) 寫入彼此配對的原件／回執，不能覆寫；有失敗就 BLOCKED
(5) 使用已凍結的 V0 產生單事件描述性誤差，缺市場共識亦可計 V0
(6) 只提交研究 PR，核對 GitHub commit 與完整 CI
(7) 再更新共同卡片；官方值／誤差尚無證據則 null
(8) 投資仍 NO_GO；絕不修改事前原始預測或自動下單
```

## 五、下一個使用者決策點

**2026-11-20**：收到 K5 首輪正式驗收成功／BLOCKED 結果後，應先評估來源封存成功率及誤差資訊，再決定是否要把這條來源提升為更穩定的 GitHub Actions 註冊 Workflow。若欲完全免依賴 ChatGPT 排程的 GitHub 寫入環境，需另行討論、審核並授權安全的預設分支自動工作流；**本次未改動 main**。

**結論：本輪已修補內部可重現錯誤，但不可能在官方發布前或不執行真實排程的情況下保證所有外部環節「100% 無故障」。目前的正確狀態是：技術資料契約／合成事件路徑已驗收，正式外部事件尚未發生，留有隔日與同日備援及明確阻塞回報。**
