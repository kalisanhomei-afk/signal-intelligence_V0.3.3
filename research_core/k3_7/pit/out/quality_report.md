# K3.7 Agent C PIT 證據品質報告

狀態：`SOURCE_FEASIBILITY_BLOCKED`。

輸入 0 筆；ledger 0 筆；拒絕／錯誤 0 筆。

| VERIFIED | PROXY | UNKNOWN | 已通過 as-of 認證 |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |

沒有發布清單時，不產生虛構 UNKNOWN 紀錄；下列缺口是來源／年度，並非已知發布筆數。

| 來源 | 年度 | 實際紀錄 | 清單狀態 |
|---|---:|---:|---|
| WASDE | 2016 | 0 | NO_RELEASE_INVENTORY |
| WASDE | 2020 | 0 | NO_RELEASE_INVENTORY |
| WASDE | 2022 | 0 | NO_RELEASE_INVENTORY |
| NASS | 2016 | 0 | NO_RELEASE_INVENTORY |
| NASS | 2020 | 0 | NO_RELEASE_INVENTORY |
| NASS | 2022 | 0 | NO_RELEASE_INVENTORY |

## 尚缺證據

- WASDE 2016：官方逐期發布清單、原始檔、歷史實際公開時間證據及 SIGNAL 下載收據。
- WASDE 2020：官方逐期發布清單、原始檔、歷史實際公開時間證據及 SIGNAL 下載收據。
- WASDE 2022：官方逐期發布清單、原始檔、歷史實際公開時間證據及 SIGNAL 下載收據。
- NASS 2016：官方逐期發布清單、原始檔、歷史實際公開時間證據及 SIGNAL 下載收據。
- NASS 2020：官方逐期發布清單、原始檔、歷史實際公開時間證據及 SIGNAL 下載收據。
- NASS 2022：官方逐期發布清單、原始檔、歷史實際公開時間證據及 SIGNAL 下載收據。

## 來源存取紀錄

- https://www.usda.gov/historical-wasde-report-data-3：SOURCE_UNAVAILABLE；嘗試時間 2026-11-13T06:49:50.876827Z；URLError: <urlopen error Tunnel connection failed: 403 Forbidden>
- https://esmis.nal.usda.gov/publication/crop-progress：SOURCE_UNAVAILABLE；嘗試時間 2026-11-13T06:49:50.910322Z；URLError: <urlopen error Tunnel connection failed: 403 Forbidden>
- https://www.nass.usda.gov/Surveys/Guide_to_NASS_Surveys/Crop_Progress_and_Condition/：SOURCE_UNAVAILABLE；嘗試時間 2026-11-13T06:49:50.920743Z；URLError: <urlopen error Tunnel connection failed: 403 Forbidden>

## 驗收限制

稽核與資料取得成功均不自動代表正式 PIT 認證。預設 SYSTEM_REPLAY 必須驗證公開時間與 SIGNAL 實際取得時間皆不晚於 as-of；PUBLIC_INFORMATION_AUDIT 必須明確標示，不能宣稱 SIGNAL 當年已持有資料。

人工核准的文件解讀是信任邊界。SHA-256 核對只證明保存位元組一致，不認證第三方真實性；官方排程、HTTP Date／Last-Modified、目前下載時間及檔案 mtime 皆不足以認證歷史公開時間。

Agent D 後續必須以 source_type、source_release_date、source_url、vintage_id、source_sha256 精確核對，重新稽核原始證據並執行 as-of gate。不得只依日期 join 或信任 CSV 分級欄位。
