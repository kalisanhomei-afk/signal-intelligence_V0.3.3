# K4.5｜2026-12-10 WASDE 事前基準預測與證據封存

**狀態：基準預測已提交／尚未具備獨立 PIT 完整驗收／市場共識待捕獲／非交易訊號。**

## 已凍結的事前基準

- 研究事件：USDA-WASDE-2026-12-10；公告**預定** 2026-12-10T17:00:00Z（美東 12:00、台灣 2026-12-11 01:00）。
- 目標：美國玉米 2026/27 行銷年度期末庫存，百萬蒲式耳。
- 方法：`USDA_PREVIOUS_WASDE_PERSISTENCE_V0`，僅以上期官方估計延續，預測 **1,758 百萬蒲式耳**；絕非 AI 生成的資訊優勢。
- 最新輸入：USDA 2026-11-10 WASDE #677，該報告中之期初 2,095、產量 15,893、進口 25、飼料與剩餘用途 5,975、食品種子工業 7,005、出口 3,275，公式 `2095+15893+25-5975-7005-3275=1758`。
- 官方文字來源：https://esmis.nal.usda.gov/sites/default/release-files/796142/wasde1126.txt
- 資料時間：`2026-11-17T00:57:44Z`；預測生成同時刻，均在下次 WASDE 之前。
- 此輪工具僅驗證官方公開網頁所列數字、供需帳與前後時序；由於原始 TXT 位元組未能在此環境直接下載核對，`source_raw_sha256=null`，不可宣稱官方原始檔獨立 PIT 認證。

### 可查驗的承諾（pre-release commitment）

| 證據 | SHA-256 |
|---|---|
| 輸入 JSON | `b248ba007ea520281d9ab0be4df5479b6d403b3fa4ef204ae7b344e4e9ae439f` |
| 預測 JSON | `54d4d7597d457c64307e9a2e1e5670cd5f1ecd52676180eded2a19a8ebcaca48` |

兩份檔案分別提交在 PR #22 隔離分支；預測檔首次提交 commit `3de8b6e9b27471080a031d8ad56169126c16a0ff`，GitHub API 當時回報 `created_at=2026-11-17T00:58:10Z`；這是可公開查閱的版本存證，**不是不可刪改的獨立發布商封存或交易所 PIT 認證**。若 branch 移動應依 commit permalink 查原件。

- 提交時的預測檔：https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/blob/3de8b6e9b27471080a031d8ad56169126c16a0ff/research_core/k4/cases/2026-12-10-forward-baseline-forecast.json
- `research_core/k4/cases/2026-12-10-ex-ante-registration.json` 登記 forecast commitment，但 `consensus_* = null`、`frozen_before_release=false`，因**整個預測 vs 共識比較**尚未完成，不能自動轉為預測能力通過。

## 可重現的最小測試

```bash
python -m unittest research_core.k4.tests.test_forward_baseline -v
python -m research_core.k4.forward_baseline --case research_core/k4/cases/2026-12-10-forward-baseline-input.json --output local-private-k45/k45_dec_baseline.json
python -m research_core.k4.ex_ante_gate --case research_core/k4/cases/2026-12-10-ex-ante-registration.json --output local-private-k45
```

預期基準 1,758，獨立交易資訊驗證 NO-GO；未封存市場共識時整體 `BLOCKED_NO_EX_ANTE_EVIDENCE`。

## 下一道最有價值的研究工作：超越持平基準

1. 透過真正有來源與公告前截止時間的 NASS 作物狀態、USDA FAS 每週出口銷售等供需驅動資料，建立**獨立的驅動變數變化量**。若沒有足以量化其對 WASDE 同一年度庫存的影響，不可把任意變化直接稱為預測。
2. 分開保留 `v0` 不變的預測與事先確定的 `v1` 增量模型；若有 v1，**另立**完整的輸入版本／模型規則／SHA／公告前封存，絕不可改寫 v0。
3. 事前取得至少一個 12 月 WASDE 市場共識原始來源，保存方法、日期、不可事後回填的公開或獨立封存證據；不得用 11 月的事後整理代替 12 月共識。
4. 12 月公告後取得官方首版、確定真正可得時間，分別比較 v0／v1／當期市場共識的誤差；單一事件只做機制驗收，不得聲稱勝率或 alpha。

**維持限制：** PIT 未獨立審核，未證實超越共識，未交易、不再購買付費行情、研究分支不合併 main；無原始授權限制數據對外發布。
