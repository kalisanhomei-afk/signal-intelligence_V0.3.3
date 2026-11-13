# SIGNAL K3.7 Agent B：USDA NASS 州別玉米狀況

## 2026-11-14：修訂標記誤判更正

原始解析器使用全文關鍵字 `Revision` 判定修訂版本，因此將官方報告的制式 `Revision Policy:` 也誤判為個別報告修訂。修正版僅辨識行首特定的修訂／更正通知（例如 `Revised edition`、`Correction Notice`）。**未出現通知不等於證明該檔為歷史首次公開版本**；`source_version_status=ARCHIVE_RETRIEVED_EDITION_ORIGINALITY_UNVERIFIED`、PIT 日期空白與 `PIT_UNVERIFIED` 仍保持。

既有 GitHub Actions 原始 Artifact 保留原始舊結果作為稽核；需用修正版 `pipeline build` 對原始資料包離線重建，產生新的 CSV 與報告，不得將舊檔原地更改或回填歷史時間。


本次交付為**標準函式庫程式、離線測試與來源受阻報告**，尚未完成歷史資料驗收。
2016、2020、2022 三年目前均為 **0 筆官方觀測**；`out/nass_state_weekly.csv` 僅有欄名。
官方來源遭環境代理拒絕（CONNECT 403），不是 USDA 回報沒有資料，也不是解析成功但沒有州別數據。
使用者已選擇先交付程式與受阻報告。測試範例不會填入正式 CSV。

開發基準：`ed365fbdbe960ac70dd6ed356766907a7267257a`；工作分支：`codex/k37-agent-b-nass`。
依據 Issue #2、根目錄 `AGENTS.md` 與 K3.7 共同契約，僅修改本目錄。

## 重現方式

在 Repository 根目錄，使用 Python 3.10+，無須 pip 安裝套件；系統需有 `America/New_York` 時區資料。
此環境使用 Python 3.12.14。所有預設輸入與輸出都在 `research_core/k3_7/nass/`。

```bash
# 完全離線；測試不要求 API Key、網路或 USDA 當前服務可用
python -B -m unittest discover -s research_core/k3_7/nass/tests -v

# 僅讀已保存的原始位元組與收據；重建成果，不重新標記下載時間
python -B -m research_core.k3_7.nass.pipeline build

# 明確的線上操作；與離線測試分開執行
python -B -m research_core.k3_7.nass.pipeline fetch --max-pages 100
python -B -m research_core.k3_7.nass.pipeline build
```

`build` 成功退出（0）表示離線稽核與輸出流程完成，**不代表已取得資料或通過資料完整性驗收**；
須另檢查 `quality_report.json` 的 `status`、`observation_rows` 與逐年覆蓋率。
`fetch` 遇來源受阻、分頁未走完、未發現報告、未成功下載報告或部分下載失敗時退出 2。
下載成功後仍須執行 `build`，才會得到解析與數據品質結果。
`--max-pages` 是安全上限；到達上限會保留 `PAGE_LIMIT_REACHED`，不宣稱搜尋完整。
使用 `--bundle`、`--output` 可指定隔離資料夾；本任務的輸出應維持在 Agent B 範圍內。

## 檔案

| 路徑 | 用途 |
| --- | --- |
| `pipeline.py` | 官方來源探索、明確下載、逐州解析、離線重建與品質稽核 |
| `data/source_manifest.jsonl` | 追加式下載收據；失敗只記嘗試時間與原因，不製造下載時間或 SHA |
| `data/discovery_log.jsonl` | 分頁、發現數量、未支援連結與來源受阻紀錄 |
| `data/discovered_reports.jsonl` | 發現報告後才產生；保留官方頁面列出的日期與連結及探索頁面 SHA |
| `data/raw/<sha256>.bin` | 成功下載後才產生；原始位元組，不轉碼、不覆寫 |
| `out/nass_state_weekly.csv` | 共同契約 B 所需欄位及附加稽核欄位；本次只有欄名 |
| `out/quality_report.json` | 來源收據、探索與解析異常、時間品質、逐年缺週與缺州清單 |
| `out/quality_report.md` | 可直接閱讀的覆蓋率摘要 |
| `fixtures/`、`tests/` | 明確標記為合成格式樣本的離線測試；不是歷史數據 |
| `VALIDATION.md` | 本次實際執行命令、結果與未通過的資料驗收門檻 |

## 官方來源與探索方式

- ESMIS Crop Progress 歷史頁：<https://esmis.nal.usda.gov/publication/crop-progress>
- NASS 發布排程指引：<https://www.nass.usda.gov/Surveys/Guide_to_NASS_Surveys/Crop_Progress_and_Condition/>

