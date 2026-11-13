# K3.7 Agent C：歷史公開時間證據稽核

Python 3.11+、標準函式庫；僅研究用途。所有新增檔案均位於本目錄，不修改 A/B、共用契約或既有研究模組。

本次實際交付是**可執行稽核器、離線測試及來源可行性報告**。WASDE 歷史資料索引、ESMIS Crop Progress 索引及 NASS 說明頁的三次實際請求均遭環境 proxy `CONNECT 403` 拒絕。既有 K3.4.1 凍結輸入只有 2023–2026 年，沒有本次指定年度。依 orchestration 的來源不可取得規則，保留空的真實 ledger，不推測日期、週次、每年發布筆數或逐期 URL。

真實紀錄：VERIFIED **0**、PROXY **0**、UNKNOWN **0**，as-of 認證 **0**；2016、2020、2022 × WASDE、NASS 共 **6 個來源／年度清單缺口**。零筆不是資料完整或 PIT 通過，也不是六筆 UNKNOWN 發布紀錄。`fixtures/` 全部為虛構測試資料，未進入 `inputs/manifest.json` 或真實 ledger。

## 可重現命令

從 repository 根目錄執行：

```sh
python -m unittest discover -s research_core/k3_7/pit/tests -v
python -m research_core.k3_7.pit.audit
```

離線命令不連網，固定輸入可產生相同 CSV、JSON、Markdown。預設輸入 `inputs/manifest.json`，輸出 `out/`：

- `pit_evidence_ledger.csv`：逐來源／發布日期／版次的裁定；目前僅標題列。
- `quality_report.json`、`quality_report.md`：完整三種分級數量、六個年度缺口、尚缺證據、實際來源存取結果及限制。
- `rejections.json`：輸入錯誤及原紀錄索引；任何錯誤均阻擋整個 bundle 認證，避免遺漏的衝突紀錄被忽略。
- `verification.json`：本次實際測試命令、結果及保留限制。

如要要求每筆都可進入特定 as-of 的正式檢查：

```sh
python -m research_core.k3_7.pit.audit --as-of 2022-12-31T23:59:59Z
```

目前會以 `EMPTY_CERTIFICATION_COHORT` 拒絕、exit code 2。一般離線稽核 exit 0 只代表稽核程序完成，必須讀取 report 狀態；不代表來源齊全、任何資料通過認證或可開始正式回測。輸入無效或 `--as-of` 檢查失敗則 exit 2。

需要另行進行「當時公眾理論上可知」研究時，明確指定 `--mode PUBLIC_INFORMATION_AUDIT --as-of ...`；輸出會標示 `signal_historical_possession_claim=false`。預設 `SYSTEM_REPLAY` 要求 `published_at <= available_at <= retrieved_at <= as_of`。

## 輸入與原始證據

Manifest 為 UTF-8 JSON，頂層 `schema_version: 1`、`records: []`。每筆紀錄包括：

原始證據 bundle 請保存於 `inputs/` 下；本目錄的 `.gitattributes` 禁止 Git 改寫 `inputs/` 與 `fixtures/` 的換行，以保留原始 SHA-256。輸出 CSV 使用固定 LF。

| 欄位 | 規則 |
|---|---|
| `source_type` | `WASDE` 或 `NASS`；本次 NASS 目標為 Crop Progress／Condition |
| `source_release_date` | 來源所述 ISO 日期，限 2016、2020、2022；不是 week ending 或下載日期 |
| `source_url` | 已知官方原始資源 HTTPS URL；不得由日期樣板猜出未曾取得的 URL |
| `source_path`, `source_sha256` | 相對 bundle 路徑與原始位元組 SHA-256；不進行換行／BOM 正規化。無原檔可留空，但不能 VERIFIED |
| `vintage_id` | 該報告版次的識別值；同來源／日期內不可重複 |
| `revision_kind` | `INITIAL` 或 `CORRECTION` |
| `supersedes_vintage_id` | 更正版必填，指向同來源／發布日期的前一版；禁止缺失、循環、同原始位元組偽更正及非遞增更正時間 |
| `retrieval_receipt` | 可選 `{path, sha256}`，指向原始 SIGNAL 下載收據；未提供時不推測下載時間 |
| `evidence` | 原始證據與核准紀錄陣列；空陣列保持 UNKNOWN |

同一原始檔可能包含多個商品／指標；ledger 以檔案版次為單位，Agent D 必須按 source_type、source_release_date、source_url、vintage_id、source_sha256 一致性對接，不能僅按同日連接。既有 producer 的 `timestamp_quality`、`published_at_utc`、`available_at_utc` 或 `pit_certified` 宣告不作為證據；直接輸入 `retrieved_at_utc` 被拒絕，須提供原始收據。

每份 evidence 的欄位：`kind`、`url`、`path`、`sha256`、`format`、`captured_at_utc`、`review`。支援原始 UTF-8 `text/plain`、`text/html`、`application/json`；不假裝能核驗二進位 PDF 的文字。檔案不得逃出 bundle（包括 symlink）；雜湊須對上實際檔案。

`review` 必須包含 `verdict: APPROVED`、非空 `reviewer`／`reason`、`reviewed_at_utc`、原文 `quote`，以及精確綁定的 `source_type`、`source_release_date`、`source_url`、`source_sha256`、`vintage_id`。review 時間不得早於保存證據時間，quote 必須逐字存在原始檔；不得由代理自行捏造第三方原文或核准。測試的虛構核准只適用測試。

## 分級規則

