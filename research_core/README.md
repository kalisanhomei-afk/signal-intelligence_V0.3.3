# SIGNAL｜雙引擎共同研究核心 K1（可執行版）

**狀態：K1 離線實作與合成樣本驗收完成；尚未開始 K2 雙引擎預測。**  
**依據：**《SIGNAL 雙引擎共同架構 V1.0》及《K1 開發任務與驗收表》，2026-11-09。  
**範圍凍結：** 不接入 USDA 即時 API、不呼叫 OpenAI、不覆蓋 SIGNAL 舊程式、不發布網站、不使用任何真實投資帳戶。

## 先看成果

直接使用 Chrome 開啟：`research_core/out/review.html`。

報告所有玉米數字均為**合成測試值，並非 USDA 實測或官方預測**。這個檔案是工程品質檢驗，不是投資研究報告。

## 專案檔案

| 內容 | 說明 |
|---|---|
| `contracts.py` | 七類資料契約：來源、觀測、事件、因果、預測、假說、決策 |
| `asof_guard.py` | as-of 可得時間檢查；預設要求系統已取得資料 |
| `units.py` | 相同物理量的精確量級換算；跨物理單位必須明確給定換算依據 |
| `stockflow.py` | 供需會計平衡與期間／範圍／版本一致性檢查 |
| `store.py` | 最小 SQLite append-only 存量；禁止直接 UPDATE/DELETE 來源及觀測紀錄 |
| `fixtures/synthetic_corn_vintages.json` | 完全虛構的美國玉米供需兩個發布版本 |
| `demo.py` | 離線產生五份驗收資料與 HTML 報告 |
| `tests/` | `unittest` 自動化驗收 |
| `out/` | 已生成的範例結果，不使用任何 API |

## 執行條件

- Windows／macOS／Linux；Python 3.11+。
- 完全採用 Python 標準函式庫，不須安裝 pip 套件。
- 在 Repository **根目錄**（與 `research_core` 並列的目錄）執行：

```powershell
py -3 -m unittest discover -s research_core/tests -v
py -3 -m research_core.demo
```

Windows 若 `py -3` 不存在，但有安裝 Python，可改用：

```powershell
python -m unittest discover -s research_core/tests -v
python -m research_core.demo
```

或直接雙擊 `research_core/執行K1離線驗收.bat`。

## 不可互相混淆的時間

- `period` 是經濟資料所描述的時期。
- `published_at` 是來源發布此版資料的時間。
- `available_at` 是這筆觀測版次外界可取得的時間。
- `retrieved_at` 是 SIGNAL **實際取得**該來源快照的時間。
- `as_of` 是研究決策時間，預設兩個條件都要成立：`available_at <= as_of`、`retrieved_at <= as_of`。

如只研究公開資訊理論上何時可知，可以明確使用 `TimePolicy(require_local_retrieval=False)`；**不能把這種模式冒充為 SIGNAL 當時已實際持有的資訊**。

## 合成供需示例與驗證

| 欄位（單位：百萬蒲式耳） | v1 | v2（後來修訂） |
|---|---:|---:|
| 期初庫存 | 1,700 | 1,700 |
| 產量 | 15,000 | 14,900 |
| 進口 | 25 | 25 |
| 國內使用 | 12,300 | 12,300 |
| 出口 | 2,800 | 2,800 |
| 期末庫存 | 1,625 | 1,525 |

**這些數字都是虛構的，不可用於投資判斷。** v1 的日期為 2026-01-10，v2 為 2026-01-15。在 1 月 12 日重播時，只能使用 v1；1 月 16 日才可選 v2。

## 需要輸出的五份檔案

1. `out/observation_catalog.json`：完整來源、觀測與時間／版本資訊。
2. `out/asof_replay.json`：修訂前與修訂後的時點重播。
3. `out/model_inputs.json`：固定研究時點的六項供需輸入及會計核對。
4. `out/qa_report.json`：故意錯誤案例的攔截與診斷。
5. `out/review.html`：可讀的黑金風格驗收報告。

## 本輪「通過」代表什麼、不代表什麼

**代表：** 固定合成測試資料的來源雜湊、版本不可覆蓋、發布及取得時點、單位、期間、會計平衡與因果標示控制有效。

**不代表：** 任何真實 USDA 數據完整性、真實世界因果識別、預測優於基準、期貨價格可預測、策略獲利或資產配置適當。

驗收準則：離線測試全部通過；`qa_report.json` 的 `all_passed = true`，且 `model_inputs.json` 的 `balance.balanced = true`。未通過前不進入 K2。
