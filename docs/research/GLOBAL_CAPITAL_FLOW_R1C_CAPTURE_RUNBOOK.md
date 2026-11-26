# R1c 官方原始檔最小擷取工具（實驗性，離線測試通過）

- 範圍：人工指定的 **單一** \`www.federalreserve.gov\` H.6 HTML 或 \`home.treasury.gov\`／\`www.treasury.gov\`／\`ticdata.treasury.gov\` TIC ZIP 官方直連 URL，HTTPS 且同機構重新導向。無站內搜尋、無批次抓取、無排程或交易連結。
- 指令（必須在**允許對外 HTTPS 的環境**操作）：\`python scripts/capture_official_research.py "https://www.federalreserve.gov/releases/h6/20200827/" --kind html --out research_raw\`
- ZIP 同理：先在 https://home.treasury.gov/archives-of-tic-monthly-data-releases 找到**實際** ZIP 連結後，將其貼入第一個參數並改 \`--kind zip\`。**不要猜想 URL**。
- 本輪的最小驗收只需 H.6 2020-08-27 (HTML) 與一個已查證官方 TIC 發布檔 (ZIP) 各一份。原始檔及收據放在本地 \`research_raw\`，不要將原始資料或敏感內容提交到 GitHub。
- 輸出原檔的 SHA-256、HTTP headers、最終 URL、擷取 UTC 起訖、ZIP 檔名與大小 metadata，並保存獨立 JSON 收據；有大小限制、不覆寫、拒絕非政府網域和 ZIP traversal 成員，完全不解壓縮。
- **重要：這是現在下載到的 HTTP 回應 bytes 的 hash，並非證明該檔自歷史發布日時完全未更改。** 對應的歷史發佈版與發布時刻仍須另外驗證；收據強制 \`accepted_for_model=false\`、\`contemporaneous_original_file_certified=false\`、\`license_status=UNVERIFIED\`。
- 不使用 FRED／ALFRED 作模型資料；授權仍需另審。此工具**不處理**模型、交易、股票含息總報酬、資產配置。
- 目前 ChatGPT 容器外部官方域名 DNS 解析失敗，且直接下載工具失敗，因此 \`R1c OFFICIAL_NETWORK_CAPTURE=BLOCKED\`，不要虛構原始檔 SHA。
- 離線驗收（沒有網路、無 Actions）：\`python -m unittest discover -s tests -p 'test_capture_official_research.py' -v\`；本機 Python 執行 8/8 通過（2026-11-22）。
- Fed 官方已於 2026-11-12 公告舊 DDP 預格式資料 2027-03-31 及 DDP 頁面 2027-07-01 將退役；本工具擷取官方 H.6 舊發布 HTML（非每次重新下載的最新 DDP 全歷史），避免錯把修訂版變成各期舊版。來源：https://www.federalreserve.gov/datadownload/Choose.aspx?rel=H6
- 下一個決策：原始取得環境可用後，先用 2 個官方檔案取得收據，再由獨立審查驗證發布時點、內容、授權及必要 180 個月的樣本覆蓋。Go/No-Go Gate 0 仍 BLOCKED。
