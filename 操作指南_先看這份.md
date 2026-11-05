# 視界 SIGNAL V0.3.3｜實際部署與 RSS 連線驗證

## 這一版達成什麼

**一份可部署的 GitHub Pages 專案 + 真實 RSS/Atom 端點探測（由 GitHub Actions 執行）+ 黑金來源狀態儀表板。**

- 保留先前鎏金介面、11/05 靜態編輯樣本與事件時間軸。
- 實際連線測試（只測端點可讀、解析結果數、出錯原因、日期；**不抓全文、不儲存文章標題**）。
- GitHub Actions 會建立公開網站用的安全白名單資料夾 `_site/`，不上傳內部來源登記、開發文件及程式碼。
- 端點連線失敗依然顯示失敗，不假裝資料正在更新；本次只測探測，不授權新聞採集。
- GitHub Pages 以 GitHub Actions artifact 部署，避免 git push 資料造成觸發循環。
- 預設只有手動觸發才探測；排程先保持關閉，供核對機器人存取條款後啟用。

> **目前尚未在使用者 GitHub 帳號部署，也尚未由 GitHub runner 執行真實外網測試。** 本地 Python 執行環境的 DNS 不通。不可將「離線測試通過」寫成「來源已驗證」。

## 不會自動發生的事情

- 不會自動蒐集或刊登 Reuters、BBC、arXiv 等候選來源文章標題。
- 不會產生正式每日新聞，也不會執行 AI 重要性分析。
- 不會將「可連線」自動改為「權利審查通過」。
- 不能將這版視為自動新聞服務。

## 手把手：Windows + GitHub Desktop（建議）

1. 下載解壓縮此 ZIP，進入 `SIGNAL_V0.3.3` 資料夾。確定 `.github/workflows/signal-preflight-pages.yml` 仍在資料夾內（`.github` 是隱藏資料夾）。
2. 安裝 GitHub Desktop 並登入帳號。選 `File → Add local repository`，指向解壓縮後的 `SIGNAL_V0.3.3`。若提示不是 Git repository，選 `create a repository here`。
3. 在 GitHub Desktop 提交第一次 commit，然後選 `Publish repository`。正式發佈前先確認**沒有放入密碼、付費文章、交易紀錄**。若使用免費方案且要使用 Pages，建議先用不含私人資料的公開 repository；GitHub Pages 網址本身是公開可讀的。
4. 開啟 GitHub repository 網站，選 `Settings → Pages → Source = GitHub Actions`。
5. 選 `Actions → SIGNAL V0.3.3 preflight and Pages → Run workflow`。這一次才會真正從 GitHub runner 連線測試 10 條候選 RSS。
6. 工作完成後，進入 `Actions` 開啟該次執行，下載 `signal-live-probe-v033` 檢查具體結果。Pages 網址可在 workflow 的 Deploy 步驟或 Settings → Pages 找到。開啟 `.../source-console.html` 查看來源連線狀態。
7. **先保持兩次／日排程關閉**。待確認每個來源的自動讀取規定，再至 Repository → Settings → Secrets and variables → Actions → Variables 新增 `SIGNAL_ENABLE_PROBE_SCHEDULE=true` 啟動預檢排程。這只是端點探測，仍**沒有**啟動正式資訊蒐集。

> 若你想保持研究資料完全私密，不應把個人收藏或投資資料放入 GitHub Pages。GitHub 官方說明 Pages 站點可公開存取，即使 repository 為私人也不應把它當作私密網站。

## 本地測試（不需要網路）

```powershell
python scripts/test_pipeline.py
python scripts/test_governance.py
python scripts/test_v032.py
python scripts/test_v033.py
python scripts/build_public_site.py --output _site
python -m http.server 8000 --directory _site
```

開啟 `http://localhost:8000/`，來源管理頁為 `http://localhost:8000/source-console.html`。
本地顯示 `尚未實際連線` 是預期行為，**不是錯誤**。

## 本次驗收關卡

| 項目 | 本地狀態 | GitHub 實跑後狀態 |
|---|---|---|
| RSS / Atom 解析與排除外部 entity | 通過離線測試 | 仍需逐端點實測 |
| 來源權利防護（未核准不正式爬文） | 通過 | 不會自動解除 |
| 10 條候選／8 個發布機構 | 設定完成 | 不保證每個都能讀取 |
| GitHub Actions YAML 工作流 | 完成靜態檢查 | 需上傳才可啟動 |
| GitHub Pages 網站 | 本地可建構 | 需使用者 GitHub 帳號設定 |
| 連續三次正式蒐集成功 | 尚未達成 | 必須在權利核准後另行驗收 |

## 正式內容接入下一步（V0.3.4）

真實 probe 結果出來後，先從合法可供自動存取的資訊來源中選出至少四家不同機構啟用 `data/sources.json`；每條均必須記錄 `permission_evidence_url`、權利範圍、審核時間、`live_tested_at`。接著開啟停用的正式採集排程、驗證 3 次更新，再做 V0.4 AI 分類/內容可信度分析。
