# SIGNAL K4.11｜12 月 WASDE 公告前端到端預演與正式結果備援路徑

**編製：2026-11-17。這是事前準備，不是 2026-12-10 的結果。**

## 本次檢查發現、且已修補的必要缺口

舊 K4.10 `prospective_scorecard.py` 只在「**官方結果**」與「**12 月公告前市場共識**」兩者同時齊全時顯示 V0 絕對誤差。如果 12/10 官方結果已公布、但沒有取得可稽核的公告前共識，原程式會繼續輸出 `WAITING_FOR_DECEMBER_PRE_RELEASE_CONSENSUS_AND_USDA_OUTCOME`，雖不會造假，但造成**官方已公布仍無法評分**的實質缺陷。

已新增**不改動任何凍結預測**的官方專用結果管線 `research_core/k4/wasde_official_outcome_capture.py`：

- 固定 K4.10 V0 **1758 million bushels**，先重新重算事前原始 `2026-12-10-forward-baseline-forecast.json` 的 SHA-256 並核對既有評分契約。絕不改寫舊 JSON。
- ESMIS USDA 官方 `WASDE` 文字報告，預期 2026 年 12 月 `wasde1226.txt`，只在 **2026-12-10T17:00:00Z 之後**才允許對外發送請求。**這是預期路徑，不是已發布之網址；必須在官方發布後確認實際可用**。
- 驗證官方網域、HTTPS、回應來源 URL、實際取得開始及完成 UTC，原始 byte 長度與 SHA-256。
- 只解析 **U.S. Feed Grain and Corn Supply and Use** 頁的 **CORN** 段、**Million Bushels** 單位、**2026/27 Proj.** 欄、2026 年 12 月 Nov／Dec 欄位；前期 Nov 位置必須仍為 1758。拒絕把世界玉米庫存（百萬公噸）、FEED GRAINS 行或 2025/26 當成 2026/27 美國玉米期末庫存。
- 成功後生成**互相匹配、以 SHA 命名**的三份輸出：`*_official_raw.txt`、`*_capture_receipt.json`、`*_v0_score.json`，各檔以獨占模式建立，避免重複執行覆寫先前版本。
- **即使市場共識仍然缺失**，也能取得單次描述性 `v0_absolute_error_mbu=abs(官方期末庫存 - 1758)`，而 `market_consensus_mbu=null`、`consensus_abs_error_mbu=null`，維持 `alpha_verified=false`、`trade_eligible=false`。

## 真實已發布來源的預演

對 USDA 已於 2026-11-10 公告的官方文字原件 `https://esmis.nal.usda.gov/sites/default/release-files/796142/wasde1126.txt`，GitHub Actions [run #44034187733](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/44034187733) 當場下載**122,379 bytes**，直接以新解析器的 11 月模式驗證 `2026/27 CORN Ending Stocks: Oct 1849, Nov 1758`，**成功**。這是真實 11 月官方原件的格式測試，**不能**當成 12 月未公布結果。一次性網路測試完成後，已從日常 PR CI 刪除，避免日後網路不穩影響正常測試。

純離線 K4.11 有明確標記為 synthetic 的 12 月格式 fixture，測試官方單獨評分、正確年度／月份／單位、預期週次、假來源、公告前禁止下載、原始 byte 保存、重複檔案不可覆寫等情境。

## 12/11 正式驗收的順序

1. **先確認** USDA 官網 `https://usda.azureedge.us/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report` 的 2026-12-10 正式版確已發布、該次 WASDE 文字原件的實際下載 URL。2026 年 12 月 ESMIS 網址需先驗證；若官方改用不同正式網址，嚴禁冒用 11 月舊版；可於研究分支按實際網址修改**來源 allowlist**、新測試、重新跑 CI，不能繞過來源驗證。
2. 使用 K4 PR #22 的研究分支、在官方實際發布時間之後執行：

```bash
python -B -m research_core.k4.wasde_official_outcome_capture \
  --output-dir k411-official-staging
```

3. 若成功，核對三份 output 及 `trade_eligible=false`。以 byte-exact 方式把真正的原始檔、取得回執與官方 V0 評分**另外新增**到 PR #22 的 `research_core/k4/evidence/wasde/2026-12/`；不得修改已凍結原始 V0 或 K4.10 空白事前 evidence。只有提交成功、GitHub CI 成功才能宣稱封存完成。
4. **再核對**是否有真正公告前保存、可稽核的 12 月 analyst consensus。如果有，另行執行 K4.10 `prospective_scorecard.py` 的 V0 vs consensus 比較；沒有就保留 consensus null，不影響官方 V0 誤差。
5. 最後更新 PR #24 的研究卡片，固定引用新的 evidence commit 並再次驗證，維持 `NO_TRADING`。
6. 如果來源 404／格式差異／GitHub 無權限：明確 `BLOCKED`，保留所有已有證據，不填官方值，不等待下個月；可以在來源恢復後對**同一事件**再次取得正確月份的正式原件。

### 已知無法在 11/17 事先保證的因素

USDA 尚未公布 12 月原始報告，因此無法保證未來該次 URL 和欄位完全一致；GitHub Actions 成功不代表排程 Agent 未來必定具備 GitHub 寫入權限、或來源不會暫時 404。這些都以 **BLOCKED／人工審核或當日重試**處理，不猜測。

**K4.11 Gate：OFFICIAL_NOVEMBER_REAL_LAYOUT_VERIFIED、DECEMBER_PARSER_SYNTHETIC_TESTS_PASS、DECEMBER_SOURCE_PENDING、DECEMBER_V0_FROZEN、NO_TRADING。**
