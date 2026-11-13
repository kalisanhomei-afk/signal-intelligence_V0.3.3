# K3.7 Agent B 本次驗收紀錄

執行日期：2026-11-13（Asia/Taipei）；Python 3.12.14；Repository 根目錄執行。
分支：`codex/k37-agent-b-nass`；基準：`ed365fbdbe960ac70dd6ed356766907a7267257a`。
本次依使用者回覆，交付程式與來源受阻報告，**不宣告歷史資料驗收完成**。

## 已執行命令與實際結果

| 命令 | 實際結果 | 退出碼 |
| --- | --- | ---: |
| `python -B -m unittest discover -s research_core/k3_7/nass/tests -v` | 43 tests，全部 OK | 0 |
| `python -B -m unittest discover -s research_core/k31/tests -v` | 既有 K31：34 tests，全部 OK | 0 |
| `python -B -m unittest discover -s research_core/k3_4/tests -v` | 既有 K3.4：15 tests，全部 OK | 0 |
| `python -B -m research_core.k3_7.nass.pipeline build` | `SOURCE_FEASIBILITY_BLOCKED_OR_NO_DATA`，`observation_rows=0` | 0 |
| `python -B -m research_core.k3_7.nass.pipeline fetch --max-pages 100` | `SOURCE_UNAVAILABLE`，`pages_attempted=1`，`reports_discovered=0` | 2 |

共 92 項離線測試通過。未執行整個 Repository 的全套測試、模型評估或線上成功下載驗收。
既有 K31／K3.4 測試只讀原有檔案，所需暫存輸出在臨時目錄；本次沒有更新其固定成果。

Agent B 測試包括：當期逐州五分類與 G+E、跨行表頭、其他作物與前期資料隔離、
0–100 範圍與加總容許誤差、缺評級與未列州區分、重複州隔離、日期／週末檢查、
官方連結探索與分頁限制、下載失敗紀錄、原始位元組完整性、不可覆寫版次與衝突稽核、
排程代理／未知時間隔離、夏令時間轉換、合成範例拒入正式輸出，以及已提交快照逐位元組離線重建。

所有數值解析測試皆使用**合成格式樣本**。真實三年報告未下載，不能把這些測試當成真實原文格式已驗證。

## 線上來源受阻證據

正式 `fetch` 執行紀錄保存在 `data/source_manifest.jsonl`，而非只在說明文件轉述：

| 角色 | 請求網址 | 嘗試時間 UTC | 實際結果 |
| --- | --- | --- | --- |
| 官方排程 | `https://www.nass.usda.gov/Surveys/Guide_to_NASS_Surveys/Crop_Progress_and_Condition/` | `2026-11-13T06:48:48.057595Z` | `URLError: <urlopen error Tunnel connection failed: 403 Forbidden>` |
| 歷史報告探索 | `https://esmis.nal.usda.gov/publication/crop-progress` | `2026-11-13T06:48:48.083652Z` | `URLError: <urlopen error Tunnel connection failed: 403 Forbidden>` |

環境狀態與 `/etc/codex/network-policy.json` 顯示這兩個主機未在允許清單。
403 發生在代理 CONNECT 階段，沒有取得 USDA 原文，因此沒有原文 SHA-256、成功下載時間或歷史證據 URL。
沒有停止 TLS 驗證、繞過代理、換用非官方鏡像或把其他年度資料改成試點年度。

## 資料驗收尚未通過項目

| 年度 | 已取得報告 | 州別觀測 | 已驗證歷史公開時間 | 狀態 |
| --- | ---: | ---: | ---: | --- |
| 2016 | 0 | 0 | 0 | 整個年度未取得 |
| 2020 | 0 | 0 | 0 | 整個年度未取得 |
| 2022 | 0 | 0 | 0 | 整個年度未取得 |

三年均未取得任何參考州觀測：Colorado、Illinois、Indiana、Iowa、Kansas、Kentucky、Michigan、
Minnesota、Missouri、Nebraska、North Carolina、North Dakota、Ohio、Pennsylvania、South Dakota、
Tennessee、Texas、Wisconsin。其餘 32 州屬參考範圍之外，不假定為官方每週應報而缺漏。
逐年完整稽核週次與州名清單見 `out/quality_report.json`。

- 目前沒有「下載成功但無法解析」的歷史來源；因探索入口受阻，尚無個別歷史原文網址可驗證。
- 未知各年實際狀況表起訖、缺州、缺評級及修訂情形；不能推斷缺口是官方未報。
- 尚無真正歷史首次發布版認證，也無精確歷史公開可用時間；排程來源本次亦不可取得。
- 三年實際來源格式、實際百分比與完整季節覆蓋率，必須待網路允許後再驗收。

## 可進入的下一步

可以建立 PR 供程式碼與可行性審查；資料完整性門檻仍受阻，不能交由 Agent D 視為已驗收的完整輸入。
下一輪允許官方主機後，沿用 `fetch → build → offline tests`，逐年度檢查真實原文與版次，
再由 Agent C／D 補上獨立 PIT 證據與整合審查。
本次未 merge、部署、設定排程或宣稱預測能力。
