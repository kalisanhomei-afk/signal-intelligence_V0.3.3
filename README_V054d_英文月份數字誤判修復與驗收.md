# 視界 SIGNAL V0.5.4d｜數字引用誤判最小修復

## 本次實際結果（取自使用者 2026-11-06 提供的最新 Artifact）

- `evidence.json`：官方頁面／作者摘要成功讀取 3/3；BEA 9 段、EIA 與 arXiv 有資料。
- `analysis.json`：AI 嘗試 1 次、成功草稿 0、失敗 1。
- 原因分類 `numeric_not_exactly_in_cited_excerpt`，拒絕的數字符號為 `9`。
- **無法由這份 Artifact 唯一確定 AI 將 `9` 用於何處**，因為程式為避免儲存未審閱生成文字，沒有保存被拒絕的完整草稿。`September` 翻成「9月」是合理的可能原因，而不是已證實的錯誤句。

## 修復範圍與安全邊界

**僅在單則 `key_facts.statement` 所引用的證據文字明確包含英文月份全名時**，把該陳述的「數字+月」轉為相同意義的中文月份文字。

例：證據 E1 有 `September`，模型寫 `9月逆差增加 $3.6 billion` → 儲存及驗證時規範化為 `九月逆差增加 $3.6 billion`。

該規範化不影響其他數字，包括金額、百分比、年份與日期（日期中的「日」）。沒有引用 `September` 的 `9月` 仍不能通過；`9 billion`、`2026`、`219` 等沒有證據的數字仍被拒絕。

這是**防止因為月份中英文書寫方式而誤拒的校驗修正**，不是放寬統計數字一致性；任何引用通過後仍只算「模型待人工審閱草稿」，不算事實查證完成。

## 檔案與部署步驟

更新包只有下列檔案，使用時解壓到原 Repository 根目錄，覆蓋同名檔案（不要把外層 ZIP 名稱當成新資料夾）：

- `scripts/evidence_analysis_v054.py`
- `scripts/test_v054d.py`（新增純離線測試）
- `.github/workflows/signal-v054-evidence-pilot.yml`
- `README_V054d_英文月份數字誤判修復與驗收.md`

GitHub Desktop：`Fetch origin` → 如有更新則 `Pull origin` → 覆蓋以上檔案 → Summary 填入：

`Fix cited English-month normalization in V0.5.4d numeric guard`

執行 `Commit to main` → `Push origin`。

GitHub Actions：開啟現有 **SIGNAL V0.5.4 official evidence + optional AI pilot (manual only)**，使用最新 `main`。

1. 先跑 `run_paid_ai=false`，確認 `test_v054d.py` 離線測試與來源擷取成功。
2. 再跑 `run_paid_ai=true`、`max_paid_calls=1`，只允許一筆付費 API 呼叫。
3. 在 **Summary** 核對 `AI calls / drafts / failures`，下載最新的 `signal-v054-source-excerpts-ai-manual-review` Artifact，提供 `analysis.json` 與 `pilot_review_v054.html`。

### 驗收判準

- `Source excerpt retrieval = 3/3`（三個指定來源都可取得至少部分摘錄）
- `AI calls = 1, drafts = 1, failures = 0`（**尚待實際驗證，不保證**）
- `verified claims = 0`（直到人類完成逐項查核，這個值必須維持 0）
- 假如 AI 再次失敗：保留 Artifact，**先看 `rejected_numeric_token`，不要盲目重跑多次**。這次修復只處理有來源證據的英文月份轉中文數字月份，無法保證涵蓋其他錯誤。

## 已做的免費測試

已使用原本 V0.5.4、V0.5.4b、V0.5.4c 與新增 V0.5.4d 的離線測試；所有模擬模型輸出皆不連線至 OpenAI，不計費。

## 後續技術建議

如果相同問題持續出現，不應再單靠 Prompt 試錯，而應將證據事實數字改由程式從來源資料抽取、構成 `facts_ledger`（資料表），由模型只選擇已登錄的事實 ID 並撰寫分析；數值由程式引用原始來源。這是下一個主要架構調整，不屬於此次最小修復範圍。
