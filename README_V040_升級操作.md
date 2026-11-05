# 視界 SIGNAL｜V0.4.0 情報初篩升級指引

## 版本定位

**V0.4.0 是正式來源元資料上的「情報初篩候選」試行版，不是完成的新聞查證、深度研究或投資預測。** 它保留 V0.3.4 自動採集及公開來源授權範圍，新增跨來源輪流抽樣、明確的證據限制及可選用的 AI 標題註記。

## 先做：無需 AI 金鑰的安全升級

1. 在已公開的 GitHub Desktop 專案 `signal-intelligence_V0.3.3`，點選 **Repository → Show in Explorer**。
2. 解開 `視界_SIGNAL_V0.4.0_覆蓋更新包.zip`，複製**包內的檔案與資料夾**到 Repository 根目錄；覆蓋同名檔。**不要再多包一層 `SIGNAL_V0.4.0`。不要刪除 `.git`。**
3. **不要替換**目前 Repository 裡已經由 GitHub Actions 維護的 `data/live_items.json`，否則歷史資料可能丟失。此覆蓋包沒有這個檔案。
4. 在 GitHub Desktop 填寫提交訊息 `Upgrade SIGNAL to V0.4.0 cautious intelligence triage`，點 **Commit to main → Push origin**。
5. 到 GitHub 網站 **Actions → SIGNAL V0.4.0 metadata + cautious triage + Pages → Run workflow → main → Run workflow**。
6. 工作流程須看到 `collect-build`、`deploy` 兩個工作都成功，再開啟 Pages 網站並切換左側 **「情報初篩」**。沒有 AI 金鑰時，正常顯示的是「規則初篩」，**不會偽裝 AI 輸出**。

> 舊版 V0.3.3 部署工作流程已改為退休提示，避免兩套 Actions 同時覆蓋同一個網站。V0.4.0 是新的唯一正式部署流程。

## 選擇性啟用 AI（會產生 API 使用費）

預設**關閉**，不需要 API 金鑰即可完成安全的初篩流程與網站驗收。要啟用：

1. 前往 OpenAI API 平台，建立具適當預算限制的 API Key（ChatGPT 訂閱與 API 分開計費）。
2. 在 GitHub Repository **Settings → Secrets and variables → Actions → Secrets → New repository secret**，名稱必須是 `OPENAI_API_KEY`，值填入 API 金鑰。
3. 同一頁切換 **Variables → New repository variable**，名稱為 `SIGNAL_AI_ENABLED`，值 `true`。
4. 如需指定模型，可額外設定 `SIGNAL_AI_MODEL`，預設是 `gpt-4.1-mini`（需該 API 帳戶支援）。
5. 重新手動執行 **SIGNAL V0.4.0 metadata + cautious triage + Pages**。
6. 在 `情報初篩` 看到「AI 標題註記」數量增加，並核對 `AI 版本 / 來源 / 原文 / 應查核`，再決定是否維持開啟。

**安全與費用**：單次執行最多嘗試 6 筆新註記，同一標題與規格版本會快取；預定每日兩次。重複手動執行、標題更動、模型更動或模型錯誤均可能產生額外用量；程式呼叫上限不是帳務上限，仍應在 API 平台設定支出控制。絕不在網頁、JSON 檔或提交紀錄貼上 API Key。

## 系統究竟會顯示什麼？

- 已部署、但未設 API 金鑰：候選來源、標題、時間、原文、規則產生的「優先檢視／一般候選」。不生成翻譯、原因或查證結論。
- 設了 API 金鑰：額外生成中文標題、**可能**關聯、應追查的證據、目前未知之處。所有輸出都標示「僅標題／非全文／非獨立查證」。
- 來源只有 Fed、BEA、arXiv 三家獨立發布機構，缺乏政治、產業、社會等資料；系統會提醒覆蓋不足，不會聲稱產生完整的全球「今日精選」。
- `今日情報` 和 `本週觀察` 目前仍是帶日期的人工編輯樣本；**不會把它們假冒為今日更新**。

## V0.4 驗收門檻（部分必須人工審查）

| 控制點 | 第一輪標準 | 目前情況 |
|---|---|---|
| 資料來源白名單 | 未核准來源不得導入 AI | 離線測試通過 |
| 原始追溯 | 每張候選卡有原文網址、發布單位與時間 | 程式測試通過 |
| 不可把標題當全文 | 無來源內文不得假稱已查證、同儕審查、量產 | 程式強制待審；AI 需人工抽驗 |
| 去重／多樣性 | 同機構多頻道合併計數；初篩最多 4 筆／機構 | 離線測試通過 |
| AI 成本 | 預設關閉，單次最多 6 筆新分析 | 離線測試通過 |
| 資料安全 | GitHub Pages 僅發佈白名單元資料與初篩 | 離線測試通過 |
| 真實線上驗收 | 手動執行 Actions，確認公開網站可顯示候選 | **尚待你部署** |
| AI 品質抽樣 | 人工驗看至少 30 則，記錄誤判與臆測 | **尚未進行** |

**下一個階段 V0.4.1**：擴充已核准的獨立來源、事件合併與跨來源證據鏈，才能談真正的「重要性排序」。目前不能為新聞打看似客觀的 90 分，也不能產生投資方向預測。
