# 視界 SIGNAL V0.4.4｜優質來源擴充、技術試運行與權利防線

這是對 **既有 V0.4.3 專案根目錄** 的覆蓋更新包，不包含已經蒐集的 `data/live_items.json`、`data/intelligence.json` 等個人／歷史資料。

## 本次新增與限制

- **EIA Today in Energy**：美國能源資訊署，官方能源／電力與商品資訊；僅發布有來源標示的標題、日期、連結，先驗證 GitHub 真實連線。
- **NASA News**：美國 NASA 公開訊息 RSS，涵蓋航太、工程等（不是純工程新聞）；同樣只發表描述性元資料，避免使用圖片、標誌或全文。
- **日本銀行 BOJ、歐洲央行 ECB**：僅測技術連線與 RSS 可解析數量，暫不把標題寫入公開情報，先完成商業／再利用授權審查。
- **臺灣證交所 TWSE**：其官方 RSS 條款明確寫明僅供閱讀，本次**不自動探測或公開 RSS 內容**；日後另評估官方 OpenAPI 的獨立授權。

**這不是 5 家新增正式新聞來源：只有 EIA／NASA 兩家進入受控試運行。** 若 GitHub 被 403 擋住仍會顯示失敗，並保留既有 Fed／BEA／arXiv 內容；不繞過存取限制。

## 更新順序

1. GitHub Desktop → `Fetch origin` → 如有 `Pull origin` 先同步。
2. 將 ZIP 解壓縮**內部的檔案與資料夾**放進 Repository 根目錄，覆蓋同名檔。不要把 ZIP 整個資料夾放入，也不要覆蓋／刪除 `.git` 或已累積的 `data/live_items.json`。
3. Summary：`Expand official SIGNAL sources with V0.4.4 rights gates` → `Commit to main` → `Push origin`。
4. GitHub → Actions → `SIGNAL V0.4.4 official source expansion + Pages` → `Run workflow`（`main`）。
5. 查看工作摘要的「V0.4.4 優質來源擴充（授權分流）」及 `collect-build` 的 `successful_sources/source_count`；打開網站「證據檢核」頁下方的新來源表。

**注意：** Actions 成功只代表程式執行成功。此次仍需看 EIA/NASA 是否顯示 reachable_parsed / 成功連線，不能將 403 當成已通過來源驗證。

## 驗收條件

- 舊的 4 條來源結果與歷史資料不被新來源連線失敗所清除。
- EIA/NASA 如果成功，才在網站 `新發現` 頁看到其標題；若未成功，網站展示明確錯誤／更新時間。
- BOJ/ECB/TWSE 的內容不得進入公開的 `live_items.json` 或 AI 初篩。
- V0.4.3 的來源盲區診斷仍為**資料輸入覆蓋**，全球重大事件遺漏率仍是 `null`，AI 不能捏造沒有蒐集到的事件。
- 只保存來源描述性資訊，沒有採集付費新聞全文、圖片或個人資料。

## 來源依據（2026-11-05）

- EIA RSS： https://www.eia.gov/tools/rssfeeds/ ；公開領域條件： https://www.eia.gov/TODAYINENERGY/about.php
- NASA RSS： https://www.nasa.gov/rss-feeds/ ；媒體使用： https://www.nasa.gov/nasa-brand-center/images-and-media/
- BOJ RSS： https://www.boj.or.jp/en/tips.htm ；著作權與商用限制： https://www.boj.or.jp/en/about/copyright.htm
- ECB RSS： https://www.ecb.europa.eu/home/html/rss.en.html
- TWSE RSS： https://www.twse.com.tw/zh/terms/rss.html （官方明示僅供閱讀）

下一步 V0.4.5：針對新來源的實測成效、可用性／來源健康、盲區與數據授權逐項驗收；再引入政治、企業、台灣／日本／巴西具有合法存取介面的新聞或政府資料。不要假設官方來源等於獨立觀點。
