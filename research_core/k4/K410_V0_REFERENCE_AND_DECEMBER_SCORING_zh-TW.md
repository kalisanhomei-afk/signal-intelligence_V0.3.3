# SIGNAL K4.10｜公告前凍結的玉米期末庫存預測評分關卡

**狀態（2026-11-17）：九年 V0 持平基準完成；12 月 10 日 USDA 真實結果與 12 月公告前市場共識尚未可取得／封存。程式驗收 PASS，不代表 V1 或交易優勢通過。**

## 研究問題與固定比較方式

**目標：** 美國玉米 2026/27 行銷年度期末庫存（百萬蒲式耳），官方報告預定 2026-12-10 17:00 UTC（台灣 12/11 01:00）。

- 已於 2026-11-17 GitHub 公開保留的 **V0 持平基準**：`USDA_PREVIOUS_WASDE_PERSISTENCE_V0=1758` 百萬蒲式耳；此數值就是 11 月 USDA 官方數字，不是新創的 AI 趨勢預測。
- 其原始 forecast JSON SHA-256 已固定為 `54d4d7597d457c64307e9a2e1e5670cd5f1ecd52676180eded2a19a8ebcaca48`，見 `cases/2026-12-10-forward-baseline-forecast.json`。評分程式會重算 forecast JSON **實際位元組**的 SHA，任何事後改寫都拒絕評分。
- 評分規則在公告前固定為 **絕對誤差（MAE 的單事件組成）**：`V0_error=abs(12月USDA - 1758)`；`consensus_error=abs(12月USDA - 12月公告前市場共識)`。數值愈小愈好；比較 `V0_error - consensus_error`，正值代表市場共識在**該事件**較準，負值代表 V0 在**該事件**較準。
- 任何獨立 V1 模型必須有自己公告前封存的版本、輸入截止 UTC、預測和原始 SHA；本期 **V1 不存在**、不能將事後假設情境或「無預測」當成零誤差。

## 現有九年持平基準（2017/18 至 2025/26）

程式直接由已提交的 USDA 官方 11→12 月 as-reported 當期庫存修訂標籤重新計算，每年持平預測是該年 11 月值：

| 指標 | 真實九年樣本結果 |
|---|---:|
| 樣本 | 9 年 |
| MAE 平均絕對誤差 | **57.78** 百萬蒲式耳 |
| 絕對誤差中位數 | **45.00** 百萬蒲式耳 |
| RMSE 均方根誤差 | **85.89** 百萬蒲式耳 |
| 最大單年絕對誤差 | **200.00** 百萬蒲式耳 |
| 實際變動相對持平預估的平均偏差（actual − forecast） | **−31.11** 百萬蒲式耳 |
| 未修訂／上修／下修 | 3／2／4 年 |

**重要**：九年的官方答案可當作計算 V0 表現的描述性標籤，**不可**視為已認證的歷史 FGIS 事前特徵；n=9 無法當成未來 90%/95% 預測區間，也不足以證明方向預測或交易優勢。

## 公告後的失敗即停關卡

`research_core/k4/prospective_scorecard.py` 讀取兩份**事前約定的獨立檔案**：
- `cases/2026-12-10-v0-scoring-contract.json`：固定事件、標的、模型、forecast SHA、計分規則；已於公告前 GitHub 提交。
- `cases/2026-12-10-v0-scoring-evidence-empty.json`：12 月共識與官方結果全為 `null`，刻意留空，不臆測。

預期執行：

```bash
python -B -m research_core.k4.prospective_scorecard \
  --output k4-review/k410_frozen_december_scorecard.json
```

現階段輸出 `WAITING_FOR_DECEMBER_PRE_RELEASE_CONSENSUS_AND_USDA_OUTCOME`；`v0_abs_error_mbu=null`、`consensus_abs_error_mbu=null`、`model_v1_abs_error_mbu=null`、`trade_eligible=false`。

未來若找到市場共識，必須保存**明確屬於 2026 年 12 月 WASDE** 的來源、原始 SHA、發布與實際捕獲 UTC 且 **均早於官方發布時間**；USDA 12 月數值必須於公告後自官方來源擷取原始位元組及捕獲 UTC。只有兩方資料齊全且時間先後相容，程式才可輸出 **單事件描述性誤差比較**。程式檢查欄位或 SHA 形式，**不代表自行確認外部來源的首次發布時間或 SHA 所對應內容真實**；另需人工／獨立稽核。

> **禁止**把 November 2026 的共識 1,846、或其他事後新聞對 November 報告的分析，移填為 December 2026 市場共識。也禁止因單次 V0 比共識好／壞即宣稱 SIGNAL 具備 alpha。

## 下一個決策點與既有自動追蹤

- USDA 官方公布日可於 https://usda.azureedge.us/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report 核對。
- 已存在 12 月共識追蹤及 FGIS WA_GR101 前瞻封存任務；本次**沒有重建或重複**這兩項。
- 已加上一次性 **2026-12-11 台灣時間約 09:00**「SIGNAL 12月 WASDE 預測驗收」任務：公告後查證 USDA、事前共識證據、執行 K4.10 評分，缺證據就維持 BLOCKED；但自動任務本身**不保證能取得新原始位元組或成功提交 GitHub**。
- 若 12 月沒有可稽核的公告前共識：**V0 對 USDA 的單次誤差可在有正式官方證據後描述，V0 對市場共識的比較不得放行**。
- 一次完成流程驗收後停止在這個事件上優化誤差閾值／解讀規則；長期必須持續累積多個不同事件的 **事前凍結預測 vs 事前共識 vs USDA 官方結果**，才有機會進行樣本外研究、納入風險與交易成本。

**關卡：K4.10_SCORING_PIPELINE_PASS / DECEMBER_CONSENSUS_PENDING / DECEMBER_OUTCOME_NOT_RELEASED / INDEPENDENT_PIT_UNVERIFIED / V1_ABSTAIN / TRADE_ELIGIBLE=false。**

K4.10 原始程式與測試位於 PR #22 `codex/k4-corn-hypothesis-mvp` 研究分支，**不合併 main**、不使用 Databento、不交易。
