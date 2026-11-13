# K3.7 Agent A：WASDE 歷史發布版本

本模組只處理 **2016、2020、2022 發布年份**的美國玉米資料，不限制為
當年度 marketing year，因此保留同一發布中的各個 marketing year、估計及
預測。未修改既有 K31～K3.6，使用 Python 3.10+ standard library，無新增套件。

**本次交付狀態：程式與離線測試完成；真實資料回填尚未驗收。**
執行環境以 CONNECT 403 阻擋 USDA，使用者已同意先交付程式、離線測試與
來源受阻報告。`out/wasde_vintages.csv` 只有標頭，`out/manifest.json` 記錄
36 個待檢查月份均為 `SOURCE_UNAVAILABLE`；這不代表 USDA 未發布報告。
沒有下載成功的原始資料、來源雜湊或 PIT 認證。詳見 `SOURCE_FEASIBILITY.md`。

## 重現指令

從 Repository 根目錄執行離線測試，不需要網路或安裝套件：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s research_core/k3_7/wasde/tests -v
```

本次 34 項全部通過；`TEST_RESULTS.txt` 保存完整輸出，以及 7 組既有模組
回歸結果（136 通過、1 略過）。測試使用明確標示的人工格式範例，並非 USDA
觀測值。真實官方原始檔的 fixture 與比對仍待取得來源後補做。

在允許 USDA 的環境中進行線上下載，使用新的輸出目錄：

```bash
python research_core/k3_7/wasde/pipeline.py \
  --output research_core/k3_7/wasde/work/online-run-1 \
  --raw-dir research_core/k3_7/wasde/raw
```

若下載成功，保留原始檔與 manifest，可完全離線重新解析：

```bash
python research_core/k3_7/wasde/pipeline.py \
  --replay research_core/k3_7/wasde/work/online-run-1/manifest.json \
  --raw-dir research_core/k3_7/wasde/raw \
  --output research_core/k3_7/wasde/work/replay-run-1
```

Exit code `0` 僅代表 36 個月份都有完整通過稽核的觀測，仍是 PIT 未驗證；
exit code `2` 代表來源受阻、缺漏、解析／完整性問題或來源版本衝突。
輸出目錄必須是空的；已有資料時拒絕覆寫。每次執行使用不同目錄，保留先前
版本與 manifest，審核後再以新的版本提交作為交付資料，不應直接覆蓋舊紀錄。
預設 `out/` 已包含本次受阻結果，直接執行預設指令會拒絕覆寫，屬預期保護。

## 解析及來源規則

- 從官方 archive 的實際 HTML link target 發現檔案，不猜測每月下載網址。
  2016／2020 使用官方 2016–2020 ZIP；2022 使用逐月 CSV。解壓後僅選取
  pilot 年份；不輸出 2017–2019 或其他年份。
- 原始下載 bytes 以 SHA-256 命名，存於 `raw/`；每次下載另存 acquisition
  receipt。相同內容再次下載保留新的實際 retrieval time，不更動先前 receipt。
  ZIP 的 `source_sha256` 是整個下載 ZIP，另以 `source_member` 與
  `source_member_sha256` 指明內部 CSV；不把解壓檔案的雜湊冒充下載雜湊。
- `source_url` 記錄成功下載後的確切官方 URL；僅允許 HTTPS USDA 主站與官方
  mirror，redirect 在下一個 request 之前檢查。無自動改寫 mirror 網址。
- 保留 release date、marketing year、projection/estimate flag 與每個 source
  hash；不以最新值覆蓋歷史發布。相同 release／year／metric 若有不同來源
  hash，全數保留並標記 `SOURCE_VERSION_CONFLICT`，交由人工審查。
- Schema 必須包含具名欄位、`AnnualQuarterFlag`；日期支援 ISO 與美式數字
  日期。未知格式失敗並留下 `PARSE_ERROR`。未知的表內 attribute 原文列入
  audit，不猜別名；缺少任何必要 metric 時標記 `INCOMPLETE_METRICS`。

最少八項 metric 為 harvested area、yield、production、beginning stocks、
imports、total domestic use、exports、ending stocks。metric 名稱沿用
`k3_4/integrate.py`，例如 `production_million_bushels`。unit 保留 K3.4 使用的
`Million Acres`、`Million Bushels`、yield 的 `Bushels`；yield 的每英畝語意由
官方 attribute 與 `yield_bushels_per_acre` 表達。沒有跨單位猜測或默默換算。

## 完整性及時間證據

稽核同一 release／marketing year 的供需式：

`beginning stocks + production + imports = domestic use + exports + ending stocks`

並檢查已報告的 total supply、total use、domestic use components。供需容許
3 million bushels 的整數四捨五入誤差，沿用既有 K3.4 容許值；記錄每個
residual 與 tolerance。面積乘單產另檢查與 production 的一致性，採 area 與
yield 各四捨五入至 0.1、production 至 1 million bushels 的誤差上界：
`yield*0.05 + area*0.05 + 0.5025`。不更改原始數值以滿足平衡。

錯誤單位、非數字、缺值、負值、重複 metric 或 balance mismatch 會拒收整個
cohort，原始 bytes 與拒收原因仍保留。缺少必要 metric 的其餘已解析數值可以
輸出，但均標記 `INCOMPLETE_METRICS` 並使完整覆蓋門檻失敗。ZIP 任一 member
有無法解析的 schema／重複 cohort 時，整個來源失敗，不偷偷保留部分成功。

`retrieved_at_utc` 是成功下載完成時的當下 UTC；離線 replay 保留原 receipt
時間，不假裝重新下載。`published_at_utc`、`available_at_utc`、`evidence_url`
全部留白，`timestamp_quality=UNKNOWN`，正常數值也標記 `PIT_UNVERIFIED`。
不把 release date、預定發布時間、ZIP metadata、HTTP Last-Modified 或本次
retrieval time 當成歷史公開時間；時間認證交由 Agent C／後續整合處理。

Manifest 區分 `SOURCE_UNAVAILABLE`、來源 HTTP 404 的
`MISSING_SOURCE_RESOURCE`、`PARSE_ERROR`、`MISSING_OFFICIAL_RELEASE`
（僅表示已檢查來源中未觀測到）與不完整／拒收 cohort。即使 HTTP 200，若沒有
可辨識的 pilot 連結也視為格式問題，不認定全部月份未發布。

## 後續驗收

下一步可審查程式與來源受阻報告；目前不應將此輸出送入完整資料整合或宣稱
Issue #1 的歷史資料驗收已通過。取得來源後，使用同一指令下載、保留原始
檔、加入最小官方 fixture、逐年份比對發布版本與單位／平衡，再決定交付 Agent D。
維持本套可重現下載與 cache／replay 流程，避免人工下載 ZIP 與搬移資料。
