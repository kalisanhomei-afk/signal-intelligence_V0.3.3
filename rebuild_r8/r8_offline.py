#!/usr/bin/env python3
"""SIGNAL R8-A: offline, fixed-snapshot, evidence-bounded editorial drafts.

This module DOES NOT use a model, any network, or the production SIGNAL site.
Claims and human-readable narrative are hand-written test fixtures, NOT AI output.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
FIX = BASE / "fixtures"
OUTPUT = BASE / "out"
EXPECTED_SOURCE_SNAPSHOT_SHA256 = "1bca9543dea02a954ae374087c703d40a2d91418aa1de51f49d1b3cc247590a5"
CASE_NAMES = {"bea": "BEA｜美國對台貿易", "eia": "EIA｜煉油產品配置", "arxiv": "arXiv｜MESA 機器人研究"}
REQUIRED_KEYS = {"schema_version", "case_id", "observation", "interpretation", "impact", "importance", "limitations", "next_checks", "publication_allowed"}
CLAIM_KEYS = {"text", "claim_type", "fact_ids", "assumptions"}
TYPES = {"observation": "fact", "interpretation": "inference", "impact": "hypothesis"}
# NOTE: A deterministic lexical guard is NOT a semantic factual verifier.
WRITTEN_NUMBER_PATTERN = re.compile(r"\d|百分之[零〇一二三四五六七八九十百千萬億兩]+|[零〇一二三四五六七八九十百千萬億兩]{1,8}(?:億美元|萬美元|美元|個百分點|百分比|％|%|倍|年|月)")
CERTAINTY_PATTERN = re.compile(r"(?:已獨立驗證|已經證實|必然|一定會|保證獲利|確定導致|價格必漲|全球首創|已商業化)")
CASE_SPECIFIC_BANS = {"arxiv": ("成功率", "準確率", "商業部署已成熟"), "eia": ("終端油價必漲", "精確產出率"), "bea": ("已確認受益企業",)}


class DraftError(ValueError):
    def __init__(self, code: str, field: str, explanation: str):
        super().__init__(f"{code} @ {field}: {explanation}")
        self.code = code
        self.field = field
        self.explanation = explanation


def fail(code: str, field: str, message: str) -> None:
    raise DraftError(code, field, message)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fact_catalog() -> dict:
    if sha_file(FIX / "fact_catalog_snapshot.json") != EXPECTED_SOURCE_SNAPSHOT_SHA256:
        fail("SOURCE_SNAPSHOT_CHANGED", "fact_catalog_snapshot", "固定事實快照 SHA256 不符，請勿以未審核數據取代")
    catalog = read_json(FIX / "fact_catalog_snapshot.json")
    if catalog.get("schema_version") != "signal-unified-fact-catalog-r4" or catalog.get("publication_allowed") is not False:
        fail("INVALID_CATALOG", "fact_catalog_snapshot", "快照版本或發布限制不符")
    sources = catalog.get("sources")
    if not isinstance(sources, dict) or set(sources) != set(CASE_NAMES):
        fail("INVALID_CATALOG", "sources", "三來源完整性檢查失敗")
    total = 0
    for case, facts in sources.items():
        if not isinstance(facts, dict) or not facts:
            fail("INVALID_CATALOG", case, "缺少來源事實")
        for fact_id, f in facts.items():
            if f.get("fact_id") != fact_id or f.get("case_id") != case:
                fail("INVALID_CATALOG", fact_id, "事實 ID 與來源不一致")
            if not isinstance(f.get("value_original"), str) or not isinstance(f.get("unit_original"), str):
                fail("INVALID_CATALOG", fact_id, "原始數值或單位缺失")
            if not f.get("source_evidence_id") or not str(f.get("source_url", "")).startswith("https://"):
                fail("INVALID_CATALOG", fact_id, "證據來源不完整")
            if f.get("independently_verified") is not False:
                fail("INVALID_CATALOG", fact_id, "來源快照不可自稱已獨立查證")
            total += 1
    if total != 16 or catalog.get("fact_count") != 16:
        fail("INVALID_CATALOG", "fact_count", "此離線案例固定為十六筆事實")
    return catalog


def assert_keys(value: Any, expected: set, field: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        fail("INVALID_SCHEMA", field, f"欄位集合不符；必要欄位 {sorted(expected)}")


def safe_text(value: Any, field: str, min_len: int = 12) -> str:
    if not isinstance(value, str) or len(value.strip()) < min_len:
        fail("INVALID_TEXT", field, "文字不可為空或過短")
    if WRITTEN_NUMBER_PATTERN.search(value):
        fail("MODEL_GENERATED_NUMBER", field, "模型自由文字不可含數字、日期或簡單中文數量表述")
    if CERTAINTY_PATTERN.search(value):
        fail("UNSUPPORTED_CERTAINTY", field, "文字含有未具備證據的絕對斷言")
    return value


def check_authored_texts(draft: dict) -> None:
    """Check only prose fields; fact IDs (with digits) are handled separately."""
    case = draft["case_id"]
    banned = CASE_SPECIFIC_BANS[case]
    fields: list[tuple[str, Any, int]] = []
    for name in TYPES:
        obj = draft[name]
        fields.append((f"{name}.text", obj["text"], 12))
        fields.extend((f"{name}.assumptions[{i}]", a, 5) for i, a in enumerate(obj["assumptions"]))
    fields.append(("importance.reason", draft["importance"]["reason"], 15))
    fields.extend((f"limitations[{i}]", a, 5) for i, a in enumerate(draft["limitations"]))
    for i, c in enumerate(draft["next_checks"]):
        for field in ("question", "target_source", "decision_test"):
            fields.append((f"next_checks[{i}].{field}", c[field], 8))
    for field, val, minimum in fields:
        text = safe_text(val, field, minimum)
        for phrase in banned:
            if phrase in text and not (case == "eia" and "不是精確產出率" in text):
                fail("CASE_SPECIFIC_PROHIBITED_CLAIM", field, "此案例的限定用語不得當作研究結論")


def validate_draft(draft: dict, catalog: dict) -> dict:
    assert_keys(draft, REQUIRED_KEYS, "draft")
    if draft["schema_version"] != "signal-r8-analysis-draft-v1":
        fail("INVALID_SCHEMA", "schema_version", "與 R8 凍結規格不符")
    case = draft["case_id"]
    if case not in CASE_NAMES:
        fail("UNKNOWN_CASE", "case_id", "不支援的來源案例")
    if draft["publication_allowed"] is not False:
        fail("PUBLICATION_DENIED", "publication_allowed", "未經人審不得發布")
    allowed = catalog["sources"][case]
    chosen: list[str] = []

    def validate_ids(ids: Any, field: str) -> list[str]:
        if not isinstance(ids, list) or not ids or len(ids) != len(set(map(str, ids))):
            fail("INVALID_FACT_IDS", field, "ID 列表不得為空、重複或錯誤型別")
        for fact_id in ids:
            if not isinstance(fact_id, str):
                fail("INVALID_FACT_IDS", field, "ID 必須為字串")
            if fact_id not in allowed:
                fail("INVALID_OR_CROSS_CASE_FACT", field, f"引用不存在或跨來源事實 ID: {fact_id}")
            chosen.append(fact_id)
        return ids

    for section, expected_type in TYPES.items():
        item = draft[section]
        assert_keys(item, CLAIM_KEYS, section)
        if item["claim_type"] != expected_type:
            fail("WRONG_CLAIM_TYPE", f"{section}.claim_type", "事實、推論、待證假說不可混淆")
        validate_ids(item["fact_ids"], f"{section}.fact_ids")
        if not isinstance(item["assumptions"], list) or not all(isinstance(a, str) for a in item["assumptions"]):
            fail("INVALID_SCHEMA", f"{section}.assumptions", "假設必須為字串列表")
        if section in {"interpretation", "impact"} and not item["assumptions"]:
            fail("MISSING_ASSUMPTIONS", f"{section}.assumptions", "推論或假說必須明列前提")
        if not isinstance(item["text"], str):
            fail("INVALID_SCHEMA", f"{section}.text", "分析內容格式錯誤")

    importance = draft["importance"]
    assert_keys(importance, {"tier", "reason", "fact_ids"}, "importance")
    if importance["tier"] not in {"高", "中", "低", "待評估"}:
        fail("INVALID_IMPORTANCE", "importance.tier", "重要程度不在規格範圍")
    validate_ids(importance["fact_ids"], "importance.fact_ids")
    if not isinstance(draft["limitations"], list) or not draft["limitations"]:
        fail("MISSING_LIMITATIONS", "limitations", "需要具體不確定性")
    checks = draft["next_checks"]
    if not isinstance(checks, list) or not 1 <= len(checks) <= 3:
        fail("MISSING_FOLLOW_UP", "next_checks", "至少提出一個可查核工作")
    for i, item in enumerate(checks):
        assert_keys(item, {"question", "target_source", "decision_test"}, f"next_checks[{i}]")
    check_authored_texts(draft)
    return {"case_id": case, "fact_refs": list(dict.fromkeys(chosen)), "checks": len(checks)}


def make_result(drafts: list[dict], catalog: dict) -> dict:
    if len(drafts) != 3 or {d.get("case_id") for d in drafts} != set(CASE_NAMES):
        fail("INCOMPLETE_CASE_SET", "drafts", "必須恰好包含三個固定案例")
    results: list[dict] = []
    for d in drafts:
        check = validate_draft(d, catalog)
        facts = catalog["sources"][d["case_id"]]
        check.update({
            "title": CASE_NAMES[d["case_id"]],
            "draft_source": "HAND_WRITTEN_MOCK_NOT_MODEL",
            "facts": [{k: facts[k] for k in check["fact_refs"]}][0],
            "analysis": copy.deepcopy(d),
            "human_approved": False,
            "independently_verified": False,
            "publication_allowed": False,
        })
        results.append(check)
    baseline = read_json(FIX / "r7_editorial_reference_scores.json")
    if baseline.get("schema_version") != "signal-r8-r7-editorial-reference-baseline-v1":
        fail("INVALID_BASELINE", "r7_editorial_reference_scores", "人工編輯基線版本不符")
    return {
        "r7_editorial_baseline_not_ai_score": baseline,
        "schema_version": "signal-r8a-offline-review-v1",
        "status": "OFFLINE_FIXTURE_CONTRACT_PASSED_NOT_EDITORIAL_APPROVAL",
        "run_mode": "OFFLINE_HAND_WRITTEN_MOCK_ONLY",
        "api_calls_attempted": 0,
        "real_ai_drafts": 0,
        "mock_drafts": len(results),
        "source_catalog_sha256": sha_file(FIX / "fact_catalog_snapshot.json"),
        "drafts_sha256": sha_file(FIX / "mock_analysis_drafts.json"),
        "case_count": len(results),
        "human_approved": False,
        "publication_allowed": False,
        "limitations": [
            "固定歷史快照，並非重新讀取網頁；未完成獨立驗證。",
            "分析文字是人工撰寫的離線測試樣本，不是 AI 模型的輸出。",
            "程式驗證結構、ID、數字字面與有限禁語；不能自動判定所有語義、因果或重要性正確性。",
            "R7 分數是人工對編輯參考報告的評價，不能當成 R8 AI 分數。",
        ],
        "cases": results,
    }


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_report(result: dict) -> str:
    cards: list[str] = []
    labels = {"observation": "核心觀察", "interpretation": "可能機制", "impact": "條件式影響"}
    type_names = {"fact": "事實索引", "inference": "推論", "hypothesis": "待證假說"}
    for c in result["cases"]:
        analysis = c["analysis"]
        facts_html = "".join(
            f'<div class="fact"><span class="fid">{esc(k)}</span><div><b>{esc(f["label"])}</b><p>{esc(f["value_display"])}</p>'
            f'<small>來源證據 {esc(f["source_evidence_id"])} · {esc(f.get("attribution"))} · <a href="{esc(f["source_url"])}" rel="noopener noreferrer" target="_blank">原始來源</a></small>'
            f'{"<small>⚠ 統計範圍待核</small>" if "範圍待核" in f["label"] or not f.get("period_as_written") else ""}</div></div>'
            for k, f in c["facts"].items()
        )
        sections = []
        for key, title in labels.items():
            block = analysis[key]
            assumptions = "".join(f"<li>{esc(a)}</li>" for a in block["assumptions"])
            sections.append(
                f'<div class="claim"><span class="tag">{esc(type_names[block["claim_type"]])}</span>'
                f'<strong>{title}</strong><p>{esc(block["text"])}</p><small>引用事實：{esc(", ".join(block["fact_ids"]))}</small>'
                f'{"<ul>" + assumptions + "</ul>" if assumptions else ""}</div>'
            )
        follow = "".join(
            '<div class="follow"><b>查核問題</b><p>' + esc(x["question"]) + '</p><b>目標來源</b><p>' + esc(x["target_source"]) + '</p><b>改變判斷的條件</b><p>' + esc(x["decision_test"]) + '</p></div>'
            for x in analysis["next_checks"]
        )
        limits = "".join(f"<li>{esc(x)}</li>" for x in analysis["limitations"])
        cards.append(f'''<section class="case" data-case="{esc(c['case_id'])}">
<h2>{esc(c['title'])} <span class="sub">{esc(c['case_id'].upper())}</span></h2>
<div class="warning">OFFLINE MOCK · 非 AI 真實輸出 · 非已查證情報 · 不得發布</div>
<h3>原始事實卡（數值由 R4 快照渲染）</h3><div class="facts">{facts_html}</div>
<h3>分析段落（人工撰寫的契約範例）</h3>{''.join(sections)}
<div class="claim"><span class="tag">重要性：{esc(analysis['importance']['tier'])}</span><strong>重要性理由</strong><p>{esc(analysis['importance']['reason'])}</p><small>引用事實：{esc(', '.join(analysis['importance']['fact_ids']))}</small></div>
<h3>資訊缺口</h3><ul>{limits}</ul><h3>具體追蹤問題</h3>{follow}
<div class="review"><h3>人工評分（此處評估 MOCK 範例，非模型成績）</h3><div class="scorefields">{''.join(f'<label>{label}<select data-score="{name}"><option value="">未評</option>'+''.join(f'<option value="{i}">{i} 分</option>' for i in range(6))+'</select></label>' for name,label in [('evidence_accuracy','證據正確性'),('analytic_depth','分析深度'),('importance_reasoning','重要性理由'),('uncertainty_disclosure','不確定性揭露'),('follow_up_usefulness','追蹤價值')])}</div>
<label class="note">審閱註記<textarea data-note placeholder="請記錄低分原因、原文核對結果與改進建議"></textarea></label>
</div></section>''')
    baseline = result["r7_editorial_baseline_not_ai_score"]
    old_scores = {item["case_id"]: item["total"] for item in baseline["rated_items"]}
    comparison = '<div class="intro"><b>R7 人工編輯參考基線（不是模型準確率）</b><p>BEA：' + esc(old_scores["bea"]) + '/25 · EIA：' + esc(old_scores["eia"]) + '/25 · arXiv：' + esc(old_scores["arxiv"]) + '/25。這些是先前對「編輯參考報告」的評分，R8-A 是人工撰寫的離線範例；不能用來計算 AI 改善幅度。</p></div>'
    page = r'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>SIGNAL R8-A｜離線深度分析契約驗收</title>
<style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0e1114;color:#e8e5dc;font:15px/1.75 system-ui,-apple-system,"Microsoft JhengHei",sans-serif}header{padding:55px 22px;background:radial-gradient(circle at 90% 10%,#493817,#121518 57%);border-bottom:1px solid #6f5b35}main{max-width:1040px;margin:0 auto;padding:28px 20px 100px}header .wrap{max-width:1040px;margin:auto}h1{font-size:32px;letter-spacing:.03em;line-height:1.3;margin:10px 0}h2{color:#f4d995;font-size:25px}h3{color:#d2b56d;margin:26px 0 12px;font-size:17px}p{margin:8px 0}small{color:#a9b0b7}a{color:#edd18c}code{color:#f4db9c}.kicker{color:#e7ba61;letter-spacing:.21em;font-size:12px}.lead{color:#c8c9cb;font-size:16px}.pill,.tag{display:inline-block;border:1px solid #9a7a36;color:#e7c477;border-radius:40px;padding:3px 10px;font-size:12px;vertical-align:middle}.intro{padding:18px;border:1px solid #5a4730;background:#211d16;border-radius:10px;margin-bottom:26px}.case{margin:28px 0;padding:28px;background:#161a1e;border:1px solid #363b3d;border-radius:16px}.sub{font-size:13px;color:#aaa}.warning{border-left:4px solid #bb8740;background:#292215;padding:10px 14px;font-size:13px;color:#efd59c}.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(285px,1fr));gap:12px}.fact{display:flex;gap:14px;align-items:flex-start;border:1px solid #45403a;border-radius:10px;padding:13px;background:#1b2024}.fact b{font-size:14px}.fact p{color:#e7c477}.fact small{display:block;word-break:break-word}.fid{font:700 13px monospace;color:#e2bd67;background:#2e2a22;padding:6px}.claim,.follow{padding:16px;margin:12px 0;background:#20252a;border-radius:9px;border:1px solid #384047}.claim strong{margin-left:10px}.claim ul{color:#b9baba}.tag{background:#272b28}.follow{border-left:3px solid #b89a58}li{margin:5px 0}.review{margin-top:26px;padding:20px;border-radius:12px;background:#24241e;border:1px solid #806b3f}.scorefields{display:grid;grid-template-columns:repeat(auto-fit,minmax(152px,1fr));gap:14px}.scorefields label{display:flex;flex-direction:column;gap:5px;color:#dcc58d}.review select,.review textarea{background:#141719;color:#fff;border:1px solid #77633f;border-radius:7px;padding:9px;width:100%;font:inherit}.note{display:block;margin-top:18px}.note textarea{height:83px;resize:vertical}.actions{position:sticky;bottom:0;background:#17191cee;border-top:1px solid #a8894d;padding:14px 20px;display:flex;justify-content:center;gap:18px;align-items:center;flex-wrap:wrap;backdrop-filter:blur(8px)}button{background:#c4a160;color:#16191a;border:0;border-radius:8px;padding:12px 19px;font-weight:bold;cursor:pointer}button:hover{background:#e7c987}.foot{color:#b3b4b6;margin-top:34px}@media print{.actions,.review{display:none!important}body{background:white;color:#222}.case{background:white;color:#222;break-inside:avoid}.claim{background:#f2f2f2;color:#222}.warning{color:#222}h2,h3{color:#444}header{background:white;color:#222}}</style></head><body>
<header><div class="wrap"><div class="kicker">SIGNAL · EVIDENCE REBUILD / R8-A</div><h1>受證據約束的深度分析<br>離線契約驗收</h1><p class="lead">三種固定歷史來源 · 十六筆事實快照 · 零 API 呼叫 · 人工撰寫模擬案例</p><span class="pill">NOT VERIFIED</span> <span class="pill">NOT AI GENERATED</span> <span class="pill">PUBLICATION BLOCKED</span></div></header>
<main><div class="intro"><b>這份報告驗證的是資料契約與呈現流程，不是模型的情報品質。</b><p>所有事實數字由程式從既有 R4 固定快照填入。模型欄位使用人工編寫的模擬分析段落。來源尚未重新抓取，也沒有獨立事實驗證；R7 的既有人工分數不會自動轉成 R8 模型成績。</p><p>測試標準：不存在或跨來源的事實 ID 拒絕；自由文字直接出現數字與禁止用語時拒絕；真實因果與語義是否合理仍必須人工核對。</p></div>
'''+comparison+"".join(cards)+r'''<div class="foot">資料快照：R4 統一事實目錄（固定歷史案例）。頁面為靜態離線文件；下方匯出僅在你的瀏覽器下載 JSON，不會上傳資料。匯出的自評不構成對外發布批准。</div></main>
<div class="actions"><span>可填寫三案品質分數，但仍屬離線範例</span><button id="export" type="button">匯出 R8-A 人工評估 JSON</button></div>
<script>
document.getElementById('export').addEventListener('click',()=>{
 const cases=[...document.querySelectorAll('section.case')].map(el=>{
  const scores={};el.querySelectorAll('[data-score]').forEach(s=>{scores[s.dataset.score]=s.value===''?null:Number(s.value)});
  return {case_id:el.dataset.case,scores,note:el.querySelector('[data-note]').value};
 });
 const result={schema_version:'signal-r8a-human-review-v1',mode:'HAND_WRITTEN_OFFLINE_MOCK_NOT_AI',created_at:new Date().toISOString(),publication_allowed:false,human_publication_approval:false,cases};
 const blob=new Blob([JSON.stringify(result,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='SIGNAL_R8A_人工評估_離線範例.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
</script></body></html>'''
    return page


def run() -> dict:
    catalog = fact_catalog()
    sample = read_json(FIX / "mock_analysis_drafts.json")
    if sample.get("fixture_type") != "HAND_WRITTEN_OFFLINE_EXAMPLES_NOT_AI_OUTPUT":
        fail("INVALID_FIXTURE_SOURCE", "fixture_type", "本階段只允許人工撰寫固定案例")
    report = make_result(sample["drafts"], catalog)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "r8a_offline_result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "r8a_offline_review.html").write_text(render_report(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="SIGNAL R8-A offline-only; no OpenAI API")
    p.add_argument("--check", action="store_true", help="Validate three fixed mock drafts and produce report")
    args = p.parse_args()
    data = run()
    print(f"PASS R8-A offline: {data['case_count']} fixed cases, {data['api_calls_attempted']} API calls, publication_allowed={data['publication_allowed']}")
    print(f"Report: {OUTPUT / 'r8a_offline_review.html'}")
