# SIGNAL R1g｜免費資料來源的權利驗證與最小資料契約（2026-11-22）

**交付性質：CODE_DONE / LOCAL_OFFLINE_UNIT_TEST_PASS (12/12) / DATA_RIGHTS_UNVERIFIED / GATE0_BLOCKED。**
延續既有 Draft PR #29（stacked：#28 → #27 → #26）。不購買資料、不下載 French 原始數值、不使用 Tiingo API、不執行 M0/M1/M2 回測、不發布、不合併 main。

## 1. 唯讀官方來源稽核：Kenneth French（不要把免費下載誤當商業授權）

- [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)：官方網站確實列出 Fama/French 3 Factors 的月度 TXT、CSV、Details 與 Historical Archives；其 July cut 資料於之後八月發布。這證明「來源與歷史版本入口存在」，**不是**每個檔案都通過時點或位元組驗證。
- [官方方法變動](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)：2025-01 起 CRSP FIZ 改為 CIZ；月度股息再投入方式由月末投入改為除息日逐日複利，數值與前舊版不具完全相同的生成方法。不能把 2026 最新完整歷史回填成 2024 之前逐月原本可得的答案。
- [Fama/French 因子定義](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_factors.html)：Rm-Rf 為 CRSP 美國股票市場組合相對 1-month T-bill rate，非 SPY/BIL 的真實成交報酬；RF 至 2024-05 來自 Ibbotson，2024-06 起改取 ICE BofA US 1-Month Treasury Bill Index。這些供應資料可能有衍生商用限制。
- [CRSP 原始資料服務](https://indexes.morningstar.com/research-data-products) 為專業資料服務，不能由 French 網頁「公開可讀」推導出本公司的商業儲存/AI/重散布授權。
- **本輪找不到可據以批准**本公司在私有 AI/量化分析系統永久存取、批次重算、再發布或第三方 AI 處理的明確 Kenneth French 商業使用授權條款。正確標示：\`PUBLICLY_LISTED\`, \`COMMERCIAL_MODEL_RIGHTS_UNVERIFIED\`, \`RAW_DATA_NOT_ACQUIRED\`, \`PIT_NOT_VERIFIED\`, \`DATASET_NOT_ADMITTED\`。這不是宣稱任何學術或個人閱讀一定違法；正式使用前應詢問提供者的書面範圍。

## 2. 不依賴特定供應商的最小單筆資料契約

**檔案**
- \`scripts/validate_capital_flow_receipts.py\`：Python stdlib，純離線的單筆 JSON 結構／前視風險護欄。**沒有 API、行情抓取、持久資料庫、模型／交易指令。**
- \`tests/test_validate_capital_flow_receipts.py\`：12 個合成情境，涵蓋錯誤資料型別、遺漏欄位、UTC、截點晚於發布、未知發布時刻、證據 SHA 不吻合、結果欄誤用、版權與准入隔離。
- \`docs/research/global_capital_flow_r1g_synthetic_observation.json\`：完全虛構的月度觀察值示例，不引用任何公開或受限金融數值。

**固定欄位**：\`schema\`, \`source_id\`, \`dataset_id\`, \`observation_month\` (YYYY-MM), \`role\` (feature/outcome), \`value\` (有限數值), \`unit\`, \`source_release_utc\`, \`retrieved_utc\`, \`decision_cutoff_utc\`, \`vintage_id\`, \`raw_sha256\`, \`evidence_type\`, \`rights_status\`, \`pit_status\`, \`accepted_for_model\`。

- UTC 時刻為包含秒數的 ISO8601 + \`Z\`；不能以 observation month 推測實際官方發布時點。決策截點為 R0 固定「每月最後一個美股交易日 16:00 America/New_York」對應的**事先正確換算 UTC 值**。此護欄**不自行產生交易日曆／DST**；需由獨立時間日曆驗證。
- \`feature\` 的發布時間必須**嚴格早於** \`decision_cutoff_utc\`；未知或等於截點／晚於截點均提出警告；單筆 JSON 只是結構有效不等於 PIT 通過。
- \`outcome\` 是事後已實現的結果值，通常於預測截點之後才確定；不得混成 \`feature\`。
- \`evidence_type\` 只能是 \`SYNTHETIC\`、\`PUBLIC_METADATA_ONLY\`、\`EXTERNAL_RAW_REPORTED\` 或 \`LOCAL_RAW_VERIFIED\`，避免把外部 Agent 回報的雜湊說成本執行環境重算證據；當且僅當有實際原始 bytes 證據時可填相應 hash，單一 hash 本身**不是**不變歷史時點證明。
- \`rights_status\` 是 \`NOT_APPLICABLE/UNVERIFIED/RESTRICTED/CLEARED\`；\`pit_status\` 是 \`NOT_VERIFIED/PENDING/VERIFIED\`。沒有權利與來源版本證據時不自行變更。
- **安全刻意設計**：不論 JSON 型別檢查是否成功，\`source_gate\` 永遠輸出 \`BLOCKED\`，\`model_admitted\` 永遠 \`false\`；輸入的 \`accepted_for_model\` 必須為 \`false\`。這是前置證據契約檢查器，不是 Gate 0 授權系統。就算有人自稱 \`PIT_VERIFIED\` 與 \`CLEARED\`，也不能被這個小程式放行。
- 用 \`python -m unittest discover -s tests -p 'test_validate_capital_flow_receipts.py' -v\` 可測試；用 \`python scripts/validate_capital_flow_receipts.py docs/research/global_capital_flow_r1g_synthetic_observation.json\` 只會輸出結構檢查結果，不會進行金融資料處理。

## 3. 實際驗收、證據及未完成事項

- **本機驗證**：於獨立 Python 工作目錄重建與 GitHub 檔案位元組一致的來源；12/12 stdlib \`unittest\` PASS，範例 JSON CLI 退出碼 0、\`structure_valid=true\`、\`source_gate=BLOCKED\`、\`model_admitted=false\`。程式與測試的本機 \`git hash-object\` 結果分別為 \`1385b0f9264004bf907883b723738670b4c93a4c\`、\`89d3a9793c90c42ad0cc6aaafa87fe41273f91f0\`；合成示例 \`220014c41d5786ae94014702164e086a43a15d35\`。
- **不是**在 GitHub Actions 執行上述定向驗證；既有 GitHub \`Project continuity\` 成功只證明該 workflow，而非這支測試，不能將兩者混淆；本輪無重跑 R1c 已通過測試。
- **尚未完成**：Kenneth French 企業使用權、歷史 July cuts 實際原始檔 byte/修訂驗證、完整 2007+ PIT、可交易 SPY/BIL total-return、R2 模型及紙上交易。
- **下一個工作**：先取得公開資料的**特定資料源授權明文或供應商書面答覆**；對無授權者維持元資料研究與合成測試，不下載入商業研究系統。若正式研究目標不需可交易 ETF 回測，應另提出明確的探索性研究 proposal，不能暗中更改已凍結 R0 Gate 0。
- 成本新增：US$0。Tiingo/Twelve Data/EODHD 尚未被選定；繼續執行 R1f「品質合格後才比價」政策。任何實際交易／主線合併／付費使用需另核准。
