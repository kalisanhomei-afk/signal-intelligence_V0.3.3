# SIGNAL R1k｜BIS 美元／歐元／日圓信用同口徑比較：最小離線提取器

日期：2026-11-23 Asia/Taipei。**狀態：OFFLINE_CODE_DONE / LOCAL_SYNTHETIC_TESTS_12_OF_12_PASS / REAL_EUR_JPY_VALUES_NOT_YET_EXTRACTED / GATE0_BLOCKED。**

## 已核對來源與可比較定義

BIS 官方 GLI 將「外幣信用」定義為由銀行貸款與國際債券提供、借款人位於**各該貨幣原生經濟區以外**的非銀行信用：

| 貨幣 | 官方表 | 借款區域排除範圍 | 存量八維鍵 | 官方年增率八維鍵 |
|---|---|---|---|---|
| 美元 | E2.1 | 美國境外 | `Q.USD.3P.N.A.I.B.USD` | `Q.USD.3P.N.A.I.B.771` |
| 歐元 | E2.2 | 歐元區境外 | `Q.EUR.3P.N.A.I.B.EUR` | `Q.EUR.3P.N.A.I.B.771` |
| 日圓 | E2.3 | 日本境外 | `Q.JPY.3P.N.A.I.B.JPY` | `Q.JPY.3P.N.A.I.B.771` |

官網：https://data.bis.org/topics/GLI 、https://data.bis.org/topics/GLI/tables-and-dashboards；官方三組 series metadata：
- https://data.bis.org/topics/GLI/BIS%2CWS_GLI%2C1.0/Q.USD.3P.N.A.I.B.USD
- https://data.bis.org/topics/GLI/BIS%2CWS_GLI%2C1.0/Q.EUR.3P.N.A.I.B.EUR
- https://data.bis.org/topics/GLI/BIS%2CWS_GLI%2C1.0/Q.JPY.3P.N.A.I.B.JPY

**比較限制**：三種貨幣不能直接相加，借款人地理範圍也不同；只能比較 BIS 相同口徑下的「年增率及加減速」，不宣稱資金實際跨幣別遷移，亦不能直接推論股市、黃金或外匯資金流向。官方 `.771` 是匯率及統計斷點調整後、四季複合的年增率，不能以兩期名目存量差替代。

官方當期背景：2026 年 7 月 BIS Q1 評論稱境外美元信用年增約 **7.3%**、歐元約 **12%**；10 月 Q2 評論描述歐元計價境外信用成長快於美元及日圓，但沒有為本工具提供已核對的三種貨幣全套逐季數字。資料：https://www.bis.org/publications/202607-commentary-ibs-gli 、https://www.bis.org/publications/202610-commentary-ibs-gli。

## 實際技術交付與驗證

- `scripts/bis_gli_cross_currency_slice.py`：只接受已存在的本機 ZIP，**硬性綁定 Antigravity 已保存 ZIP SHA-256** `87c8b99cca6043ae7737fb9c15159ad5920d0fdf260e9c9a68d03cec7cb95899` 及內部 CSV SHA-256 `1bf5aff7ef3903da56ee0e6400a7390cfdb5dee397857625613233d14eaf7cdc`；不下載網路資料、不改原檔、不寫下新數值資料檔。
- 定向提取 **2026-Q1 / 2026-Q2 × USD/EUR/JPY × 存量（原幣百萬）/官方年增率（%）＝12 格**；要求 12/12 值、無重複、`OBS_STATUS=A`、欄位及單位倍數正確；拒絕不同 ZIP 或不同時間版的隱性替換。
- CLI 執行參考（僅在已存 ZIP 的 Antigravity 工作目錄；**不要再次下載**）：
```bash
python3 scripts/bis_gli_cross_currency_slice.py research_raw/20261123T004025_162908Z_bis_gli_87c8b99cca60.zip
```
- `tests/test_bis_gli_cross_currency_slice.py`：**本地獨立 Python 合成資料測試 12/12 PASS**，包含 12 格完整性、精度與百分點差、各幣區域差異、ZIP 與內部 CSV hash、缺值、重複、異常狀態、倍數錯誤、無網路 fallback 等。
- Git Blob SHA 對照：來源 `493cb826852a5d4df6dd7c18e3d797dcba331be2`，測試 `038ad0183203a6d99b287967ca636a1162d2f11c`；與獨立本機 `git hash-object` 一致。此定向測試**尚非 GitHub CI 專門測試**，不可將 Project continuity CI 說成對 BIS 真實值的驗證。
- 結果輸出設計固定 `historical_pit_verified=false`, `accepted_for_model=false`, `gate0=BLOCKED`，即使來源數值完整也不會提升正式資料關卡。

## 阻塞與下一步

**現階段阻塞**：此 ChatGPT 環境無法存取 Antigravity 的本機 `research_raw/` 原 ZIP；目前只完成可重現提取工具與合成品質測試。**不提供未曾實際取得的歐元或日圓 Q1/Q2 精確值**。

下一步為一次 Antigravity **既有檔案唯讀 CLI 執行**，只回傳 12 格有限摘要、來源 SHA 比對狀態、是否 0 缺值及三個幣別 YoY 百分點差。結果到手後再完成描述性研究卡並更新同一 PR。若 12 格不齊或倍數不同，需標記 BLOCKED、檢查 schema，不能為了湊數更改未核准的來源。

**零新增訂閱支出**；本輪沒有 BIS ZIP 重新下載、真實模型回測、交易、部署、main 合併或開始多 Agent。
