# 視界 SIGNAL｜研究進度與共同假說驗收總覽 V1

> **2026-11-17 核對快照**。這是只讀的研究品質與進度儀表板；**不是**正式上線網站、即時資料服務、已驗證的交易策略或投資建議。

## 已交付

- `status_manifest.json`：唯一的正式主線／GitHub Draft PR／K3.8 治理／六層架構／已知 CI／既有事件檢查快照。
- `cards/H-CORN-001.json`、`cards/H-NG-001.json`：**共同資料格式**。所有官方數值、來源原始 SHA、預測 V0、共識、結果、誤差、Go／No-Go 均能在同一結構呈現。
- `validate.py`：來源日期、單位、事前與事後順序、官方結果空值、風險狀態、防止把日曆數值冒充共識；明確區分「工程通過」與「投資策略通過」。
- `build_review.py`：不依賴外部 JavaScript、網路服務或額外套件，產生可以用瀏覽器開啟的單一 `review.html`。
- `tests/test_portfolio.py`：資料契約、誤差時序、未知數不得變成零、禁止合併狀態誤報、HTML 字元跳脫及交易資格防呆。

## 直接操作（Windows / macOS / Linux，Python 3.11+）

在 GitHub Repository 根目錄：

```bash
python -B -m unittest discover -s research_overview/tests -p 'test_*.py' -v
python -B -m research_overview.build_review --output research_overview/out/review.html
```

之後使用 Chrome、Edge、Safari 開啟 `research_overview/out/review.html` 即可檢視。

研究 PR 的 GitHub Actions 會上傳 **`signal-research-overview-review`** HTML Artifact，可下載到本機打開；不會部署 GitHub Pages、修改正式站、提交原始行情或設置定時抓取。

## 架構與來源事實（以 GitHub 即時查核所得的 11/17 快照為準）

1. `main` 的 README 標示 SIGNAL V0.3.3，根 `index.html` 標題標示 V0.5.2a。這是**版本標示不一致**，不代表哪一個已部署線上；本期未驗證 GitHub Pages 實際版本。
2. **PR #20 只合併 K3.8 手動 Workflow 註冊**；`main` 上的 `.github/workflows/signal-k38-manual-capture.yml` 是 *fail-closed* stub，不含可在 `main` 執行的正式採集程式。
3. **PR #19、#22、#23 仍是開放的 Draft 研究 PR**，目標分支都是 `codex/k37-orchestration`。它們的 K3.8、玉米、天然氣研究程式**未合併至 main**。
4. K4 玉米 12 月期末庫存事前 V0＝**1,758 百萬蒲式耳**；研究原始 forecast JSON SHA-256 `54d4d7597d457c64307e9a2e1e5670cd5f1ecd52676180eded2a19a8ebcaca48`。
5. K5 EIA 11/19 週庫存淨變動事前 V0＝**+61 Bcf**；原始 forecast Git Blob SHA-1 `bacc82f549fb3bba74142139d89bec94e386d88e`；MetaTrader 日曆觀測 **+69 Bcf 不等同合格市場共識**。
6. K4 和 K5 的工程測試分別已有已核對成功的工作流紀錄，但**不代表**多期、樣本外、可交易預測優勢。請注意紀錄的日期；本系統不自動重新取得最新 PR／CI 狀態。

## 統一假說卡片契約與更新政策

每張卡片固定具有：

| 區塊 | 用途 | 公告前要求 |
|---|---|---|
| `forecast` | 事前 V0 數值、單位、來源分支、原件雜湊 | 必須凍結，**不得事後改寫** |
| `evidence` | 前期實際 raw 來源及 SHA-256、時間版本限制 | 不將 SHA 當作獨立首次發布時間認證 |
| `market_consensus` | 具名、市場事前預估及證據 | 未驗證則 `value=null` |
| `indicative_external_forecasts` | 日曆／單機構參考預測 | 只能標 `INDICATIVE_ONLY` |
| `official_outcome` | 事件官方結果、原始內容 SHA、捕獲 UTC | 公告前必須全部 `null` |
| `score` | V0／共識的絕對誤差、樣本外證據 | 結果未核對前不得填入誤差 |
| `decision` | 研究、投資及交易資格 | 目前一律投資 `NO_GO`、`trade_eligible=false` |

**事件公布後也不可自動讓卡片變成「成功」：** 首先在 **來源研究 PR** 完成官方原始位元組、SHA、真正捕獲 UTC 及週別／年度驗證；再在此小型整合 PR 更新卡片的 `official_outcome`、由程式驗算 `score`，並將 `evidence_link` 指向已保存的真正 GitHub 原件。這份整合快照**本身不會下載或重新核對各研究 PR 的原始 bytes**；其來源聲明不能取代 K4／K5 的底層來源驗證。

只有確認真正有經日期、方法、原始 bytes 或其他可信存證支持的市場事前共識，才可提升 `market_consensus.status`。單次 V0 誤差比較不會讓 `out_of_sample_edge_verified` 變成 true，也不會開放交易。

## 下一次工作和停止條件

- 11/19 與 11/20：K5 首次天然氣公告前／公告後真實事件驗收。
- 11/24 起：K4 FGIS 每週新原件封存；12/11：K4 WASDE 12 月官方結果驗收。
- 事件來源未通過時間／raw 位元組驗證時，卡片維持 `NOT_RELEASED` 或紀錄為 **BLOCKED**，絕不臆造官方數字。
- 事件完成後，回頭更新狀態快照及卡片**一次**，不做高頻監控／新的資料庫／前端重構；只在成果證明有必要時才導入正式網站。
- 此 PR 僅提供狀態整合的 **最小版本**，不碰 K4／K5 凍結預測、`main` 正式介面或自動交易。請維持 Draft，未取得授權不合併。

## 資料隔離

此處只保存**公開來源的檔名及雜湊**與研究數值，不鏡像第三方全文、不包含 API Key、帳戶、資產持倉、個人資訊或交易紀錄。CI 的預覽 HTML 亦僅含公開研究快照。
