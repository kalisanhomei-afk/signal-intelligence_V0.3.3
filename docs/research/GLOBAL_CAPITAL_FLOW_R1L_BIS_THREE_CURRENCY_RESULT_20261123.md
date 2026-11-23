# SIGNAL R1l｜BIS 三大國際貨幣境外信用比較：實測證據與假說審查

日期：2026-11-23 Asia/Taipei。**狀態：EXTERNAL_REAL_DATA_12_OF_12_PASS / CROSS_CURRENCY_DESCRIPTION_DONE / HISTORICAL_PIT_BLOCKED / MODEL_GATE0_BLOCKED。** 本輪承接 R1k 工具與先前 ZIP 驗證，不重新下載、不重跑測試、不啟動 M0/M1/M2。僅把使用者貼上的 Antigravity 實際 CLI 結果與 BIS 官方當期說明轉為可追溯研究成果。

## A. 證據身分與來源限制

- BIS Global Liquidity Indicators (GLI), dataset `WS_GLI(1.0)`, E2.1 USD / E2.2 EUR / E2.3 JPY。https://data.bis.org/topics/GLI/tables-and-dashboards
- 官方全球流動性定義：https://data.bis.org/topics/GLI
- 2026-Q2 官方 BIS 評述：https://www.bis.org/publications/202610-commentary-ibs-gli
- BIS 2026-Q1 評述：https://www.bis.org/publications/202607-commentary-ibs-gli
- 方法（年增率與修訂）：https://data.bis.org/faq
- Antigravity 已保存 ZIP，取自 https://data.bis.org/static/bulk/WS_GLI_csv_flat.zip ，HTTP 200，擷取 UTC 2026-11-23T00:40:25.162908Z，HTTP Last-Modified 2026-11-18T12:44:16Z（晚於官網 Q2 公布日期 2026-10-29）。
- **外部原始 ZIP SHA-256** `87c8b99cca6043ae7737fb9c15159ad5920d0fdf260e9c9a68d03cec7cb95899`；**外部內部 CSV SHA-256** `1bf5aff7ef3903da56ee0e6400a7390cfdb5dee397857625613233d14eaf7cdc`。本次 Antigravity 原有 ZIP 透過 R1k 腳本在執行時重新驗證兩個 SHA：CLI exit 0、12/12 cells、0 missing/duplicate、OBS_STATUS=A、乘數符合。**ChatGPT 未持有來源原始位元組**，只是檢查輸出 JSON、重新核對百分點計算。
- 本表是 **2026-11-23 當期最新修訂 ZIP 的兩季數值**，不可回填成 2026 年 Q1、Q2 決策當時已知的舊版本。`PIT=false` / `accepted_for_model=false` / `Gate0=BLOCKED`。

## B. 主要實測：相似統計定義，但不是同一借款人群體

三者均為計價貨幣在**該幣原生貨幣區以外**提供給非銀行借款人的銀行貸款＋國際債券信用。借款人各自排除美國／歐元區／日本，因而母體**不相同**。

| BIS 指標 | 借款人範圍 | 2026-Q1 BIS 官方 YoY | 2026-Q2 BIS 官方 YoY | Q2−Q1（百分點） |
|---|---|---:|---:|---:|
| 美元 USD `Q.USD.3P.N.A.I.B.771` | 美國境外 | **7.308%** | **8.030%** | **+0.722** |
| 歐元 EUR `Q.EUR.3P.N.A.I.B.771` | 歐元區境外 | **12.627%** | **13.813%** | **+1.186** |
| 日圓 JPY `Q.JPY.3P.N.A.I.B.771` | 日本境外 | **2.928%** | **7.116%** | **+4.188** |

原幣名目存量（**百萬單位，不能相加／直接比較金額**）：美元 Q1 `14770950.729`、Q2 `15132723.957` 百萬美元；歐元 Q1 `5156518.229`、Q2 `5389820.686` 百萬歐元；日圓 Q1 `68312707.17`、Q2 `70013771.723` 百萬日圓。原幣 `UNIT_MULT=6: Millions`，官方 YoY `UNIT_MEASURE=771`, `UNIT_MULT=0`。

### 兩種不同的領先指標，切勿混淆

