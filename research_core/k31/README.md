# 視界 SIGNAL K3.1｜官方領先指標接入與時間回放

**狀態：工程離線原型通過；預測優勢未建立。** 不使用付費 API，不自動發布，不能當作期貨操作訊號。

## 這次真正完成的事情

1. 接入 **4 個真實 USDA NASS Crop Progress 公告版次（2026/07/06、08/10、09/08、10/05）**，人工從官方 TXT 表格的美國玉米「18 States」作物狀況列擷取五級百分比，並記錄原始網址、週末日期與保守可用時間代理值。
2. 以 K3 已有的 **2026/27 美國玉米 WASDE 7～10 月官方估計版本**作為比較對象，將每一個「預測起點」的 NASS 資料鎖定在該日期以前。
3. 實作一個**未訓練的方向假說**：若「兩次選定的 NASS 公告」的 Good＋Excellent 百分比下降，僅提出「下次 WASDE 單產估計可能下修」的假說；不是回歸模型，也不預測漲跌幅度或期貨價格。
4. 對下一次 USDA **單產預估值的修訂方向**做歷史回放，回傳命中、不命中、缺資料棄權以及詳細原因，另產生 HTML/JSON。
5. 34 項自動驗證，含禁止未來資料、來源範圍、五級百分比總和、摘錄行數字一致、資料版本、回測標記及禁止交易訊號。

## 已知結果與誠實界線

- 2026/07/10 起點：在本次選擇的 NASS 資料中只有 07/06 一期，因此 **棄權**，不假造趨勢。
- 2026/08/12 起點：已可看到 08/10 與 07/06，G+E 從 67% 降到 61%；提出「下次 USDA 單產預估下修」；09/11 WASDE 確實從 180.7 下修至 178.5（吻合）。
- 2026/09/11 起點：已可看到 09/08 與 08/10，G+E 從 61% 降到 56%；同樣預期下修；10/09 WASDE 從 178.5 **上修至 181.2（方向錯誤）**。
- 可評估 2 次，命中 1 次。**不能宣稱模型有預測優勢、勝過 K3 基準，或可據此交易。**
- 2026/10/09 起點可看到 10/05 NASS 的 54%，但 K3 固定資料未含 11/10 WASDE，故這筆**不計入評分**。截至 2026/11/11，11/10 官方版已發布；需在後續正式新增來源與 QA，不應假裝仍待公布。

### 特別注意：評估指標不同

K3 的 persistence 基準預測的是**下一期的期末庫存估計（百萬蒲式耳）**；K3.1 的領先方向假說對象是**下一期單產估計的修訂方向（蒲式耳／英畝）**。
兩者不能直接比 MAE 或宣稱 K3.1 改善了 K3。K3.1 另保存同一單產目標的 persistence MAE 作為日後具體數值模型的基準，尚未可比。

## 瀏覽報告

直接用 Chrome 開啟：`research_core/k31/out/k31_review.html`。

結構化資料：`research_core/k31/out/k31_leading_indicator_study.json`。

## 安裝位置（不可覆蓋舊版）

Repository `signal-evidence-rebuild` 分支：

```text
signal-intelligence_V0.3.3/
└── research_core/
    ├── k2/              （原有）
    ├── k3/              （原有）
    ├── contracts.py     （原有）
    └── k31/             ← **只新增本資料夾**
        ├── engine.py
        ├── demo.py
        ├── fixtures/
        ├── tests/
        ├── out/
        └── 執行K31離線驗收.bat
```

### Windows 執行

已安裝 Python 3.10+ 時，在 Repository 根目錄：

```powershell
py -3 -m unittest discover -s research_core/k31/tests -v
py -3 -m research_core.k31.demo
```

也可雙擊 `research_core/k31/執行K31離線驗收.bat`。

## 來源與時間注意事項

- USDA NASS 每週 Crop Progress 原始 TXT：
  - 07/06：<https://esmis.nal.usda.gov/sites/default/release-files/795970/prog2726.txt>
  - 08/10：<https://esmis.nal.usda.gov/sites/default/release-files/796012/prog3226.txt>
  - 09/08：<https://esmis.nal.usda.gov/sites/default/release-files/796051/prog3626.txt>
  - 10/05：<https://esmis.nal.usda.gov/sites/default/release-files/796095/prog4026.txt>
- WASDE 來源沿用 K3 四個官方公告版本資料，保留 K3 對原始 TXT 的人工轉錄聲明。
- **兩組資料都是回溯建立的「當時公開可取得」版本，不代表 SIGNAL 在 7～10 月就曾實際保存。**
- NASS 的報告在日期旁未保留可機讀且逐版認證的精確時分秒，因此程式使用「報告發布次日 12:00 UTC」作為**保守可用時間代理值**，不是官方發布時分秒；這個選擇在本樣本均早於下一次 WASDE 起點。
- 18 州作物狀況摘要不等於 100% 全美面積普查；也不等於官方單產預測。選定的 4 期 NASS 間有省略其他週的版本，因此信號差值**不是逐週變化率**。

## K3.2 的驗收門檻

1. 正確匯入多個市場年度的歷史 WASDE／NASS 版本，擴大到至少 24 個跨年度可比較的預測起點。
2. 在對照目標可得以前先凍結規則；只用該時點已公布資料，並做 walk-forward 驗證。
3. 比較同一**單產**目標的數值預測與 persistence，及其他季節性基準；不可把方向命中率與 MAE 混比。
4. 檢驗季節性、地理權重、上游氣候／面積、官方發布修訂與市場預期；再引入可依法取得的期貨行情，分開評估投資價值。

**禁止升級解讀：** 源數值可信度 ≠ 因果識別 ≠ 預測優勢 ≠ 交易獲利。
