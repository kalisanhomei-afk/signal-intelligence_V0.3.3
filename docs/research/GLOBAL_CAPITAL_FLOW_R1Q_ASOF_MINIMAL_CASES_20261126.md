# SIGNAL R1q｜公開資料 as-of 時序閘門：四筆來源日期實例（2026-11-26）

**執行範圍：** R1「Public Data First」一筆最小正式時序驗證，不改 R0 研究範圍、月末 16:00 America/New_York 截點或任何 K4/K5 凍結預測；不需付費、不抓原始 ZIP、不要求使用者重傳已保存資料。

## 核對基礎
- 已唯讀恢復 SIGNAL `AGENTS.md`、main/PR #29 `docs/CURRENT_STATUS.md`、Issues/PR/CI，且讀取既有 R1b/R1c/R1m 收據及文本。引用官方發布日只能給**日期級**可得性，不能冒充逐秒與歷史首次位元組驗證。
- 本輪以官方頁面對照：2020 年 1 月 TIC **2020-03-16** 公布 +122.9 十億美元；2026 年 9 月 TIC **2026-11-18** 公布 +261.0 十億美元；2026-Q2 BIS GLI 最新公布日 **2026-10-29**。**上述公布內容均為目前可回看之官方文字，不是各日期當日原始 HTML byte snapshot。**
- 官方連結： https://home.treasury.gov/news/press-releases/sm943 ; https://home.treasury.gov/news/press-releases/sb0693 ; https://home.treasury.gov/data/treasury-international-capital-tic-system/release-dates-of-tic-data ; https://data.bis.org/topics/GLI

## 四筆 as-of 判斷（不是回測）

| 研究截點（美東 16:00） | 來源資料觀察期 | 官方當次發布日 | 日期條件 | 最終入模 |
|---|---|---|---|---|
| 2020-02-28 | TIC 2020-01，+122.9 十億 USD | **2020-03-16** | 晚於截點，確定尚未公布 | **REJECT** |
| 2020-03-31 | TIC 2020-01，+122.9 十億 USD | **2020-03-16** | 發布日在截點之前，但無完整當日 bytes | **HOLD** |
| 2026-10-30 | TIC 2026-09，+261.0 十億 USD | **2026-11-18** | 晚於截點，確定尚未公布 | **REJECT** |
| 2026-10-30 | BIS GLI 2026-Q2 | **2026-10-29** | 發布日在截點之前，但精確首次公布 UTC／當時 CSV 版本不明 | **HOLD** |

**可驗證結果：** 4 筆中 2 筆排除（確定未公布）、2 筆保留待證（發布日期較早但缺歷史 PIT/權利）。**0 筆准許進入正式模型**。這不是 0/4 預測準確率，也不是宣稱官方資料不能用；是對「交易當時已知資訊」的嚴格時間守門。

### 為何不能把 HOLD 自動放行？
- 2020-03-16 TIC ZIP 已於 2026-11-22 被 Antigravity 外部擷取並回報 SHA，`npr_history.csv` 指定數值對照新聞稿 PASS；但 ZIP `Last-Modified` 為 2026 且存在封存成員時間戳晚於當次新聞稿的風險。因此不能用 2026 版本宣稱 2020-03-31 已見過相同 bytes。
- 2026-10-29 BIS 官方評論可支持該月公布方向，Antigravity 11/23 捕獲的目前 ZIP 可供未來前瞻比較；**不能**證明 10/30 16:00 ET 時的精確 CSV 初始值已公開，且使用權仍有條件。
- TIC 官方一般 16:00 ET 發布，若資料**剛好**於同一截點公布，也必須採保守延遲，不得視為當時可用。
- 正式回測同時需合法資料權利與可交易含息 SPY/BIL outcome；本輪完全未取得這兩項。

## 下一個最小驗證
1. 不再重抓已有的 2020 TIC ZIP；若原件在授權隔離環境可用，後續再做獨立唯讀 raw hash/文件版次複驗。
2. 利用**未來**已安排 K4/K5 官方公告，建立 receipt 的確實 UTC/source SHA，從現在起累積前瞻且真正「事前可得」的證據；每個來源截點依同一守門規則放行或拒絕。
3. SPY NAV 原始上傳檔已由上次驗收 (PR #29) 讀取 5,786 筆且發現 2014-10-07 資產/流通股一致性疑點；不能要求重傳，不能用 NAV 取代可成交且含息報酬；BIL 尚未驗收。
4. **R1_GATE0=BLOCKED, R2_NOT_STARTED, NO_TRADING**。不得因 4 筆來源時間判斷而宣稱 M2 投資訊號已有效。

對應結構化稽核：`docs/research/global_capital_flow_r1q_asof_guard_cases_20261126.json`。不包含官方原始數據檔、商業行情或任何敏感材料。