| 證據 | 結果與額外欄位 |
|---|---|
| `PUBLIC_RELEASE_LOG` | 只有經審閱、具有獨立保管來源且明確證明**同一原始位元組**實際首次發布和公開可取得時刻的紀錄，才可 VERIFIED |
| `OFFICIAL_SCHEDULE` | 僅 PROXY，時間放 `official_schedule_utc`；不填 verified 時間欄位 |
| `ARCHIVE_CAPTURE` | 只記 `observed_public_by_utc` 上限；不能聲稱最早公開時間，單獨使用時 UNKNOWN |
| `HTTP_METADATA`, `REPORTED_DATE`, `CORRECTION_NOTICE` | 保存文件及理由，單獨使用時 UNKNOWN；不把 HTTP Date、Last-Modified、文件日期或更正通知當成 exact proof |
| 無證據或互相衝突 | UNKNOWN；不退回排程作為實際時間、不取較早／較方便的時間 |

`PUBLIC_RELEASE_LOG` 的 review 另需：

- `assertion: ACTUAL_PUBLICATION_AND_AVAILABILITY_FOR_EXACT_BYTES`、`independent_custody: true`；證據 host 必須不同於原始來源，且不能是 USDA 本身或其既有鏡像。
- `published_at_utc`、`available_at_utc`：明確有時區的 ISO 時刻，兩者與 source SHA-256 都須逐字出現在原文 quote。只接受可直接核對的保守格式；缺乏這些資訊不自動升級。
- `published_at <= available_at <= captured_at`；若有 SIGNAL 收據，亦要求 `available_at <= retrieved_at`。
- INITIAL 的發布時刻轉成 `America/New_York` 後須與所述發布日期相同。更正版不得早於該日期及前一版實際發布時刻；允許同日較晚更正。

`OFFICIAL_SCHEDULE` 的 review 另需 `assertion: SCHEDULE_ONLY`、`scheduled_local`、`timezone: America/New_York`，必要時提供 `offset`。核准者須確認原文適用該逐期日期；一般政策不能冒充逐期實際上線證據。時間轉換拒絕春季不存在的時刻，秋季重複的時刻必須明確指定合法 offset。NASS 假日延期不得以固定週一推測。

`ARCHIVE_CAPTURE` 的 review 另需原文可核對的 `observed_public_by_utc`。若早於另一份證據宣稱的「最早可取得時刻」，視為衝突。官方排程和實際發布不同時，保留兩者，因為延遲或提前不等於互相矛盾的實際時間證據。

主 `evidence_url`、`evidence_sha256`、`evidence_format` 只在 VERIFIED 時填入，遵守共用契約；PROXY／UNKNOWN 的原始網址、雜湊、格式、核准與理由完整保存在 `documentary_evidence` JSON 欄位。多份有效證據以 `|` 分隔主欄位並保留完整陣列。

## 版本與認證

`published_at_utc` 是**該版**發布時刻；`first_published_at_utc` 是原始 INITIAL 時刻（有證據時），`corrected_at_utc` 是該更正版的發布時刻。更正時間不能回填初版時刻。缺少更正本身的獨立時間證據時，即使初版 VERIFIED，更正版仍 UNKNOWN。

CSV 的 `pit_certified` 永遠 `false`：靜態時間證據分級不是特定回測的認證。正式流程應使用 `certify_manifest(path, as_of, mode="SYSTEM_REPLAY")`，重新核對原始檔及證據，不信任可改寫的 CSV。此 API 對**所有提供的紀錄**逐筆檢查，有任何 UNKNOWN、PROXY、未來版本或未實際取得紀錄即拒絕。它不替 D 做 cohort 選取，也不整合 A/B 輸出。

**信任限制**：這是人工核准文件的獨立稽核程序，不是第三方簽章驗證系統。SHA-256 只驗證保存位元組一致性，不證明發行者、reviewer 身分、第三方真實性或收據未被偽造。人工核准必須真的審查獨立保管來源及逐版精確時間；不能因 URL 不同就自行認證。下載收據需來自可信 SIGNAL 收集流程。若目前下載的檔案缺乏和歷史證據匹配的原始位元組，不能稱為歷史 PIT。

## 線上來源可行性與後續步驟

```sh
python -m research_core.k3_7.pit.collect --output research_core/k3_7/pit/inputs/new-source-probe
```

這是明確的線上命令，與測試分開；三個 locator 均源自既有 K3.3／K3.4／K3.4.1 程式中的已知 URL。它只保存本次真實嘗試時間、成功原始檔與本次下載收據，不推斷發布清單、不將 locator 內容當成時間證據。失敗不填 retrieved_at 或 source_sha256；成功也僅標示 `FETCHED_LOCATOR_NOT_TIME_EVIDENCE`。既有 capture 名稱不覆寫，重新探測須用新目錄。重現本次離線結果不必再執行。

後續最省人工的流程：先允許所需 USDA／ESMIS 來源，再取得三個年度的正式逐期清單；以不可變 bundle 保存原檔、下載收據、獨立歷史時間文件及審閱紀錄。另建 manifest 指向新 bundle、重跑同一稽核器，無需手工搬移或修改 A/B CSV。無法取得的時間繼續 UNKNOWN。需要新增 archive host 時，先確認其證據能力及可公開保存範圍。

本次可進入程式碼／規則審查；在補齊官方資料與歷史證據、完成 A/B/C 逐版核對前，**不能進入正式 PIT 認證回測**。不 merge、不部署、不訓練預測模型。
