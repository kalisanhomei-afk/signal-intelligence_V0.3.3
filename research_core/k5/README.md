# SIGNAL K5 — 天然氣庫存與需求假說（研究階段）

**H-NG-001 / 2026-11-17**。與玉米 K4 PR #22 完全分離，不修改 `main` 或 K4 資料。

**已完成：** 以 EIA 2026-11-13 正式發布的 11/06 Lower 48 天然氣地下庫存變動 +61 Bcf 作為 11/19 下一次報告的事前固定 V0 預測基準；官方數據刊載於 [EIA WNGSR](https://www.eia.gov/naturalgas/storage/) 及 [WNGSR JSON](https://ir.eia.gov/ngs/wngsr.json)。這不是獨立天氣模型，且未能取得官方原始 JSON 位元組，因此不提供猜測的 SHA。

**下一個日期：** 2026-11-19 15:30 UTC **預定** EIA 公告（台灣 11/19 23:30）；只有確認實際公布後才核對當週官方結果。真正的 11/19 數值與市場共識目前 **NULL**。

**可重現：**
```bash
python -B -m unittest discover -s research_core/k5/tests -p 'test_*.py' -v
python -B -m research_core.k5.ng_baseline \
  --case research_core/k5/cases/2026-11-19-eia-prior-week-input.json \
  --output k5-local/recomputed_v0.json
```

請讀 [K5.0 假說與資料可信度驗收](K50_NATURAL_GAS_RESEARCH_GATE_zh-TW.md) 了解候選方向、反證規則和停止條件。此 PR 保持 **Draft / V1_ABSTAIN / NO_TRADING / NO_MAIN_MERGE**。
