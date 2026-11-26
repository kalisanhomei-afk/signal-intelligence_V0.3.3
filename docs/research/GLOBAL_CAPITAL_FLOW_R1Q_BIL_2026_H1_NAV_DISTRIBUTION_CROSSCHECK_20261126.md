# SIGNAL R1q｜BIL 2026 H1 公開 NAV＋配息與發行人績效獨立交叉核對

**2026-11-26，研究級唯讀實驗；不是合規的可交易 ETF 回測，也不是當時可用 PIT 模型輸入。**

## 真正取得並重算的原始證據

- 用戶上傳的 State Street BIL NAV 工作簿 `navhist-us-en-bil (1).xlsx`：原始 SHA-256 `da8a46b06b1d3d224f59e3c321f77dd0a5ad131011156a53807f755162f61656`，先前已完成 4,908 NAV 日期驗收，本次以 `artifact_tool` 唯讀讀取必要欄位。
- 用戶上傳配息工作簿 `spdr-etf-historical-distributions (1).xlsx`：原始 SHA-256 `0008b3cc16472d89944e1cf36dced2ec5df5430e07c8731fcf1e38f3dd67774c`；因整簿 `artifact_tool` 匯入超時，本次改以 Python 標準庫 ZIP/XML 在記憶體中唯讀掃描 BIL 對應列，不輸出原始來源行情。
- **不重新抓已經驗收的原檔**，也沒有第三方行情資料、交易 API 或帳戶資料。這兩個原始檔是用戶上傳，非本次直接接收官方 HTTP response，發布版本及商用授權仍未確認。

## 已完成且可複算的三個期間

採用**研究假設**：在每個 ex-date 將當日每股分配額，以該日基金 NAV 即時再投入原基金，忽略手續費、稅與不能在 NAV 即時成交的現實限制；再投資單位數連乘。

`NAV_TR(a,b) = NAV_b / NAV_a × ∏_{ex∈(a,b]} (1 + distribution_ex / NAV_ex) - 1`

`distribution_ex` 取 `DIVIDEND ($) + SHORT TERM CAPITAL GAIN ($) + LONG TERM CAPITAL GAIN ($)` 三類；空白資本利得欄暫以 0 作**此公式的示範性數值假設**，不代表法律上已證實無其他分配類別。正式版本需對照發行人績效方法及配息再投入日。

| 期間 | NAV 起點 | NAV 終點 | 分配事件 | 本次數值研究算得 | 發行人公開 Fund Before Tax / NAV |
|---|---:|---:|---:|---:|---:|
| 2026-01-01 起至 2026-06-30（基準 NAV 2025-12-31） | 91.386292 | 91.645611 | 5，分配合計 1.319806 USD/share | **+1.740396737%** | **YTD +1.74%** |
| 2026-Q2（基準 NAV 2026-03-31） | 91.643421 | 91.645611 | 3 | **+0.883358768%** | **QTD +0.88%** |
| 2026-06 單月（基準 NAV 2026-05-29） | 91.648290 | 91.645611 | 1 | **+0.291644721%** | **1 Month +0.29%** |

發行人**獨立比對來源**：https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-bloomberg-1-3-month-t-bill-etf-bil ，網站 `Fund Performance / Fund Before Tax / NAV`，**as of 2026-06-30**，公告顯示 **1 Month 0.29%、QTD 0.88%、YTD 1.74%**。本次三項取百分比兩位小數皆相符；不能因此宣稱所有歷史年度/拆股期間已通過或再投資日假設與發行人內部方法完全一致。

## 重要辨識：NAV 本身不是已實現總報酬

若錯誤地只比較 H1 起/末 NAV，得 **+0.283761376%**，與發行人公布的 **+1.74%** 顯著不同；把現金配息再投入之後，研究值才匹配官方 NAV 報酬的顯示精度。這證明「只用 NAV 價格變動」會漏掉重要收益。

**此測試不能支持以下結論**：
- ETF 投資者能在 ex-date 以 NAV 即時成交／零手續費；
- 任一月份 16:00 ET 凍結模型當時已具備此資料版本；
- 2017 BIL 反分割已在完整報酬歷史中修正；
- 2008-03-03 發行人 payout-date 異常已解決；
- 此資料已獲准企業商用、永久保存或傳到外部 AI。
- 有正式市場 alpha、回測績效、K4/K5 預測成果。

## 停止重做與下一步
- **`BIL_H1_2026_NAV_TOTAL_RETURN_PROXY_3_OF_3_MATCH_ISSUER_TO_2DP=TRUE`**；
- `BIL_2017_SPLIT_FULL_HISTORY_UNVALIDATED=TRUE`，`CORP_ACTION_RIGHTS_UNVERIFIED=TRUE`，`SPY_BIL_EXECUTABLE_RETURN_NOT_AVAILABLE=TRUE`，`FORMAL_GATE0=BLOCKED`。
- 不必再下載 State Street 的 NAV 或配息 XLSX，也不必再查同一 H1 對照。
- 下一個最小不同期間的驗證：在不改變 R0 計畫下，僅核對包含 **2017-11-30** 反分割的短窗口 NAV 每股單位調整，以及 2008-03-03 配息錯置之正式原始來源。如正式交易研究需要，應另處理授權及成交價格（NAV不能取代）。
