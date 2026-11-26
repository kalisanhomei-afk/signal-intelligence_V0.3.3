# SIGNAL R1c｜2020-03-16 TIC 歷史 ZIP 收據接收及 PIT 風險審查

**日期：2026-11-22 Asia/Taipei。狀態：EXTERNALLY_CAPTURED, REPORTED_HASH_CROSSCHECKED; HISTORICAL_PIT_NOT_VERIFIED。** 本文件根據使用者提供的 Antigravity 原始執行報告建立。GitHub 此次保存收據**中繼資料**及風險評估，不保存 ZIP 本身；ChatGPT 尚未取得本機 `research_raw/` 中原檔，不主張獨立重算 SHA-256。

## 2026-11-22 後續 R1c 單一新聞稿數值比對（最新驗收；覆蓋下方待辦）
**判定：SINGLE_CELL_VALUE_MATCH = PASS（Antigravity 外部實測回報；非 ChatGPT 本機取得原始位元組複核），HISTORICAL_PIT_VERIFIED = false，Gate 0 = BLOCKED。** 2026-11-22 接獲 Antigravity 的唯讀 CSV 抽取與算術交叉檢查，未重新下載資料、未修改 ZIP 或程式。先前「CSV_VALUE_MATCH_NOT_TESTED」係當時狀態，已由本節取代。

