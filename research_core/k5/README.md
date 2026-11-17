# SIGNAL K5 — 天然氣庫存與需求假說（研究階段）

**H-NG-001 / 2026-11-17**。與玉米 K4 PR #22 完全分離，不修改 `main` 或 K4 資料。

**K5.0 已完成：** 以 EIA 2026-11-13 正式發布的 11/06 Lower 48 庫存變動 **+61 Bcf**，提前凍結下一次 11/19 的 V0；不修改任何原先預測檔。

**K5.1 已完成（2026-11-17）：** 已真正取得 EIA 官方 JSON 原始 **7,197 bytes**，SHA-256 `6eb6c699b789d7130d3f50dbe5681e835b57bc25dd118380398169dda63fe252`，實際捕獲 UTC `2026-11-17T02:55:16.841819Z`。原始 BOM 和全部位元組及 receipt 已提交 [K5 EIA 來源證據資料夾](evidence/eia)，CI 逐位元組驗證。這份**補充來源證據**不改寫原先 V0 檔案中的 null，亦非獨立 PIT 認證。詳見 [K5.1 來源稽核](K51_EIA_ORIGINAL_SOURCE_CAPTURE_AUDIT_zh-TW.md)。

**下一個日期：** 2026-11-19 15:30 UTC **預定** EIA 公告（台灣 11/19 23:30）；只有確認實際公布後才核對當週官方結果。真正的 11/19 數值與市場共識目前 **NULL**。

**可重現：**
```bash
python -B -m unittest discover -s research_core/k5/tests -p 'test_*.py' -v
python -B -m research_core.k5.ng_baseline \
  --case research_core/k5/cases/2026-11-19-eia-prior-week-input.json \
  --output k5-local/recomputed_v0.json
```

請讀 [K5.0 假說與資料可信度驗收](K50_NATURAL_GAS_RESEARCH_GATE_zh-TW.md) 了解候選方向、反證規則和停止條件。此 PR 保持 **Draft / V1_ABSTAIN / NO_TRADING / NO_MAIN_MERGE**。
