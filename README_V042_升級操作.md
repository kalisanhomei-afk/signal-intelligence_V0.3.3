# 視界 SIGNAL V0.4.2｜作者摘要元資料與證據鏈更新

## 與 V0.4.1 的差別
V0.4.1 只取得候選的 M0「標題、時間、來源 URL」。V0.4.2 **新增一次正式 arXiv API 元資料查詢**，核對論文 ID 與標題一致才將研究候選升到 M0A：「已取得作者摘要元資料」。這**不是**已獲同儕審查、學術成果獨立驗證或全文閱讀。Fed／BEA 暫不抓取原文，其候選維持 M0。

官方政策：arXiv API 允許使用 CC0 描述性元資料（含 abstract），並要求傳統 API／RSS **不超過每 3 秒 1 次請求**，故此版本每次只呼叫一個、最多八篇 ID 的批次，並在 RSS 採集後延後 4 秒。來源政策：https://info.arxiv.org/help/api/tou.html

## 本次已實作（目前已完成**離線**測試）
- `scripts/evidence_v042.py`：一次 arXiv 官方 Atom API 批次查詢；網址、ID、標題驗證；失敗時不虛構 M0A；相同指紋使用歷史快取。
- `scripts/test_v042.py`：檢驗身分對應、官方端點、網址偽裝防護、API 失敗降級、公開網站不可偽造已查證。
- `scripts/build_public_site.py`：網站只能發布 M0／M0A 元資料；拒絕錯誤來源、偽造「已驗證」的結果；不發布全文或私密設定。
- 網頁「證據檢核」：顯示 M0／M0A 數量；符合 M0A 的論文可展開**作者原文英文摘要**，並保留明確未查證提示。
- GitHub Actions：自動生成 `data/evidence_enriched.json`，保存版本並部署；Job summary 另外顯示 M0／M0A、API 錯誤數。

## 更新步驟（與前幾版相同）
1. 在 GitHub Desktop 先按 **Fetch origin → Pull origin**（若有），確保同步自動資料更新 Commit；有衝突先停止。
2. 下載「V0.4.2 覆蓋更新包 ZIP」並解壓縮，**僅把裡面的檔案**覆蓋到現有 `signal-intelligence_V0.3.3` Repository 根目錄。請勿將 ZIP 本身、外層資料夾、個人檔案傳上去，也不要刪除 `.git`。
3. **不要覆蓋 `data/live_items.json`、`data/intelligence.json`、`data/evidence_audit.json`**。本更新包不含這些資料，也不含 `data/evidence_enriched.json`；後者由 GitHub 自行建立。
4. GitHub Desktop 的 Summary 輸入：`Add V0.4.2 official arXiv abstract evidence`；按 **Commit to main → Push origin**。若遠端又更新，先 Fetch／Pull 再 Push，不要 Force Push。
5. GitHub → **Actions** → **SIGNAL V0.4.2 primary metadata evidence + Pages** → **Run workflow** → main → Run workflow。
6. 確認 `collect-build`、`deploy` 綠燈；查看 Job summary 後段 **「V0.4.2 官方作者摘要元資料補充」** 是否有 M0A 及 API 錯誤。
7. 打開網站「證據檢核」，應看到 `M0` 或 `M0A`。**如果本次 M0A=0，不代表程式成功取得摘要**，請看 API 問題。不要以 Actions 綠燈當作內容驗證。

## 驗收邊界
- API 可用與 ID/標題相符：部分 arXiv 候選可升 M0A；未取得 M0A 的維持 M0。
- 發布機構仍僅 Fed、BEA、arXiv **三家**；沒有重大政治／產業全面覆蓋。
- 獨立佐證數與「已驗證主張」固定 0；重要性、個人投資預測均未啟用。
- 未能在此離線環境對你的 GitHub 執行實際 arXiv API 連線驗收；需由你觸發上述 Actions。

## 後續版本
V0.4.3 才開始：從有許可的多主體來源建立**獨立佐證／反證**，針對重大事件進行抽樣人工審核，並在來源分布足夠的情況下做重要性／遺漏率測試。不能單靠 arXiv 作者摘要就升 M2。
