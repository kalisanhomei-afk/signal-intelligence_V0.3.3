# SIGNAL K4.5｜事前預測／市場共識封存 MVP

**Decision: RESEARCH-ONLY. Historical event 2026-11-10 is BLOCKED; no ex-ante forecast can be reconstructed from its outcome. No trades.**

## 研究問題
在官方 WASDE 期末庫存公布前，SIGNAL 能否使用當時真正可取得的供需／NASS 資料，獨立預測美國玉米期末庫存，並在控制市場公告前共識的前提下，對公告 surprise 的方向或幅度提供增量資訊？

本階段不再從單一事件中搜索最佳公告後進場秒數／持有時間。K4.4 在一事件中做了 20 個高度相關的情境；正報酬情境不是策略勝率，也無真實 receipt、方向模型和 fill。

## K4.5 驗收契約
`ex_ante_gate.py` 的固定輸入為 `signal-k45-ex-ante-registration-v1`。必須登記：
- 官方**預定**發布 UTC；注意預定發布時間不是獨立驗證的實際可得時間。
- SIGNAL 預測數值（百萬蒲式耳）、方法版本、模型輸入截止時間及輸入 manifest SHA-256。
- 預測原始檔 SHA-256、創建 UTC、獨立不可竄改封存 UTC。
- 同一目標和行銷年度的市場共識數值、來源／方法、原始 SHA-256、獨立公告前封存 UTC。
- 事先凍結的規則 `compare_frozen_forecast_to_frozen_consensus_before_official_outcome`，且 `frozen_before_release=true`。

**Fail closed:** 任何非 UTC Z 時間、公告後材料、預測早於其輸入、封存早於預測、無效 SHA、額外塞入官方結果、缺少共識或預測時，拒絕或 BLOCKED。即使全部欄位填妥，也只達 `REVIEW_CANDIDATE_NOT_PIT_CERTIFIED`，不自動授予 PIT 認證或交易資格。真正的原始內容、時間可信來源及彼此獨立性仍由獨立審查確認。

2026-11-10 的公開歷史案例保留全部事前預測／共識欄位 null；切勿將事後得知的 USDA 1758 或公開回顧的共識值填成當時已封存的預測。本範例行銷年度鎖定 2026/27；未來新作年需正式版本化 target，不可直接換掉目標卻沿用本案。

## 可重現的離線執行
```bash
python -m unittest research_core.k4.tests.test_ex_ante_gate -v
python -m research_core.k4.ex_ante_gate --case research_core/k4/cases/2026-11-10-ex-ante-registration.json --output local-private-k45
```
預期：`BLOCKED_NO_EX_ANTE_EVIDENCE`; trade_eligible=false。不呼叫 API、不使用 Databento key、不收費。

## 下一個真正可被驗收的事件：先封存，再觀察
1. **公告前**固定預測模型、供需輸入版本、forecast JSON 與 SHA；同時記錄 consensus 原始快照、來源及 capture UTC，建立獨立封存。
2. **公告後**另存官方首版原始報告、下載完成 UTC、報告 SHA，確認實際 data available-at；不得回填當期結果到 forecast。
3. 僅在兩套公告前封存都獨立通過後，計算模型與共識各自誤差及方向；比較 forecast-vs-consensus 是否優於共識單獨基準。
4. 單一事件只能作 pipeline smoke test；跨事件樣本充足、時間版本一致、包含失敗樣本與成本後才考慮升級投資研究。零假說是模型沒有超越共識的增量價值。

## 近期取捨
- 優先補可獨立封存的**發布前市場共識**與**SIGNAL 預測**；這是目前唯一真正阻塞的證據門檻。
- K3.8 forward NASS 擷取提供作物狀態上游資料，**不能代替**月度 WASDE 事前庫存預測或當時共識。
- 不新增 Databento 付費下載，不公開任何原始行情，不下單，不合併本 K4 研究到 main。

**轉正條件：** 所有 evidence 的獨立捕獲與時間審查通過、確有事前凍結的預測、可比較的市場共識、多事件樣本及完整風險成本驗證；任一欠缺一律維持 NO-GO。
