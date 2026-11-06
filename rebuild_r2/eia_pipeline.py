#!/usr/bin/env python3
"""SIGNAL Evidence Rebuild R2 — reproducible offline EIA *fixed-excerpt* parser.

This is a deliberately constrained proof of concept for two previously stored
EIA excerpts. It does NOT fetch websites, infer additional figures, call an API,
verify the original website, or publish content. Fail closed for any new format.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA_VERSION = 'signal-facts-r2'
SOURCE_URL = 'https://www.eia.gov/todayinenergy/detail.php?id=68424'
# The hashes pin the *specific two user-supplied, previously archived snippets*.
# They do not constitute independent confirmation of their content.
SNIPPET_DIGESTS = {
    'E2': '453d6eca6f97b3fb4fd69abd09213f9da568a28ccb96a06f403ca53a0aa0429b',
    'E5': '07dd3138cf25e66f8c5582020a36449a8aa8ce402b475f31457350adbbfba48d',
}
MONTH = ('January February March April May June July August September '
         'October November December').split()
M = '(?:' + '|'.join(MONTH) + ')'
RANGE = re.compile(
    r'The U\.S\. refining fleet tends to have a strong refinery yield of '
    r'gasoline—typically between (\d{1,3})%–(\d{1,3})%\.'
)
JET = re.compile(
    r'The U\.S\. refinery fleet exceeded an average jet fuel yield of '
    rf'(\d{{1,3}})% for the first time in ({M}) (\d{{4}}), according to EIA data\. '
    r'Since then, the fleetwide average jet fuel yield has remained at or '
    rf'above (\d{{1,3}})% through the latest Petroleum Supply Monthly data for ({M}) (\d{{4}})\.'
)


def digest(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def checked_excerpt(source: dict) -> dict:
    item = source.get('item', {})
    if not isinstance(item, dict):
        raise ValueError('Source item is not an object')
    url = item.get('url')
    if (item.get('publisher_id'), item.get('source_id'), url) != ('eia', 'eia-energy', SOURCE_URL):
        raise ValueError('R2 source is not in fixed EIA allowlist')
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.hostname != 'www.eia.gov' or parts.username or parts.password:
        raise ValueError('Invalid EIA source URL')
    if item.get('status') != 'excerpts_available' or item.get('kind') != 'html' or item.get('body_read') is not True:
        raise ValueError('Archived excerpt was not marked as retrieved source content')
    spans = item.get('evidence_spans')
    if not isinstance(spans, list) or len(spans) != 2 or {x.get('id') for x in spans if isinstance(x,dict)} != set(SNIPPET_DIGESTS):
        raise ValueError('Exactly the previously reviewed E2 and E5 are required')
    result = {}
    for row in spans:
        if not isinstance(row,dict):
            raise ValueError('Invalid excerpt row')
        key, body = row.get('id'), row.get('text')
        if not isinstance(body, str) or digest(body) != row.get('sha256') or digest(body) != SNIPPET_DIGESTS[key]:
            raise ValueError(f'Edited or unapproved excerpt: {key}')
        result[key] = body
    return result


def _fact(fid: str, metric: str, role: str, val: str, evidence_id: str,
          period: str | None, note: str, excerpts: dict) -> dict:
    if not re.fullmatch(r'\d{1,3}',val):
        raise ValueError('Unapproved number token')
    return {
        'fact_id': fid, 'metric': metric, 'measurement_role': role,
        'value_original': val, 'unit_original': 'percent (%)',
        'period_as_written': period, 'qualifier': note,
        'source_evidence_id': evidence_id,
        'source_span_sha256': digest(excerpts[evidence_id]),
        'source_verification': 'archived_excerpt_pattern_match_only_not_independently_verified',
    }


def _build(source: dict) -> dict:
    item = source['item']
    excerpts = checked_excerpt(source)
    range_match = RANGE.search(excerpts['E2'])
    jet_match = JET.search(excerpts['E5'])
    if range_match is None or jet_match is None:
        raise ValueError('Source wording not covered by R2 reviewed parsing rules')
    gasoline_low, gasoline_high = map(int, range_match.groups())
    first_threshold, first_month, first_year, continuing_threshold, last_month, last_year = jet_match.groups()
    if not (0 <= gasoline_low < gasoline_high <= 100):
        raise ValueError('Invalid gasoline yield bounds')
    if not (0 < int(first_threshold) <= 100 and first_threshold == continuing_threshold):
        raise ValueError('Contradictory jet fuel threshold')
    if not (MONTH.index(last_month) + 12 * int(last_year) >= MONTH.index(first_month) + 12 * int(first_year)):
        raise ValueError('Invalid source period ordering')
    period_first, period_end = f'{first_month} {first_year}', f'{last_month} {last_year}'
    facts = [
        _fact('EIA-F001','us_refinery_motor_gasoline_yield','typical_range_lower_bound',str(gasoline_low),'E2',None,
              'Typical range reported by this article; not an observed value for a specific month',excerpts),
        _fact('EIA-F002','us_refinery_motor_gasoline_yield','typical_range_upper_bound',str(gasoline_high),'E2',None,
              'Typical range reported by this article; not an observed value for a specific month',excerpts),
        _fact('EIA-F003','us_refinery_jet_fuel_yield','first_exceeded_threshold',first_threshold,'E5',period_first,
              'Threshold exceeded; actual March yield not provided in excerpt',excerpts),
        _fact('EIA-F004','us_refinery_jet_fuel_yield','continued_at_or_above_threshold',continuing_threshold,'E5',
              f'{period_first} through {period_end}',
              'Threshold sustained in reported monthly data through named ending month',excerpts),
    ]
    return {
        'schema_version': SCHEMA_VERSION,
        'publication_allowed': False,
        'human_approved': False,
        'review_status': 'machine_extracted_from_archived_snippets_requires_human_confirmation',
        'source': {
            'publisher_id': 'eia', 'source_id': 'eia-energy', 'source_url': SOURCE_URL,
            'source_title': item.get('title'), 'source_published_at': item.get('published_at'),
            'source_archived_retrieved_at': item.get('retrieved_at'),
            'excerpt_sha256': {k: digest(v) for k,v in excerpts.items()},
            'rights_note': 'Archived in user-provided GitHub Actions artifact; excerpts for internal offline validation only',
        },
        'facts': facts,
        'claim_groups': [
            {'kind':'typical_range','metric':'us_refinery_motor_gasoline_yield',
             'low_fact_id':'EIA-F001','high_fact_id':'EIA-F002'},
            {'kind':'threshold_history','metric':'us_refinery_jet_fuel_yield',
             'first_exceeded_fact_id':'EIA-F003','continued_minimum_fact_id':'EIA-F004'},
        ],
        'raw_excerpts': [{'id':k, 'text':excerpts[k]} for k in ('E2','E5')],
        'audit': [
            'E2 only reports a typical gasoline yield range, not current monthly production',
            'E5 reports thresholds; 12% is not an observed exact March or August jet-fuel yield',
            'Do not infer fuel prices, future refinery yields, measured jet-fuel output or causal effect sizes',
            'Source IDs and checksums give traceability only; no live independent confirmation was performed',
            'No AI calls, no site publication, no external requests',
        ],
    }


def extract(source: dict) -> dict:
    result = _build(source)
    validate(result, source)
    return result


def validate(bundle: dict, source: dict) -> None:
    # Build the only allowed entire bundle directly from the pinned archived excerpts.
    # Prevents tampering with the original numbers, unit, periods, evidence ID,
    # approval status, citation anchors or report claims.
    if bundle != _build(source):
        raise ValueError('Output differs from pinned excerpt facts; no auto-approval or value rewriting')


def render_html(bundle: dict) -> str:
    validate_safe = bundle.get('publication_allowed') is False and bundle.get('human_approved') is False
    if not validate_safe:
        raise ValueError('Refuse rendering approved/publication status in offline R2')
    table = []
    for fact in bundle['facts']:
        table.append('<tr>' + ''.join(
            f'<td>{html.escape(str(v))}</td>' for v in [
                fact['fact_id'],fact['metric'],fact['measurement_role'],
                f"{fact['value_original']} {fact['unit_original']}",
                fact['period_as_written'] or '未明示單月',fact['source_evidence_id'],
                fact['qualifier']]) + '</tr>')
    escaped_url = html.escape(bundle['source']['source_url'],quote=True)
    evidence_html = ''.join('<details><summary>' + html.escape(row['id']) + '</summary><p>'
        + html.escape(row['text']) + '</p></details>' for row in bundle['raw_excerpts'])
    return '''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>SIGNAL Evidence Rebuild R2 · EIA 離線審核</title>
<style>body{max-width:1200px;margin:0 auto;padding:28px;background:#101721;color:#f0eadb;font:15px/1.75 system-ui,sans-serif}h1{color:#dbb66e}article{background:#1c2938;border:1px solid #46556a;border-radius:10px;padding:22px;margin:18px 0}a{color:#d5b778}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #556070;text-align:left;vertical-align:top}th{color:#e7c47c}.warning{padding:14px;border-left:4px solid #e3b04d;background:#3a2e22}summary{cursor:pointer;color:#e7c47c}@media print{body{background:white;color:black}article{background:white;color:black}}</style></head><body><h1>視界 SIGNAL｜Evidence Rebuild R2</h1>
<p class="warning"><strong>離線實驗，不是已查證情報。</strong>僅擷取固定 EIA 摘錄中的數字關係；不可自動發佈，也未啟用 AI。</p>
<article><h2>來源與範圍</h2><p><a href="''' + escaped_url + '''" target="_blank" rel="noopener noreferrer">EIA 原始文章 ↗</a></p><p>只使用先前 GitHub Actions Artifact 的 E2 與 E5，未重新擷取網站。來源段落保存校驗碼，但不等於獨立佐證。</p></article>
<article><h2>待人工核對的結構化事實</h2><table><tr><th>Fact ID</th><th>指標</th><th>數值角色</th><th>原始數值與單位</th><th>時間</th><th>摘錄</th><th>限制</th></tr>''' + ''.join(table) + '''</table></article>
<article><h2>原始摘錄（內部測試）</h2>''' + evidence_html + '''</article>
<article><h2>關鍵誤讀防護</h2><p>汽油 45%–50% 是文中所述「典型範圍」，不是 2026 年 8 月觀測值。航空燃油 12% 是門檻：3 月首次高於該門檻，直到 8 月每月維持至少該門檻；不能把兩者寫成精確測量值。</p></article>
<article><h2>人工驗收（全部勾選前不可發佈）</h2><p>□ E2／E5 與 EIA 原文一致　□ 汽油數值是典型值而非當月值　□ 航空燃油是門檻而非確切測值</p><p>□ 明確區分數據期間　□ 單位和定義已核對　□ 尚無跨機構獨立佐證　□ 不自動產生市場與價格推論</p></article></body></html>'''


def main() -> None:
    ap = argparse.ArgumentParser(description='Offline EIA fixed-evidence extraction; NO API / NO network')
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--report', required=True)
    opt = ap.parse_args()
    data = json.loads(Path(opt.input).read_text(encoding='utf-8'))
    facts = extract(data)
    output, report = Path(opt.output), Path(opt.report)
    output.parent.mkdir(parents=True,exist_ok=True); report.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report.write_text(render_html(facts),encoding='utf-8')
    print(f"PASS R2: {len(facts['facts'])} anchored fact records, 2 pinned excerpts, paid_calls=0, publication_allowed=false")

if __name__ == '__main__':
    main()
