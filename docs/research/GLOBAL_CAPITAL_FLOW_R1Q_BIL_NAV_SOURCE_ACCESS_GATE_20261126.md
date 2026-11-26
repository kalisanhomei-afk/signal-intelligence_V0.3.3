# SIGNAL R1q｜BIL NAV 官方原始檔存取與反分割證據檢查（2026-11-26）

**本輪實作與證據界限：** 唯讀檢查官方 State Street BIL 產品頁 / 正式 NAV History 下載鏈結、官方配息資料入口及 SEC 原始文件；嘗試由現有執行環境直接取得 BIL .xlsx **失敗**。本輪沒有 BIL 原始位元組、沒有新 SHA-256、沒有工作表讀取與逐列 NAV 驗證；**不得宣稱 BIL NAV 檔已驗收**。

## 1. 已驗證官方固定下載地址（來源頁 click 實際辨認）

- 產品頁：https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-bloomberg-1-3-month-t-bill-etf-bil
- 官方下載 NAV History（.xlsx）：https://www.ssga.com/library-content/products/fund-data/etfs/us/navhist-us-en-bil.xlsx
- 官方配息總覽/歷史配息 XLSX 入口：https://www.ssga.com/us/en/intermediary/resources/documents/etf-dividend-distributions
- 產品頁列 BIL 基金成立 2007-05-25、交易所 NYSE Arca、配息頻率 monthly；**不等於在本次真的打開 2007–2026 每日 NAV 原始 XLSX**。
- 本次網站文字工具按下「Most Recent NAV / NAV History」已解析上述指定 XLSX URL，但無法解析 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` 內容；嘗試隔離執行環境下載亦回傳 download failed，故不計入原始檔成功擷取。沒有把 HTML 節錄、頁面 NAV 現值當作 Excel 工作表資料。

## 2. 2017-11-30 官方企業行動獨立來源

美國 SEC 存檔的 **2017-11-28** SAI 補充文件：https://www.sec.gov/Archives/edgar/data/1064642/000119312517353499/d481888d497.htm ，確認 BIL 預定於 **2017-11-30** reverse split，並因此變更當日 creation-unit settlement 至 T+1。

**注意：** SEC 文件確認反分割事件日期與交割安排，但該特定補充文件**沒有寫出 1-for-2 比率**；先前研究有發行人公告的外部記錄，正式 NAV 比對若需分割比率，必須另行使用具明確比率的原始發行人文件/當日可核對原件。不能只憑這份 SEC 文件證明 1-for-2 或證明 NAV Excel 已依某一方法調整。

## 3. 下次單一檔案驗收（若安全地取得原始 Excel）

- 不公開原始 State Street workbook 到 GitHub。只記本機原始 bytes SHA-256、實際來源、檔案取得 UTC（只能在真正取得時填值），並以只讀檢查內容。
- 驗證 BIL ticker 與 worksheet、欄名/單位、日期範圍、2007-05-30 是否存在、日期唯一/排序、缺值與異常數值。
- 特別檢查 **2017-11-29、2017-11-30、2017-12-01** 附近 NAV/股數/總資產一致性；即使呈現約 2 倍跳變，也不得據此直接推論當時價格或現金持有期總報酬，需查明資料供應者調整制度。
- 官方配息 XLSX 是**另一份不同檔案**；沒有原始檔前，不宣稱已有 2007 以來完整股息及日期紀錄。
- State Street 網站可讀取/下載，**不等於已授權法人商用機器建模/長期儲存/再分發**，此項仍 HOLD。

## 4. 本輪結論

`BIL_OFFICIAL_NAV_DOWNLOAD_LINK=VERIFIED`
`BIL_NAV_XLSX_BYTES_IN_THIS_RUNTIME=FALSE`
`BIL_NAV_ROWS_INSPECTED=0`
`BIL_NAV_SHA256=null`
`BIL_2017_11_30_SPLIT_DATE_SEC_DOCUMENT=VERIFIED`
`BIL_REVERSE_SPLIT_RATIO_CONFIRMED_FROM_THIS_SEC_DOC=FALSE`
`BIL_FULL_DIVIDEND_HISTORY=UNVERIFIED`
`BIL_TRADABLE_RETURN_READY=FALSE`
`R1_GATE0=BLOCKED`
`NO_TRADING`

**Next single actual blocker:** 在任何可用且已授權的瀏覽器取得上面確認過的 BIL NAV XLSX 原檔，並讓本任務能唯讀檢查其內容；在檔案尚不存在於可讀的工作區時，禁止反覆寫計畫或誤稱已驗收。不得要求重複上傳已實際驗證的 SPY 原檔。
