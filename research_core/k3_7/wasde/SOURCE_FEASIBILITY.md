# USDA WASDE 來源可行性與本次驗收

本次依使用者確認，先交付程式、離線測試與來源受阻報告。
**未完成官方資料回填與線上解析驗證，不應關閉 Issue #1 的資料驗收。**

## 已觀察到的來源資訊

獨立 web lookup 可讀到 [USDA Historical WASDE Report Data](https://www.usda.gov/historical-wasde-report-data-3)。
該頁說明 consolidated data 保留各次報告中的數值，不納入報告發布之後才出現的
修訂；individual publications 仍是 official data of record。因此這裡支援的是
**官方 consolidated release vintages**，不聲稱取得當年原始上傳檔案或當年
公開時間的證據。

該目錄確實提供：

- [January 2016 to December 2020 ZIP](https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-2016-01-to-2020-12.zip)：
  本模組只取 2016、2020 的發布資料。
- 2022 逐月 CSV，例如 [January 2022](https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-2022-01.csv)。

Web 工具不提供 CSV／ZIP 原始 bytes（回報 unsupported content type）；其頁面
摘要不能用來產生下載原始雜湊、取得時間或真實測試 fixture。上述資訊用於
來源可行性與格式選擇，沒有轉成已下載的 observation。

## 實際線上嘗試

從 Repository 根目錄執行：

```bash
PYTHONDONTWRITEBYTECODE=1 python research_core/k3_7/wasde/pipeline.py --output research_core/k3_7/wasde/out --raw-dir research_core/k3_7/wasde/raw
```

本次嘗試時間：2026-11-13 14:51:01（Asia/Taipei）；精確 UTC 見 manifest。
Archive request 回報：`URLError: <urlopen error Tunnel connection failed: 403 Forbidden>`。
這是執行環境 proxy 的 CONNECT 拒絕，並非官方來源回傳 404，也不是官方未發布
報告的證據。先前對 `usda.azureedge.us` 的 CSV 探測也遇到 CONNECT 403。
未繞過網路限制、未改用第三方資料，也未新增套件或索取憑證。

Observed stdout：

```json
{"coverage_counts": {"SOURCE_UNAVAILABLE": 36}, "records": 0, "status": "PARTIAL_OR_BLOCKED", "verified_pit_records": 0}
```

Exit code：`2`（如實表示未通過完整資料門檻）。

| 發布年份 | 待檢查月份 | 已下載且解析成功的發布 | Observation rows | 狀態 |
| --- | ---: | ---: | ---: | --- |
| 2016 | 12 | 0 | 0 | SOURCE_UNAVAILABLE |
| 2020 | 12 | 0 | 0 | SOURCE_UNAVAILABLE |
| 2022 | 12 | 0 | 0 | SOURCE_UNAVAILABLE |

36 是 pilot 的月份檢查清單，不代表觀察到 36 次官方發布或逐一檔案的 36 次
request。Archive discovery 已受阻，因此沒有逐一取得原始檔的 URL／日期。
不能判定是否缺少特定發布，也無法檢查真實來源 schema 的歷史變化。

產物：`out/wasde_vintages.csv` 僅有 18 欄標頭；`out/manifest.json` 包含實際
嘗試時間、錯誤及 36 個月份的明確狀態。沒有 download raw bytes，故沒有
`source_sha256` 或虛構的 `retrieved_at_utc`。PIT 認證數為 0。

## 離線驗證與限制

環境：Python 3.12.14。新模組 34 項通過；既有 K31、K3.2、K3.3、K3.4、
K3.4.1、K3.5、K3.6 合計 136 通過、1 略過。合計 **170 通過、1 略過、0 失敗**。
K3.2 既有略過理由：`K3.1 not installed in local fixture`；未修改該測試或程式。
完整命令與 observed output 見 `TEST_RESULTS.txt`。

離線測試確認人工格式範例的數值、版本、稽核與失敗處理，不能證明實際官方
ZIP／CSV 的相容性。仍待完成：官方原始 fixture、各年發布覆蓋、實際
marketing year／unit／供需平衡比對、原始報告 spot-check，以及獨立 PIT 證據。

恢復來源時需要允許執行環境連到 `www.usda.gov`；官方 redirect 如涉及
`usda.gov` 或 `usda.azureedge.us` 也需允許。使用 README 中的新 run 目錄指令
下載並保存 raw cache，不應更改本次受阻結果來假裝先前成功。