- **Q2 成長率水準**：EUR **13.813%** > USD **8.030%** > JPY **7.116%**。
- **Q1→Q2 成長率加速**：JPY **+4.188pp** > EUR **+1.186pp** > USD **+0.722pp**。日圓增加最多百分點**不是**日圓總額最大，也不表示日圓資金流入最快。
- EUR–USD 年增率差：Q1 **+5.319pp**，Q2 **+5.783pp**，擴大 **+0.464pp**。
- JPY–USD 年增率差：Q1 **−4.380pp**，Q2 **−0.914pp**，收斂 **+3.466pp**。
- **重要：BIS YoY 為匯率及統計斷點調整後四季複合變化**，不是單純原幣名目存量年化 QoQ 差，也不是跨幣資金實際轉移。

## C. 另一個獨立的 BIS 官方當期證據：歐元「占比」

BIS 2026-Q2 發布的 **2026 年 10 月評論**顯示歐元在國際外幣信用（銀行貸款與國際債券）中的占比從 2022 年起提高，且歐元計價的境外信用成長比美元／日圓快。另 Q1 評論指出 2022Q3→2026Q1 的歐元信用占比由 22% 增至 28%（其全球比較集合與定義以原官方圖表為準）。

這些**發布時的敘述資料是獨立官方證據**，不是本次 12 格 CLI 提取直接計算出的市場占比，不得反過來將百分比分配表作為來源 ZIP 內原始值或特定日期 ZIP byte-vintage 證據。
- Q2 評述：https://www.bis.org/publications/202610-commentary-ibs-gli
- Q1 評述：https://www.bis.org/publications/202607-commentary-ibs-gli

## D. 研究解釋與可反駁競爭假說

**已觀察的描述性事實**：2026Q2 三幣境外非銀行信用 YoY 全部較 Q1 回升；歐元在三者中 YoY 最高；日圓 YoY 加速最大；BIS 官方評論另有歐元外幣信用占比提高的證據。

**應測而未驗證的經濟假說（H-GCF-FX-CREDIT-REL-01；不更改原 R0）**：外幣信用的相對成長與已發布的占比變化，可能反映國際融資結構與幣別資金供給條件的轉變。是否能在真正的發布日之後，對股票、短期現金、美元匯價或商品價格預期提供增量資訊？目前**無證據**回答；不能從上述事實推導出「資金由美股流向歐股/日債」、「美元流動性消失」、下一月股票會漲或跌。

**反向機制**：歐元信用占比上升可由融資成本、發行人結構、外幣再融資、借款需求、銀行貸款與債券替代等多項機制導致；不同外幣區域不是相同母體；BIS 的統計資料為信用**存量**與調整後變化，並非追蹤資金最終買入的資產類別。

**統計 Gate**：保留原 `H-GCF-USD-CREDIT-01` 與事前註冊 M0/M1/M2，不能事後將差異最大者「日圓加速」直接加進正式預測模型而不修訂研究章程及多重假說控制。跨貨幣比較是**探索性競爭解釋研究**；在歷史 PIT、授權的可交易總報酬標籤及樣本外驗證未備妥前，`R2_NOT_STARTED` / `GATE0_BLOCKED`。

## E. 完成、證據、阻塞及下一步

- 已完成：Antigravity 同一 ZIP CLI 實際退出碼 0、12/12 跨貨幣值（source-reported），來源 SHA 與內部 SHA 一致，描述性三貨幣年增率水準/百分點變化、兩幣年增率差異、本報告與有限 JSON evidence。
- 未完成：完整 2007–2026 歷史 PIT、各月發布時間與 vintage、可交易股票相對短券報酬來源與使用權、真正資金移動對各類資產的傳導關係及統計顯著性。
- **建議暫停增加 BIS 提取工具**。下一個較有價值的問題是回到已定稿的 R0 主假說：選一個官方 2026-10-29 同時代 GLI release narrative 對照已取得的 2026Q2 snapshot，以明確標示可用日資訊；並建立「歷史時點可用特徵與可交易 outcome」的剩餘門檻清單，避免研究停在無止境增加比較頁／JSON。
- 新增資料費 US$0；本輪未重下載 BIS、未啟動任何正式回測、未購買服務、未交易、未部署、未合併 main。