### 可追溯定位
- 外層 ZIP：`20261122T043451_627322Z_4c8b61acb508.zip`，先前回報完整 SHA-256 `4c8b61acb50851f277168b5b897ffd5aba5cab2fb589d44ef74c75890a3b4196`，存於 Antigravity 本機 `research_raw/`，未提交 GitHub。
- 成員：`npr_history.csv`，95,727 bytes，515 行、33 欄；外部 Python `hashlib.sha256` 回報該成員 SHA-256 `20e93f3f8a7076f5274504d0c7a018921c05e924a9379e912629720e956bb6e4`，ZIP metadata 時戳 `2020-03-11 19:26:12`（時區未知；不作當時位元組證明）。
- 檔頭 L1 顯示 `TIC monthly reports on Cross-Border Portfolio Financial Flows through January 2020`；L2 有 `16-Mar-20`，單位 `($ millions)`。
- 資料排列：L3–L12 多層欄名；L13 新聞稿列號 `[1]` 至 `[32]`；L14 分隔；**L15 為 2020-Jan**。目標欄位是 **第 31 欄（1-based；CSV index=30；Excel AE）**，標籤 `[30]`，L9–L12 逐行標為 `Monthly / Net / TIC / Flows`。
- L15、第 31 欄原始 `122883` 百萬美元，正向淨流入，轉換 `+122.883` 十億美元，四捨五入至小數一位 `+122.9`，符合財政部 [2020-03-16 官方當次新聞稿](https://home.treasury.gov/news/press-releases/sm943) 2020-Jan「Monthly Net TIC Flows」公布值 `+122.9 USD billions`。

### 兩項獨立欄位算術核對（全在 L15，單位均為百萬美元）
- 新聞稿行 `[21]`（CSV index 21；col22）=`-3778`，`[22]`（index 22；col23）=`5067`，`[29]`（index 29；col30）=`121594`。**-3778 + 5067 + 121594 = 122883**，等於 `[30]`。
- 新聞稿行 `[31]`（index 31；col32）私人淨額 `94141`，`[32]`（index 32；col33）官方淨額 `28742`。**94141 + 28742 = 122883**，等於 `[30]`。`94.141` 十億美元四捨五入 `94.1`、`28.742` 四捨五入 `28.7`；這解釋新聞稿兩個已四捨五入分項顯示值合計 `122.8`，總額顯示 `122.9` 的表面差異。

### 證據強度與不得升級事項
1. **PASS 僅證明** 2026 年本機取得之官方封存 ZIP 中的這一個指定日期/欄位，對應 2020-03-16 當次新聞稿的**公布數值一致**。它沒有證明 ZIP 內所有 49 個成員都未被事後修訂，其他月份數值也未驗證。
2. CSV 與 ZIP 的 SHA-256 是 **Antigravity 外部實測回報並在該執行環境核對**；原始 bytes 沒有交到 ChatGPT runtime；此處沒有假裝在本機重新算出原始 SHA。
3. `slt3d_globl.tic` 的 `QUARANTINE_TIMESTAMP_POST_RELEASE` **不解除**；其餘成員仍維持 `HISTORICAL_BYTES_NOT_CERTIFIED`。即使新聞稿指定欄位吻合，也不能證明當期交易前的完整 PIT 覆蓋、逐檔修訂或精確發布 UTC。
4. `accepted_for_model=false`、`license_status=UNVERIFIED`、可交易股市/美元現金含息總報酬代理尚未驗證；**Gate 0 = BLOCKED，無 R2 模型／交易啟用**。
5. **下一步**：停止重複下載同包 ZIP 與重新比對這一欄，先獨立完成資料使用權、可交易含息報酬來源以及另一個日期的版本差異樣本，才能重新評估 PIT／Gate 0；不為了蒐集 49 個成員擴張範圍。


## 1. 歷史來源定位（官方公開頁已另行查核）

- TIC [官方月度資料封存頁](https://home.treasury.gov/archives-of-tic-monthly-data-releases) 列有「03/16/2020 TIC Data for January 2020」。官方說明每個 ZIP 包含該檔名日期公布的 TIC 資料，**但此說明不足以證明 2026 目前下載的 ZIP 所有內部成員都和 2020-03-16 的位元組完全一致**。
- 根據 Antigravity 對封存 HTML 錨點的查核，請求 URL：`https://www.treasury.gov/resource-center/data-chart-center/tic/Documents/ticrel_20200316.zip`；回應最終 URL：`https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/ticrel_20200316.zip`。請求與最終網域皆符合 R1c Treasury allowlist，且同機構 HTTPS 重新導向。
- 當次 2020 年 1 月觀察資料的官方新聞稿：[2020-03-16 TIC release](https://home.treasury.gov/news/press-releases/sm943)。
- [TIC 官方發布與修訂規則](https://home.treasury.gov/data/treasury-international-capital-tic-system/release-dates-of-tic-data)：2014-09-16 起一般在 16:00 Eastern 公布；通常公布前 3 個月的修訂，部分月份修訂前一年的資料，重大修訂可能更久。**一般時刻不等於逐件已驗證的公布 UTC 秒數。**

## 2. Antigravity 現場回報（擷取成功 ≠ 歷史版本認證）

| 欄位 | 回報值 |
|---|---|
| URL | `https://www.treasury.gov/resource-center/data-chart-center/tic/Documents/ticrel_20200316.zip` |
| HTTP / Content-Type | `200` / `application/zip` |
| 目前檔案取得時間 UTC | `2026-11-22T04:34:50.834165Z` → `2026-11-22T04:34:51.627322Z` |
| ZIP 大小 | `2,810,284` bytes |
| ZIP 檔 SHA-256 | `4c8b61acb50851f277168b5b897ffd5aba5cab2fb589d44ef74c75890a3b4196` |
| 收據 JSON SHA-256 | `6282a8fe6b6bc1e06cd470a5236a9a7d2462e010f6930eae65e2496c7b09b6f8` |
| HTTP Last-Modified | `Tue, 10 Feb 2026 15:47:24 GMT` |
| ETag | `"41acd0733af2e60980f78f267071a509:1770738444.506209"` |
| ZIP 內部目錄 | 49 成員、總宣告未壓縮 `23,116,176` bytes、總壓縮 `2,803,534` bytes |
| 下載保留位置 | Antigravity 本機 `research_raw/`（Git 忽略）；**未上傳**原始 ZIP 至本次 ChatGPT 或 GitHub |
| 官方歷史原始版認證 | `false` |
| 模型准入 | `false` |
| 授權 | `UNVERIFIED` |

Antigravity 回報 SHA-256 經同一外部執行環境 `sha256sum` 複核一致；**ChatGPT 只核對正式 GitHub 狀態、官方封存說明及報告內部一致性，未得到可獨立逐位元組複核的 ZIP**。不能將「這一份 2026 年取得的 bytes 之 SHA」說成「2020-03-16 發布當時的原始 bytes 之 SHA」。

## 3. 高風險發現及反證限制

- **報告指出** 49 個 ZIP 成員中有 48 個內部時間戳在 2020-03-08～13，`slt3d_globl.tic` 為 `2020-04-10 17:00:00`，晚於封存所標示 2020-03-16 近 25 天（無明確 ZIP 時區）。
- 這個事實**高度削弱「整包 ZIP 必然是發布當日位元組不變快照」的主張**；但 ZIP 成員時間戳只是封存中可攜帶、可變動的 metadata，**不能單憑此推定該成員實際數值於 4 月 10 日改動**。需要另外的同時期 bytes 或官方修訂證據。
- 財政部的 [2023 TIC 格式變更說明](https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/tic-forms-instructions/securities-a-us-transactions-with-foreign-residents-in-long-term-securities) 確認 `slt3d_globl` 等舊檔為美國公債相關持有資料系列，後續由 `slt_table3` 取代。此成員亦不等於「全部資金流量」。
- HTTP `Last-Modified` 在 2026-02-10，屬伺服器所提供的快取／檔案 metadata；可能反映遷移、重新上傳或重寫，不足以證明內部數值在 2026 才修訂；亦不足以支持位元組從 2020 起不變。
- **處理決定：整個 2020-03-16 ZIP 作為「2026 現時官方封存」證據保存；`slt3d_globl.tic` 標記 `QUARANTINE_TIMESTAMP_POST_RELEASE`；其他 48 成員標記 `HISTORICAL_BYTES_NOT_CERTIFIED`，不因檔內日期較早就獲准入模型。**

## 4. 下一個最小可驗證動作（只做一輪，避免原檔重複抓取）

1. 在**保存同一份原始 ZIP** 的 Antigravity 本機，核對 `npr_history.csv` 內「2020/01／2020-03-16」對應的官方新聞稿欄位（請先核對欄位定義，不預設名目），與 [2020-03-16 官方當次新聞稿](https://home.treasury.gov/news/press-releases/sm943) 對照。先只檢查**一個有明確定義的數值**，包含單位、正負方向、是否為修訂值；不得拿最新歷史列直接冒充當時的公布值。
2. 若 `npr_history.csv` 內無法明確對應，改由 ZIP 中適當的 `.txt` 檔找到發布日新聞稿數值，**先核對其資料定義及觀察月份**。沒有正確對應就記錄 `BLOCKED`，禁止靠猜測。
3. 針對 `slt3d_globl.tic`，要得出「2020-03-16 時已可用」必須有**另一份發布當日的位元組／可信 contemporaneous 發布證據**；若無，保持 quarantine，勿為了追求完整歷史而無限重試。
4. 若研究需要用到同一類 TIC 指標，優先選一個在 2010–2026 有一致定義、可逐發布日辨識的**候選欄位**，先驗四個時點，而不是解讀所有 49 個成員。
5. 扣除成本後的可交易股市／短券總報酬來源與權利仍未確認，因此**Gate 0 BLOCKED、R2 不啟動**。

## 2026-11-22 官方欄位字典與最小數值核對錨點（追加唯讀查核）
- 財政部官方封存欄位字典： https://ticdata.treasury.gov/Publish/arcdatadesc.pdf 。在「REFERENCE: Archived Files RELEASED BEFORE APRIL 2023」章節，`npr_history.csv` 定義為每個新聞稿資料列的歷史數字；該官方定義已另行查核，不代表 CSV 原始列已讀取。
- 2020-03-16 當次新聞稿： https://home.treasury.gov/news/press-releases/sm943 。在 2020 年 1 月欄位，`Monthly Net TIC Flows (lines 21,22,29) /8` = **+122.9 USD billions**，`Private, net` = **+94.1**，`Official, net` = **+28.7**。後兩者顯示值加總為 122.8，與總數差 0.1；可能受各自四捨五入影響，不視為本次 CSV 比對失敗。
- **精確待驗收項目**：在 Antigravity 本機既有 ZIP 中以 Python `zipfile.ZipFile(...).open("npr_history.csv")` **唯讀**查看 CSV 標頭／資料排列（不可預測 CSV 是直向或橫向）；先尋 2020 年 1 月 +「Monthly Net TIC Flows」對應的**同一交叉欄位**，檢查數值、符號、單位。提供原始欄位名稱、行號、欄號、所在行/欄必要上下文和結果。不要只搜尋 ZIP 中的 `122.9`，以免把其他項目的數值誤認為該項。必要時再用 +94.1/+28.7 交叉驗證。
- **狀態**：PRESS_RELEASE_VALUE_VERIFIED；CSV_IN_ZIP_NOT_READ_HERE；VALUE_MATCH_NOT_TESTED；PIT_VERIFIED=false；Gate 0 BLOCKED。禁止因精確新聞稿數值已知就自行填寫 CSV 比對為 PASS。
- 此次額外查核利用新聞稿及官方字典，不重新下載 ZIP，也不重跑已成功的測試。

## 5. 驗收與範圍
- `R1c_H6_CAPTURE`: EXTERNAL_BYTES_REPORTED（前次 Antigravity 報告）；`R1c_TIC_CAPTURE`: EXTERNAL_BYTES_REPORTED，ZIP directory externally inspected。
- `RAW_BYTES_IN_CHATGPT_RUNTIME=false`、`RAW_SHA256_INDEPENDENTLY_REPRODUCED_HERE=false`、`HISTORICAL_PIT_PASS=false`。
- 本輪僅更新既有 Draft PR #29 的研究證據（本文件、JSON metadata 及 `CURRENT_STATUS.md`）；不修改正式部署、歷史預測、交易或授權設定，不新增排程，不手動重跑已過的測試。
