# SIGNAL V0.4.5｜歐盟政策／MIT 研究資訊來源小規模試運行

本更新沿用 V0.4.4 黑金鎏金介面，不增加管理頁面，也不引入 AI API 費用。新增兩條**可溯源標題元資料**候選：European Commission Presscorner、MIT News Research；僅顯示來源、標題、時間與原文連結。不得視為獨立報導或科學驗證。

## 使用／權利

- EU Commission：歐盟擁有之 EC 網站內容原則 CC BY 4.0，標示 European Commission 並連結原文；第三方內容例外。
- MIT News：官方有 RSS 並列出轉載條件。SIGNAL 僅存標題／連結，明確標示 MIT News，不重刊文章、圖片或全文。未來若做商業服務，先逐項重新確認授權。
- Reuters、AP、BBC、FT、Nikkei **未自動採集**，因媒體資料使用／商業授權尚未確認。開發中不准當作自動批次擷取來源。
- 上述來源的新增不代表全球政治、科技、產業已具備充分覆蓋，更不等於任何主張已有獨立查證。

## 安裝（覆蓋更新，不重建 Repo）

1. GitHub Desktop：`Fetch origin → Pull origin`（若可用）。
2. 只將 ZIP **內的檔案與目錄** 複製到既有 Repository 根目錄，不要再多包一層，也不要刪除 `.git`。
3. 本更新**不含 `data/live_items.json`，不會覆蓋線上累積資料**。
4. Summary：`Pilot EU policy and MIT research metadata in V0.4.5` → Commit to main → Push origin。
5. GitHub → Actions → `SIGNAL V0.4.5 European policy and research source pilot + Pages` → `Run workflow` (`main`)。
6. 看執行摘要中的 `SIGNAL V0.4.5` 區塊、新增來源的成功數、source coverage 警告與站內「新發現」。

## 驗收（沒有完成實際部署前不得宣稱成功）

- `Check offline acceptance tests` + `collect-build` + `deploy` 成功。
- 8 條候選中，原六條仍能保持原有更新或保留失敗時歷史資料；歐盟／MIT 的資料若無法讀取，明確報錯，不偽造內容。
- 每則新增項目有原始連結，沒有付費文章全文、圖片與 AI 編寫之「事實摘要」。
- Reuters/AP/BBC/FT/Nikkei 不會出現在自動收集白名單或公開資料中。
- `source_quality_v043` 只顯示來源視角，不會宣稱世界新聞覆蓋率或主張驗證率。

## 重要聲明

本機環境無法直接連結 RSS 端點；新來源的實際可讀性尚需 GitHub Actions 執行驗證。MIT 新聞室是機構自有新聞，不構成第三方查證；EC 是官方政策發布，不構成獨立媒體。若未來營利、公開商業產品或 AI 大規模使用這些內容，需要重新審核權利。

## 官方依據

- EC 法律聲明 https://commission.europa.eu/legal-notice_en
- EC 官方新聞 https://ec.europa.eu/commission/presscorner/home/en
- MIT News RSS https://news.mit.edu/rss
- MIT News Terms https://news.mit.edu/terms-of-use
- BBC metadata 規則 https://www.bbc.com/pages/terms-of-use