只下載官方頁面實際列出的 `progNNYY.txt` 連結，保留相同日期的所有來源版本。
報告日期必須出現在連結文字／title，且與 TXT 的 `Released` 標頭一致。
只跟隨頁面實際提供的下一頁連結，不用猜測報告檔案 ID，也不以檔名推定報告日期。
只允許上述兩個 HTTPS 官方主機；重新導向前先檢查主機，不停用 TLS 或繞過環境代理。
本次連第一頁都無法取得，因此**沒有任何已發現、可列舉的歷史原文網址**，也沒有可驗證的歷史原文 SHA。
環境允許來源後，重新 `fetch` 即會追加收據，既有收據保留。

## 數據與版本規則

- 只解析當期 `Corn Condition - Selected States: Week Ending ...`；不取其他作物、18 州合計、前週或前年的值。
- 保留完整州名、報告日期、週末日期、ISO 週次、玉米年度 `YYYY/YY`、五類評級與 G+E。
  `iso_week` 是曆法週次，不是種植後第幾週，也不是作物生育階段。
- 每一類必須是整數 0–100；五類總和允許 `100 ± 1` 個百分點。
  99／101 標為 `ROUNDING_TOLERANCE`；超出容許值、負值、缺類或 `(NA)` 等標記均拒收並保存原始異常列。
- 同一表格重複州列會兩列都隔離；不挑一列、不把缺值視為零、不從全國合計反推州值。
- 州名列出但評級被拒收記為 `RATING_REJECTED`；參考州沒有列出記為 `NOT_LISTED_IN_RETRIEVED_TABLE`。
  完整取回但沒有玉米狀況表記為 `NOT_REPORTED_IN_RETRIEVED_REPORT`；不支援表頭、欄序、日期或損毀原文記為 `PARSE_ERROR`。
- 18 州僅作稽核參考（州名見品質 JSON）；其餘 32 州不被假定為每週必報。
  程式可接受官方表內任何美國州名；不能把 18 州解讀為 100% 全美面積普查。
- 每年 4–11 月所有週日僅是顯示缺口的稽核格線，**不是官方報告日曆**。
  未取得的週／州保持未知，不能判為 USDA 未發布；各年完整清單見 `seasonal_coverage`。
- 原文以 SHA-256 保存；不同 URL／不同原文摘要的版次全部保留。
  同 URL 再下載相同內容只輸出一次觀測、沿用第一次實際下載時間；所有下載收據仍保留。
  同州週不同版本數值衝突會輸出全部版本，並標示 `VINTAGE_CONFLICT_PIT_UNVERIFIED`。
  下游不得對這些列直接加總、取最新或當成互相獨立樣本。
- `source_version_status=ARCHIVE_RETRIEVED_EDITION_ORIGINALITY_UNVERIFIED`：
  保存的是本次實際取得的歷史庫版次，**尚不能保證是歷史首次發布的未修訂版**。
  原文的修訂關鍵字會另外記錄。SHA 保證可重現本次取回內容，不認證它在歷史某時已公開。

## 時間證據

| 等級 | 本程式行為 |
| --- | --- |
| `VERIFIED_PUBLIC_TIMESTAMP` | 程式不會自行產生；需 Agent C 提供獨立歷史公開證據後再由整合流程判定 |
| `OFFICIAL_SCHEDULE_PROXY` | 只有成功保存且能明確解析官方週一 16:00 ET 指引時，才寫獨立排程代理欄位；假日週二／週三不套用週一指引 |
| `UNKNOWN` | 沒有可解析的官方指引，或無適用排程；不猜測時分秒 |

`published_at_utc`、`available_at_utc`、`evidence_url` 一律保持空白；即使有排程代理也不填入。
代理時間放在 `scheduled_release_at_utc`，另保留指引 URL 和原文 SHA；DST 用標準時區轉換。
目前指引是回溯研究的代理，不能證明 2016／2020／2022 當時亦適用。
`retrieved_at_utc` 只記實際成功讀完回應的 UTC 時間，離線重建不更動。
HTTP `Last-Modified`、報告日期、檔名與 SHA 都不會升級為已驗證公開時間。
本次兩個請求皆失敗，因此只有 `attempted_at_utc`／`completed_at_utc`，沒有成功下載時間。

## 目前可行性與下一階段

可進行程式碼與研究誠信審查；**不可宣告三年資料齊備，也不可作為 Agent D 的已驗收歷史數據輸入**。
2016、2020、2022 全部參考州與整個季節目前都未取得。沒有已下載卻無法解析的歷史原文；
目前真正的缺口是探索入口遭網路政策拒絕，無從得知哪些個別週／州原本有官方記載。
現有解析器僅經合成格式測試，尚待每個年度的真實原文驗證。

下一輪先允許兩個官方主機，沿用同一命令下載與重建，檢查每年實際原文格式及修訂狀態，
再把固定版次交給 Agent C／D 審查。這樣可持續追加證據，不需要手動搬檔、安裝新套件或改寫 K31–K3.6。
本模組不含模型訓練、投資預測、排程、合併或部署行為。
