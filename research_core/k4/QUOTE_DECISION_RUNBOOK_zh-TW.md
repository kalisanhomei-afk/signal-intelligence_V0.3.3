# K4 真實行情取得｜最小採購決策卡（2026-11-16）

**狀態：程式與離線測試已備；實際 Databento 帳戶未連接，尚無官方查價回傳。禁止捏造費用或資料筆數。**

## 目標與停止規則

唯一目標：核實 2026-11-10 CBOT 玉米 2026 年 12 月期貨 `ZCZ6` 在公告前後 180 分鐘內是否有真實盤中資料及查詢費用。資料集 `GLBX.MDP3`，UTC `16:30–19:30`，查 `ohlcv-1m`、`trades`、`tbbo`；不下載、不購買、不訂月費。

1. 必須先確認官方 symbology 對 `ZCZ6` 解析至唯一 instrument ID。
2. 使用 Databento `get_record_count` 和 `get_cost` 查三個 schema 的筆數與美元費用。這兩個 metadata API 不下載行情；需供應商帳戶 API key。
3. 將私有的 `databento_quote_only.json` 交給 `vendor_quote_decision.py` 判斷。若無分鐘線，停止此特定資料管道；若只有分鐘線，最多進行敘述性事件研究；即使成交與 TBBO metadata 有數量，仍需分開核查授權、實際行情與交易成本。Metadata 可能高估筆數。
4. 任何購買行情、下載或付費訂閱必須事先另外取得 owner 明確核准；未取得法律／授權條件不購買。
5. 沒有實際原始市場資料，事件研究 `NO-GO`、交易 `NO-GO`。單日樣本不構成有效策略績效證據。

## 已準備程式

- `research_core/k4/vendor_quote_only.py`：供應商帳戶授權環境執行；僅查 metadata；不將 API key 寫入檔案或日誌。
- `research_core/k4/vendor_quote_decision.py`：檢查費用、schema、筆數與合約日期；輸出 `k4_quote_decision.json`，不會解鎖交易。
- `research_core/k4/tests/test_vendor_quote_only.py`、`test_vendor_quote_decision.py`：離線防呆測試。

**最低限度操作**：先由使用者自行決定是否註冊 Databento 帳戶。憑證不得貼至 ChatGPT 對話或 GitHub Issue／PR。若有受信的本地環境，可設定 `DATABENTO_API_KEY` 並執行：

```bash
python -m pip install databento
python -B -m research_core.k4.vendor_quote_only --output local-private-k4-quote
python -B -m research_core.k4.vendor_quote_decision --quote local-private-k4-quote/databento_quote_only.json --output local-private-k4-review
```

此操作**僅做查價**。避免把含帳戶資訊的例外訊息或私有檔案提交至公開 GitHub。若對命令列不熟悉，可以先跳過帳戶設定；下一步可以另外設計受信的低操作門檻流程，前提仍是帳戶/授權安全。

官方 API 文件：https://databento.com/docs/api-historical/metadata?lang=python

**單次事件研究成本門檻尚未設定，不得用任意數字代替使用者採購核准。**
