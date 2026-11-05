# SIGNAL V0.4.1 — 證據缺口與可追溯性（Evidence Gap Audit）

## 本階段已實作
- 每次資料蒐集、規則初篩後產出 `data/evidence_audit.json`，與每則候選的 URL、source_id、publisher_id、標題一一比對。
- 保守的證據狀態：所有候選固定為 `M0 / 未查證`，獨立佐證數為 0；原文未讀取，不得升級為「已查證」。
- 區分 Fed／BEA 第一手發布與 arXiv 預印本；每種來源提供對應的查核問題。
- 新增「證據檢核」頁面；維持原本鎏金大理石配色、原始資料及「情報初篩」頁面。
- 公開發佈白名單僅增列 `data/evidence_audit.json`，不得夾帶文章全文或人工審查私人備註。
- 新增 `scripts/test_v041.py`，對來源、權限、同源重複與未經證實的「已查證」狀態採用失敗即停止（fail closed）機制。

## 重要界線
1. 此次是**證據缺口治理工具**，不是已經查核全文、跨來源驗證或完成 AI 的情報分析。
2. V0.4.1 **不新增 RSS，也不啟動付費 AI**，不提供可信度或全球重要性數字，以避免誤導。
3. 目前僅 3 家獨立發布機構，全球新聞、政治、產業、能源與地域覆蓋尚不完整。
4. **最終的情報可信度評價需要 M1 原始內文核對、M2 實質獨立來源佐證，以及人工審閱。**

## 更新到現有 GitHub Repository
1. 下載 `SIGNAL_V0.4.1_覆蓋更新包.zip`，解壓後將裡面的**內容**放入現有 Repository 根目錄，**不要多放一層資料夾**。
2. 切勿刪除 `.git`；不要覆蓋或刪除已在 Repository 中累積的 `data/live_items.json` 和 `data/intelligence.json`。本補丁內不含這兩個檔案。
3. GitHub Desktop `Summary`: `Add V0.4.1 evidence gap and provenance audit` → `Commit to main` → `Push origin`。若有自動更新 Commit，先 Fetch、Pull；出現衝突不要選擇強制覆蓋。
4. 到 GitHub Actions 選擇 **SIGNAL V0.4.1 evidence gaps + cautious triage + Pages**，Run workflow，branch = main。工作流程檔名仍為 `.github/workflows/signal-live-v034.yml`，避免產生平行部署流程。
5. 驗收：`collect-build` 與 `deploy` 都成功；網站「情報初篩」仍正常，左側新增「證據檢核」。可查看原始連結、證據狀態及待查問題。所有候選仍顯示「未查證」。
6. GitHub Pages 更新未必立即顯示，可重新整理並查看 `data/evidence_audit.json`。

## 完成標準
- 已建立且可追溯的證據缺口資料，不得把新聞標題視為研究或政策結論。
- 重複的 arXiv RSS 訊號不構成獨立佐證。
- 任何不屬於 Fed、BEA 或 arXiv 核准連結的元資料不得進入證據清單。
- 單次 GitHub 成功仍不足以證明長期資料品質；之後仍需連續更新、外部重大事件遺漏評估。

## 下一階段建議（尚未實作）
- V0.4.2：授權允許的原始摘要／官方數值核對及審核記錄；多來源真正的獨立性判定，進行人工作業抽樣。
- V0.4.3：採用明確測試集檢查重要性判斷、召回率／漏報率、地域與主題偏差；後續才輸出每日情報。
