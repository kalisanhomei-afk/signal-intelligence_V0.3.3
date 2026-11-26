# SIGNAL R1u | H-ICI-WRAPPER-01 首筆事前規則後觀測（2026-11-26 唯讀查核）

**判定：** `FORWARD_RULE_FIRST_OBSERVATION_RECORDED`、`WRAPPER_DIVERGENCE=TRUE`、`MMF_SAME_WEEK_DECREASE=TRUE`、`1_OF_4`、`PIT_UNVERIFIED`、`ROTATION_UNPROVEN`、`R2_NOT_STARTED`、`NO_TRADING`。

## 1. 既有註冊規則及不可改條件

延續既有 `docs/research/GLOBAL_CAPITAL_FLOW_R1U_ETF_MUTUAL_FUND_DIVERGENCE_PILOT_20261123.md` 於 **2026-11-23** 寫明的 `H-ICI-WRAPPER-01`。只計入後續「完整 ICI 股權共同基金、股權 ETF、股權合計」三欄均已公布的連續可比週；三條符號條件為「共同基金 < 0、ETF > 0、合計 > 0」。MMF 僅在相同 observation week-end 時紀錄存量變動方向，絕不可將不同類別的流量視為互相轉帳。註冊規則要求四筆，不因新結果而放寬或事後挑選。

## 2. 首筆實際新觀測（同一 2026-11-18 截止週）

**觀測截止日：2026-11-18；查核日：2026-11-26（台灣）。** 原始公開網頁的文字目前可讀取，但沒有取得能獨立重算 HTTP body SHA-256 的原始位元組；網站當前內容可能被修訂，公告當下精確 UTC、首版 byte vintage 均未獨立認證。

| ICI 指標 | 2026-11-18 | 發布日 | 類別 |
|---|---:|---|---|
| 股票共同基金估計淨新現金流 | **−18,955 USD million** | 2026-11-25 | 正式 ICI 公開文字，可能修訂 |
| 股票 ETF 估計淨發行 | **+74,800 USD million** | 2026-11-24 | 正式 ICI 公開文字，可能修訂 |
| 股票合計估計流入 | **+55,844 USD million** | 2026-11-25 | ICI 對應合併類別 |
| 基本相加 | +55,845 USD million | 2026-11-26 計算 | 兩分項合計與合併差 **1 USD million**，相對於估計/四捨五入標示屬容忍差，不宣稱完全相等 |

來源：
- ICI combined, 2026-11-25: https://www.ici.org/research/stats/combined_flows
- ICI estimated long-term mutual, 2026-11-25: https://www.ici.org/research/stats/flows
- ICI ETF issuance, 2026-11-24: https://www.ici.org/research/stats/etf_flows

**事前符號規則：** `-18,955 < 0` 且 `+74,800 > 0` 且 `+55,844 > 0`，故此一週 `WRAPPER_DIVERGENCE=TRUE`，目前僅 **1/4** 筆完整候選，不能預先稱達到 3/4 或顯著。

## 3. 同截止日 MMF 核對（同週匹配，不是流量路徑）

ICI 2026-11-25 公開 MMF 報告表明：
- `2026-11-11` MMF total assets = **7,980.02 USD billion**；
- `2026-11-18` MMF total assets = **7,976.44 USD billion**；
- 同一 11/18 截止日與上述股權三項一致，兩值相差 **−3.58 USD billion**；
- 這是 **MMF 資產變動**，非經逐筆核對的淨交易流，更不是資金移往 ETF 的因果證明。

來源 ICI MMF, 2026-11-25: https://www.ici.org/research/stats/mmf 。

下一筆候選原本是 2026-11-25，但感恩節影響下 ICI MMF 下一截止日是 **2026-11-24（星期二）**；如股票類資料維持 11/25 截止，則必須標為 `INCOMPARABLE`，不可對齊或偷偷更改預註冊週別。後續 12/02、12/09 同理必須先檢查各系列截止日。

## 4. 來源證據等級與研究使用限制

- `OFFICIAL_WEBSITE_TEXT_OBSERVED=TRUE`；`ORIGINAL_HTTP_BYTES_CAPTURED=FALSE`；`ORIGINAL_SHA256=null`；`FIRST_PUBLICATION_EXACT_UTC_UNVERIFIED=TRUE`；`MODEL_DATA_RIGHTS_UNVERIFIED=TRUE`。
- 這是 **2026-11-23 預先註冊規則後，2026-11-24/25 公布的第一筆描述性樣本**，具有觀察時間先後順序，但不等於獨立證明每一來源的首版完整 PIT。
- 來源網站警告歷史估算可能調整；不得把今天讀到的版本回填成過去每一天交易前所知的數字。
- 無法證實 **MMF → ETF／股票** 特定資金路徑；不能把股權 ETF 淨發行和股票二級市場逐筆資金混為一談。
- 本次只記公開表格四個聚合數字及核對規則，不抓取受權利限制的完整歷史 XLSX、不擴張 SPY/BIL 市場定價或 R2 模型。
- 既有 TIC ZIP `npr_history.csv` **單欄交叉驗證已由 Antigravity 2026-11-22 回報 PASS**；H.6 與 TIC 原始檔亦已於外部環境捕獲，故不重抓這兩份。缺的是 ChatGPT 獨立 raw bytes 複驗、首版歷史 PIT 與授權，不是「全部資料都尚未取得」。

**下一步：** 等預註冊的下次 ICI 各系列正式公布後再核對日期與數值，累積四個完整匹配週；每個新週只追加一筆、有缺漏就標 `INCOMPARABLE` 或 `INSUFFICIENT_COVERAGE`。本輪不觸發任何新遠端擷取、模型或交易。
