# K4.5-B｜2026/11/16 玉米出口檢驗：真實供需變數稽核

**研究結果：`ABSTAIN_UNCALIBRATED_EXPORT_DRIVER`。已取得正式報導的外部需求線索，但沒有經校準、可重現的「2026/12 玉米期末庫存 V1 點預測」。不可把情境當成預測，不能交易。**

## 資料身分與可得時間

- 上游數據：USDA AMS/FGIS `WA_GR101` — Grain Inspected for Export，報告週結束日 2026-11-12，原始報告登錄 2026-11-16（catalog 顯示 09:56 am，時區未獨立驗證）。
- USDA 官方原始 TXT 入口：https://www.ams.usda.gov/mnreports/wa_gr101.txt （在 2026-11-17 網頁檢視時明列 `WA_GR101`、2026-11-16、該週玉米 865,503 公噸、累計 12,463,023 公噸；但此 URL 會被新週報覆寫，**不可視為不可竄改的歷史封存**）。
- 官方動態報告目錄：https://mymarketnews.ams.usda.gov/viewReport/3071；報告清單於 2026-11-16 顯示 `WA_GR101`。由於原始 TXT 位元組下載失敗，`official_raw_sha256=null`，仍不能宣稱已取得 raw-byte PIT。
- 本次可核對數字來源：CME Economic Calendar, 2026-11-16 10:00 CT https://www.cmegroup.com/education/events/econoday/675853；`source_report_release_utc_claim=2026-11-16T16:00:00Z` 是以 CME 公布時間換算的**來源時間聲稱**，不是獨立認證的首筆可取得時間。
- `inputs_cutoff_utc=2026-11-17T00:00:00Z`（截至該時間公開的資訊快照）；截至此次研究尚無官方文件原始位元組 SHA、可信獨立 captura 時間，必須維持 `source_pit_authenticated=false`。
- 目標：USDA 2026-12-10 12:00 ET 預定發布之 2026/27 美國玉米 ending stocks (million bushels)。不將 Nov16 出口資料改寫已封存的 V0 = 1,758 million bushels。

## 事前變數與相反方向

| 指標 | 數值 | 解讀 |
|---|---:|---|
| 11/12 當週出口檢驗 | 865,503 公噸 | 實物已檢驗出口量，**不是訂單銷售量** |
| 達成 USDA 年度出口預估所需週均 | 1,701,336 公噸 | 當週僅達此速度的 50.872% |
| 2026/27 累計檢驗 | 12,463,023 公噸 | 與上年同期 15,851,319 公噸相比約 −21.375% |
| 本年度出口檢驗完成率 | 15.0% | 比歷年同期五年平均 12.9% 高 2.1 個百分點 |

來源：CME 彙整 USDA FGIS Weekly Export Inspections，數值附於封存 JSON。

**關鍵**：短週速度、年度同期 YoY、相對於五年季節曲線的累計完成度，分別回答不同問題；並且可能方向相反。不得將「短週落後所需平均」簡化為必然調降整年出口，也不能只用「高於五年平均」當作確定上修。FAＳ 出口銷售／承諾與 FGIS 出口檢驗為不同衡量；不能直接相加。

## 固定機制情境（非概率預測）

只有在其他供需數值不變時，`期末庫存變化 = − 出口估計變化`：

| **假設** USDA 12 月對出口預估的修訂 | **條件性** 期末庫存 |
|---:|---:|
| −50 百萬蒲式耳 | 1,808 百萬蒲式耳 |
| 0 | 1,758 百萬蒲式耳 |
| +50 百萬蒲式耳 | 1,708 百萬蒲式耳 |

`±50` 是透明、固定的**敏感度測試設定**，並非從 11/16 數據估計出的變化，更不是 12 月官方結果的預測區間。不能選擇最符合事後結果的條件。

## 完成的可重現工程

- `research_core/k4/export_driver_screen.py`：驗證資料身分、週別、as-of UTC、前後關係、單位／正值、不得加入 12 月實際 outcome；自動算出週均比例、年增率、季節差、情境；永遠不回傳未经校準的 V1 點預測。
- `research_core/k4/cases/2026-11-16-fgis-inspections-driver.json`：外部可查數據、來源連結、未解鎖的證據欄位。
- `research_core/k4/cases/2026-11-16-fgis-export-driver-screen-result.json`：固定研究輸出。不得在 12 月報告後改寫該份結果。
- `research_core/k4/tests/test_export_driver_screen.py`：固定結果重演、矛盾訊號、日期穿越、偽 PIT、假 hash、情境偷換、事後 outcome 灌入、數值錯誤等測試。

```bash
python -m unittest research_core.k4.tests.test_export_driver_screen -v
python -m research_core.k4.export_driver_screen \
  --case research_core/k4/cases/2026-11-16-fgis-inspections-driver.json \
  --output local-private-k45/export_driver_screen.json
```
執行只使用 Repository 檔案，不需 Databento API，不買行情、不連結券商、不下單。

## 下一個決策點

**有資料 ≠ 能轉為有辨識力的預測。** 想要提出數值 V1，應先在事前版本化的歷史資料上校準出口檢驗進度 → USDA 下期出口修訂，包含季節項、已知 USDA 預測、未來可得資訊的時間滲漏檢查、樣本外測試，且要打敗上期持平基準與市場事前共識。如果沒有可靠映射，模型必須 ABSTAIN。12 月市場共識及正式來源封存仍為獨立待解決的證據缺口。

**Gate: EVIDENCE_SCREEN_PASS (GitHub Actions [#43993719450](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/43993719450)：116/116 tests PASS，包含官方 FGIS TXT 來源鎖定測試); V1_POINT_FORECAST_NO_GO; PIT_UNVERIFIED; TRADE_ELIGIBLE=false.**
