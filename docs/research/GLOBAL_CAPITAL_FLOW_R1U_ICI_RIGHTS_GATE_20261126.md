# SIGNAL R1u — ICI 資料權利與商用研究准入閘門（2026-11-26）

## 查核結果（ICI 官網直接發布的政策）
**實質新發現：ICI 週報可公開閱讀，並不表示授權 SIGNAL 進行定期機器下載、完整表格鏡像、再發布、商業模型訓練或對客戶提供資料。**

官方網址（公開政策，不需登入）：
- ICI Copyright and Linking Policies: https://www.ici.org/copyright-and-linking-policies
- ICI Copyright and Permissions Form: https://www.ici.org/permissions
- ICI statistical research subscription program: https://www.ici.org/ici-subscriptions
- ICI public release entry: https://www.ici.org/research/stats/combined_flows

ICI 政策指出網站內容受著作權保護，一般網頁材料的個人本機保存、合理短摘及連結有明確界限；不得直接推論可自行鏡像其資料或整批重製、再利用。其授權申請頁另明確區分**統計研究底層資料**（會員及訂閱者才可取得、不可任意轉刊）與公開研究摘要；統計訂閱選項涵蓋每週基金／ETF／MMF 系列，且針對客戶再發布另需符合訂閱及授權條件。官方沒有在這幾個頁面明確授與 SIGNAL 內部商用機器化建模、持續抓取、永久備份或對外再利用的權利。

**本報告不是法律意見**。法律上單一事實、少數統計數字可能有不同待遇，但不能把「公開可見」等同「所有後續使用均已獲得契約授權」。目前使用者未批准購買 ICI 訂閱或對外洽詢，故不購買、不寄信、不代填申請。

## 三種使用分級（研究保護條件）

| 使用情境 | 建議狀態 | 原因 |
|---|---|---|
| 人工唯讀查看 ICI 公開摘要、記錄研究發現和官方連結 | `DESCRIPTIVE_RESEARCH_ONLY` | 僅少量獨立摘要；仍需遵守引用與使用條款 |
| 內部排程大量下載 ICI 完整表格、整理可重用的時序資料庫、訓練商業模型 | `HOLD_RIGHTS_REQUIRED` | 不宜將公開網頁當作無限制免費資料來源 |
| 對客戶提供 ICI 原始表格、下載 API、付費投資研究產品內重製數據 | `NO_GO_WITHOUT_WRITTEN_TERMS` | 再發布權及特定商業用途須正式確認 |

## 對 SIGNAL R1u 假說的立即影響

- 已記錄的 `H-ICI-WRAPPER-01` 四週方向檢查，僅當作**公開資料的少量研究摘要**，不擴展成受限制的完整數據產品。
- 不建立 ICI 大規模自動擷取任務、原始 HTML 備份庫或週更完整模型資料表。**暫停 ICI 商用模型准入**；原有 `1/4` 描述性觀測不受影響，仍為 `PIT_UNVERIFIED`。
- 如果要進一步發展為可對外銷售的 SIGNAL 投資研究產品，先確認授權條款：內部機器化分析、歷史版本保留、商業模型輸入、訂閱終止後稽核保留、衍生結果展示與是否可轉授權。此時未寄出詢問信，遵守使用者逐封事先核准規範。
- **更低成本替代策略：** 正式投資建模優先繼續評估 Fed/Treasury 等來源的個別授權和 PIT 可用性，以及既有 Twelve Data 資料授權回信；ICI 暫作解釋性外部觀察，不新增軟體整合。
- 本次未取得新的原始 ICI HTTP bytes、未重跑既有測試、不宣稱任何 ICI 預測結果或 alpha。

## Gate 結論

`ICI_PUBLIC_REPORT_VIEWABLE=TRUE`
`ICI_INTERNAL_COMMERCIAL_MACHINE_USE_AUTHORIZED=UNVERIFIED`
`ICI_FULL_DATA_ARCHIVING_AUTHORIZED=UNVERIFIED`
`ICI_DOWNSTREAM_REDISTRIBUTION_AUTHORIZED=UNVERIFIED`
`R1U_DESCRIPTIVE_ONLY=TRUE`
`R1_GATE0=BLOCKED`
`R2_NOT_STARTED`
`NO_TRADING`

下一步：等待已排定的 K4/K5 官方實際公布驗收；R1 另待既有 Twelve Data 回覆或確認真正符合授權、原始來源及資料時間版本的市場價格代理。在此之前不擴充 ICI 機器化採集。
