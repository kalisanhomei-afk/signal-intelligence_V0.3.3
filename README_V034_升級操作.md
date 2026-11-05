# 視界 SIGNAL V0.3.4｜正式元資料自動更新（GitHub 部署升級）

> 這是 **V0.3.3 的增量更新**，不是新的 GitHub Repository。保留既有 repo `signal-intelligence_V0.3.3`，不要重新建立。

## 這次已新增什麼

- 首批 **4 個已檢視再利用條款的 RSS 通道，來自 3 個發布機構**：美國聯準會（Fed）、美國經濟分析局（BEA）、arXiv（AI／Robotics 兩條）。
- GitHub Actions **台灣時間每天約 08:27／20:27** 排程；可隨時手動執行。
- GitHub 自動建立簡短的來源狀態報表，記錄成功、失敗、取得筆數；失敗保留舊資料，顯示過期。
- 只儲存標題、來源、網址、時間等**描述性元資料**；歷史保留最長 45 日，上限 420 則；不抓文章全文、不擷取付費牆。
- 維持既有 SIGNAL 鎏金／米白／墨黑介面；點「**新發現**」看自動標題，點「來源管理」看正式更新狀態。

## 一、更新現有 GitHub 專案（Windows）

1. 解壓縮 `視界_SIGNAL_V0.3.4_覆蓋更新包.zip`，**進入解壓縮資料夾裡面**。
2. GitHub Desktop → `Repository` → `Show in Explorer`，打開目前 `signal-intelligence_V0.3.3` 的**根目錄**。
3. 將更新包內的 `.github`、`scripts`、`data`、`docs` 等檔案／資料夾與 `index.html`、`index.template.html`、`source-console.html`、`README_V034_升級操作.md` 全部複製到根目錄；詢問重複檔案時按**覆蓋**。
4. **不要**將整個更新包資料夾再放進 Repo，避免發生上次多一層資料夾導致 Actions 無法辨識的問題。也不要刪除 `.git`。
5. 回 GitHub Desktop，左側應出現新增／變更的檔案，Summary 輸入 `Upgrade SIGNAL to V0.3.4 live metadata`，點 `Commit to main`，再點 `Push origin`。

### 應檢查的檔案位置

GitHub 網站 `Code` 根目錄應直接顯示：

```
.github/workflows/signal-live-v034.yml
scripts/collect_v034.py
scripts/v034_summary.py
scripts/test_v034.py
data/v034_sources.json
 data/live_items.json  ← 上方空白僅為顯示縮排；實際在 data 內
index.html
source-console.html
```

## 二、在 GitHub 執行第一次更新

1. 打開 GitHub Repository → **Actions**。
2. 左側點選 **`SIGNAL V0.3.4 live update and Pages`**（不要選舊的 V0.3.3 preflight）。
3. 右側 `Run workflow` → 分支選 `main` → 再按 `Run workflow`。
4. 點選本次執行紀錄，`collect-build` 和 `deploy` 都應為綠色。向下看 `SIGNAL V0.3.4 官方／研究元資料更新`，確認**成功通道數及取得標題數**。
5. 打開原本 SIGNAL 網站，不需新建網址；進入 **「新發現」** 查看更新，或打開 `/source-console.html` 查看當次採集狀態。

如果「新發現」仍為 0：先查看 `collect-build` 報告；單一網站回 HTTP 403 不代表主程式失敗。若四個全部失敗，系統應保留歷史資料並明確顯示 `unavailable`，不會生成假新聞。

如果 `git push` 顯示 permission denied：檢查 Repo → Settings → Actions → General → Workflow permissions 是否允許工作流程適當的 `Read and write permissions`。此 Workflow 明確要求 `contents: write`，用來**只回寫 `data/live_items.json`**。不需建立 Personal Access Token。

如果找不到新 Workflow：GitHub 上 `.github/workflows/signal-live-v034.yml` 應位於 Repo 根目錄；若檔案被放到 `SIGNAL_V0.3.4/` 子目錄就不會被辨識。

## 三、自動排程與維護

- 排程執行時間為 **UTC 00:27／12:27**，台灣時間 **08:27／20:27**；GitHub 排程會因平台負載延遲或少數排程跳過，**不是保證準點**。
- 免費／公開 Repo 若長期沒有活動，GitHub 可能停用排程；需留意 Actions 執行紀錄。
- 此次沒有使用 API Key、密碼、信用卡資料、個人投資記錄；Repo 目前為公開，**不要上傳私人資訊**。
- 專案原本的「今日情報」仍是**日期固定的示範編輯摘要**；只有「新發現」接入自動標題。AI 分析、政治與產業多來源接入等在 V0.4 之後進行。
- 若將來重新部署新版，先保存 `data/live_items.json`，否則覆蓋空白版本會使此前 45 天的暫存歷史消失。

## 四、資料授權、判斷與風險邊界

- Fed：官方聲明可公開閱讀與 RSS 訂閱；官方網站「除另有標示外」為公有領域，若有第三方材料另外處理。證據：https://www.federalreserve.gov/disclaimer.htm 。
- BEA：官方網站內容原則上屬公有領域，另有標註例外。證據：https://www.bea.gov/help/faq/147 。
- arXiv：描述性元資料依 CC0 可儲存／轉換／分享，但論文全文的著作權另計；legacy API（含 RSS）**每三秒最多一個請求，同時最多一連線**。證據：https://info.arxiv.org/help/api/tou.html 。
- 來源連線成功 ≠ 新聞內容獨立查證 ≠ 重大事件優先級 ≠ 投資建議。
- BLS 與 NASA JPL 在先前 GitHub 試驗回傳 403；此次**不規避網站控制**，保留在候選來源名單，後續改走合規官方資料管道。

## 五、正式 V0.3.4 驗收標準

1. GitHub 手動執行成功，至少 **2 個不同發布機構**有實際資料（階段性門檻；非已達成聲明）。
2. `data/live_items.json` 存在、只含公開元資料，無付費文章全文或機密。
3. `source-console.html` 正確區分**V0.3.3 端點預檢**與 **V0.3.4 正式元資料更新**。
4. 連續 3 次執行，新增消息不重複、來源故障不會抹除歷史資料，45 天到期能清除。
5. 發生來源錯誤時保留真實狀態、不得填入虛構標題；未能達成上述條件，不能標記為已完成 V0.3.4 實際連線驗收。

開發狀態：程式與離線單元測試已完成；**尚未代替使用者部署本更新到 GitHub**，外部更新效果須由首次執行結果確認。
