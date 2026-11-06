#!/usr/bin/env python3
"""SIGNAL Evidence Rebuild R1: offline only; one preapproved BEA evidence span.

No API calls, scraping, GitHub Actions, secret handling, or publishing.
Facts are emitted from exact, versioned source excerpts; AI has NO authority
here to originate numeric facts. This is a proof of architecture, not a
production-grade extractor for arbitrary economic statements.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA_VERSION = "signal-facts-r1"
APPROVED_URL = "https://www.bea.gov/news/2026/us-international-trade-goods-and-services-september-2026"
MONTHS = "January February March April May June July August September October November December".split()
DECIMAL = r"(\d+(?:\.\d+)?)"
PATTERN = re.compile(
    rf"^The deficit with Taiwan increased \${DECIMAL} billion to \${DECIMAL} billion in ({'|'.join(MONTHS)})\. "
    rf"Exports increased \${DECIMAL} billion to \${DECIMAL} billion and "
    rf"imports increased \${DECIMAL} billion to \${DECIMAL} billion\.$"
)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fact(code: str, metric: str, typ: str, value: str, source_text: str, source_eid: str):
    assert re.fullmatch(DECIMAL, value)
    return {"fact_id":code,"metric":metric,"measurement_role":typ,
            "value_original":value,"unit_original":"USD billion",
            "source_evidence_id":source_eid,"source_span_sha256":digest(source_text),
            "source_verification":"excerpt_exact_match_only_not_independently_verified"}


def extract(data: dict) -> dict:
    """Fail closed: do not infer facts from unmatched, unreviewed formats."""
    item = data["item"]
    if (item.get("publisher_id") != "bea" or item.get("url") != APPROVED_URL
        or item.get("source_id") != "bea-news"):
        raise ValueError("Source not explicitly allowlisted for R1")
    url = urlsplit(item["url"])
    if url.scheme != "https" or url.hostname != "www.bea.gov":
        raise ValueError("Unapproved URL")
    rows = item.get("evidence_spans", [])
    if len(rows) != 1 or rows[0].get("id") != "E7":
        raise ValueError("R1 requires exactly the reviewed BEA E7 excerpt")
    evidence = rows[0]
    text = evidence["text"]
    if not isinstance(text, str) or evidence.get("sha256") != digest(text):
        raise ValueError("Source excerpt checksum mismatch")
    m = PATTERN.fullmatch(text)
    if not m:
        raise ValueError("Unmatched prose: no facts emitted; needs human schema review")
    deficit_delta, deficit_total, month, exports_delta, exports_total, imports_delta, imports_total = m.groups()
    values = [
        ("F001", "taiwan_reported_deficit", "current_level", deficit_total),
        ("F002", "taiwan_reported_deficit", "increase", deficit_delta),
        ("F003", "reported_exports", "current_level", exports_total),
        ("F004", "reported_exports", "increase", exports_delta),
        ("F005", "reported_imports", "current_level", imports_total),
        ("F006", "reported_imports", "increase", imports_delta),
    ]
    facts = [_fact(*v, text, "E7") for v in values]
    out = {
        "schema_version": SCHEMA_VERSION,
        "publication_allowed": False,
        "human_approved": False,
        "review_status": "machine_extracted_requires_human_crosscheck",
        "source": {
            "publisher_id": "bea", "source_id": "bea-news", "source_url": item["url"],
            "source_title": item["title"], "source_published_at": item["published_at"],
            "excerpt_id": "E7", "excerpt_sha256": digest(text), "period_as_written": month,
            "period_year_in_excerpt": None,
            "rights_note": "Excerpt supplied in existing SIGNAL user test artifact; review before further redistribution"
        },
        "facts": facts,
        "claim_groups": [
            {"kind":"increased_to","subject":"taiwan_reported_deficit","amount":"F001","change":"F002"},
            {"kind":"increased_to","subject":"reported_exports","amount":"F003","change":"F004"},
            {"kind":"increased_to","subject":"reported_imports","amount":"F005","change":"F006"},
        ],
        "raw_excerpt": text,
        "audit": [
            "No inferred base-period values, percentage changes, exchange conversions or market impact",
            "'reported_exports/imports' are context-bound to excerpt E7; geographic/basis scope needs human review",
            "The excerpt mentions September without a year: metadata year is separate and not promoted into excerpt facts",
            "Citation IDs identify excerpts; they do not prove independent verification"
        ]
    }
    validate(out, data)
    return out


def validate(bundle: dict, evidence: dict) -> None:
    if bundle.get("publication_allowed") is not False or bundle.get("human_approved") is not False:
        raise ValueError("No automatic approval in R1")
    if bundle.get("schema_version") != SCHEMA_VERSION: raise ValueError("Invalid schema")
    source = bundle["source"]
    if source.get("source_url") != APPROVED_URL or source.get("period_year_in_excerpt") is not None:
        raise ValueError("Source scope elevated")
    row = evidence["item"]["evidence_spans"][0]
    if source["excerpt_sha256"] != digest(row["text"]):
        raise ValueError("Evidence changed")
    check = PATTERN.fullmatch(row["text"])
    if not check: raise ValueError("Evidence no longer matches")
    # Rebuild exact expected facts from source, making values impossible to change by 'review' JSON.
    expected = [
        ("F001", "taiwan_reported_deficit", "current_level", check.group(2)),
        ("F002", "taiwan_reported_deficit", "increase", check.group(1)),
        ("F003", "reported_exports", "current_level", check.group(5)),
        ("F004", "reported_exports", "increase", check.group(4)),
        ("F005", "reported_imports", "current_level", check.group(7)),
        ("F006", "reported_imports", "increase", check.group(6)),
    ]
    expected_facts = [_fact(*entry, row["text"], "E7") for entry in expected]
    if bundle.get("facts") != expected_facts:
        raise ValueError("Fact value, unit, direction, evidence ID or hash tampered")
    if source.get("period_as_written") != check.group(3): raise ValueError("Period mismatch")


def validate_analysis(draft: dict, facts: dict) -> dict:
    """For future AI use: free text is a hypothesis and cannot contain numeric claims.

    Any numerical display must come from fact IDs rendered by the program.
    This is only a local mock contract: no model is called here.
    """
    if set(draft) != {"priority","focus_fact_ids","hypothesis","unknowns"}:
        raise ValueError("Unexpected model fields")
    if draft["priority"] not in {"先讀", "追蹤", "一般", "資料不足"}:
        raise ValueError("Invalid priority label")
    ids = {x["fact_id"] for x in facts["facts"]}
    selected = draft["focus_fact_ids"]
    if not isinstance(selected, list) or len(selected) > 6 or len(selected) != len(set(selected)) or not set(selected) <= ids:
        raise ValueError("Unknown or duplicate fact IDs")
    for field in ["hypothesis", "unknowns"]:
        value = draft[field]
        if not isinstance(value, str) or not 1 <= len(value) <= 250:
            raise ValueError("Empty or oversized draft field")
        if re.search(r"\d|[０-９]", value):
            raise ValueError("AI-created digit in free text; numerical claims must use fact IDs")
    if not any(draft["hypothesis"].startswith(x) for x in ["若", "如果", "假設", "待確認"]):
        raise ValueError("Hypothesis is not explicitly conditional")
    return draft


def render_html(bundle: dict, draft: dict|None = None) -> str:
    lookup = {"taiwan_reported_deficit": "來源所述對台逆差", "reported_exports": "來源段落所述出口", "reported_imports": "來源段落所述進口"}
    roles = {"current_level":"該期數值", "increase":"增加額"}
    rows = "".join(f'<tr><td>{x["fact_id"]}</td><td>{lookup[x["metric"]]}－{roles[x["measurement_role"]]}</td><td><code>{html.escape(x["value_original"])} USD billion</code></td><td>E7（待核對）</td></tr>' for x in bundle["facts"])
    url = html.escape(bundle["source"]["source_url"], quote=True)
    extra = ""
    if draft:
        selected = ', '.join(draft["focus_fact_ids"])
        extra = f'<section><h2>條件式 AI／模擬分析草稿（未查證）</h2><p>初篩：{html.escape(draft["priority"])}；引用事實編號：{html.escape(selected)}</p><p>假說：{html.escape(draft["hypothesis"])}</p><p>未知：{html.escape(draft["unknowns"])}</p></section>'
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>SIGNAL Evidence Rebuild R1｜離線審核</title><style>body{{max-width:1100px;margin:auto;padding:32px;font-family:system-ui;line-height:1.6;background:#101721;color:#ece7d9}}h1{{color:#d0ad68}}section{{background:#202a38;padding:22px;border-radius:10px;margin:16px 0}}a{{color:#d3bb89}}table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #495161;padding:10px;text-align:left}}code{{color:#e9bf7a}}.warn{{border-left:3px solid #d2a657;padding:12px;background:#34302b}}@media print{{body{{background:white;color:black}}section{{background:#fafafa}}}}</style></head><body><h1>SIGNAL｜證據重建 R1 · 離線人工審閱</h1><p class="warn">只完成程式式數值擷取與校驗，並非來源事實已獲獨立驗證。禁止自動發佈／交易用途。</p><section><h2>來源</h2><p>{html.escape(bundle["source"]["source_title"])}</p><p><a href="{url}" target="_blank" rel="noopener noreferrer">前往 BEA 原始公告 ↗</a></p><p>段落：E7；來源段落月份：{html.escape(bundle["source"]["period_as_written"])}；來源段落未直接提供年份。</p></section><section><h2>程式擷取的待審事實</h2><table><tr><th>ID</th><th>原始指標（待釐清統計範圍）</th><th>原文數值和單位</th><th>來源</th></tr>{rows}</table></section>{extra}<section><h2>人工驗收</h2><p>□ 已在官方原文再次核對 E7 與摘錄一致</p><p>□ 確認 exports/imports 的統計範圍與對象</p><p>□ 確認統計基準、期間、單位、是否修訂</p><p>□ 模型假說與證據分離，數字由程式插入</p><p>□ 未經人工核准不得進入正式「今日情報」</p></section></body></html>'''


def main():
    ap = argparse.ArgumentParser(description="Offline SIGNAL fact extraction R1, no network/API")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    evidence = json.loads(Path(args.input).read_text(encoding="utf-8"))
    facts = extract(evidence)
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(facts,ensure_ascii=False,indent=2),encoding="utf-8")
    report = Path(args.report); report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(render_html(facts),encoding="utf-8")
    print(f"PASS: {len(facts['facts'])} original numeric facts from BEA E7; publication_allowed=false; paid_calls=0")

if __name__ == "__main__":
    main()
