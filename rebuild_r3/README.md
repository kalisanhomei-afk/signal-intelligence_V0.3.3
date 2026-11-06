# SIGNAL Evidence Rebuild R3｜arXiv 作者摘要結構化（隔離離線驗收）

## 目標與嚴格界線

R3 是在 `signal-evidence-rebuild` 分支新增的**獨立**離線研究摘要實驗，不修改 R1、R2，也不會修改原本的 SIGNAL 網站。

本包只讀取使用者先前上傳的 V0.5.4 GitHub Actions Artifact `evidence.json` 裡，arXiv 研究 MESA 的**作者摘要** E1～E6（固定來源、固定內容）。**不是**任意 arXiv 論文通用解析器；不重新連網、不呼叫 OpenAI、不向 GitHub 發布內容。

來源文章：`https://arxiv.org/abs/2611.05567`

資料來源：先前使用者上傳的 `signal-v054-source-excerpts-ai-manual-review(3).zip/evidence.json`；此包附上從中擷取並保存的六段原文字句。來源 sha256 指紋只證明測試 fixture 與先前保存內容一致，**不證明摘要主張真實、數據可重現或已同儕審查**。所有數值均是「作者摘要自述，待核對」。

## 產生的六項待查證事實

| Fact ID | 作者摘要內容 | 資料性質 | 摘錄 |
|---|---|---|---|
| ARXIV-F001 | 5 個 evaluation suites | 方法設計數量（非效能） | E4 |
| ARXIV-F002 | 4 個泛化軸（空間、物件實例、物件類別、子任務） | 方法設計數量 | E4 |
| ARXIV-F003 | 2 個平台／套件（MESA、BiMESA） | 作者自述研究設計 | E5 |
| ARXIV-F004 | 評估 7 種 baseline methods | 作者自述實驗設計 | E6 |
| ARXIV-F005 | 最強模型於 MESA 的百分比 52% | 作者報告結果，**指標定義未核實** | E6 |
| ARXIV-F006 | 最強模型於 BiMESA 的百分比 49% | 作者報告結果，**指標定義未核實** | E6 |

**重要：** 摘要沒有足夠資訊得知 52% / 49% 的具體指標定義、分母、信賴區間；不應自行稱作「準確率」或「任務成功率」。作者聲稱 BiMESA 是第一個大規模雙臂泛化 benchmark，這是**未獨立核實的優先權主張**。5 個 suite 並不是另加 4 個軸得出 9 個 suite。

## Windows 測試方法（選做；無 Python 也可以先看報告）

1. GitHub Desktop 上方先確認 `Current branch = signal-evidence-rebuild`，**不要選 main**。
2. 把 ZIP 裡的 `rebuild_r3` 資料夾放入 Repository 根目錄，使 `rebuild_r1`、`rebuild_r2`、`rebuild_r3` 三者並列。
3. 直接用 Chrome 開啟 `rebuild_r3/out/arxiv_review.html` 查看本次已產生的示範報告。
4. 若已裝 Python，可在 Repository 根目錄執行：

```powershell
python -m unittest discover -s rebuild_r3 -p "test_*.py" -v
python rebuild_r3/arxiv_pipeline.py --input rebuild_r3/fixtures/arxiv_mesa_abstract_e1_e6.json --output rebuild_r3/out/arxiv_facts.json --report rebuild_r3/out/arxiv_review.html
```

（Windows 若只有 `py`，把 `python` 改為 `py`。）

5. 若要再驗證全部三個獨立實驗，可依序執行：

```powershell
python -m unittest discover -s rebuild_r1 -p "test_*.py" -v
python -m unittest discover -s rebuild_r2 -p "test_*.py" -v
python -m unittest discover -s rebuild_r3 -p "test_*.py" -v
```

## GitHub Desktop 提交

1. 左下角確認僅新增 `rebuild_r3/...`，無其他需要提交的修改。
2. Summary 輸入：`Add isolated arXiv author-abstract fact extraction R3`。
3. 點選 `Commit to signal-evidence-rebuild`。
4. 點選 `Push origin`。
5. 不要點 Create pull request、不合併 main、不執行 V0.5.4 的付費 AI Actions。

## 驗收界線、下一階段

本機離線測試涵蓋固定來源、摘要雜湊、來源標記、指標角色、百分比口徑警告、遭篡改資料拒絕、禁止自動發布。並不等同人工閱讀論文全文或外部重複驗證成功。

**R4 才處理三種資料來源（BEA／EIA／arXiv）的共用 Schema 與 AI 的 fact ID 引用契約。** 在 R4 的完全離線模擬測試通過以前，不做任何付費 API 測試。
