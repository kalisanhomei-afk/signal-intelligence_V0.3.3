#!/usr/bin/env python3
"""SIGNAL Evidence Rebuild R3: offline, strictly pinned MESA abstract extraction.

Purpose: test faithful machine extraction from the six snippets saved in a
user-supplied GitHub Actions artifact. No network, API, AI, peer-review check,
independent verification, data publication, or generic arXiv parsing.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA_VERSION = 'signal-facts-r3'
SOURCE_URL = 'https://arxiv.org/abs/2611.05567'
SOURCE_TITLE = 'MESA: An Evaluation Framework for Compositional, Semantic, and Spatial Generalization in Robotics'
ARCHIVE_ID = 'rss-209029a364bea7da5bf4f7'
SNIPPET_DIGESTS = {
    'E1': 'd408ce43e2a4ca402f7121e1bbac538a69af04438440c8f813e5b331682afbea',
    'E2': '566f423e0cf0b8b131270eeb393f02c751befaeca9193abbe7160738f2233564',
    'E3': '2849a9d7049213dd18aad01b82f67bee9138d83c4ef6278b27118f94cc94f7cb',
    'E4': '19ac23e57fd452ddfd01db8578a942ce869a43fdd12d46f15c91a944c9d79915',
    'E5': '295e849b23facc42b10c1c65187425cb5dfdb9bd04b9081417226d49e738ff6d',
    'E6': 'd4c06b1058b7dd18f0539a32944d40575cc2e77ca6cfd9e7a1b896d594310f07',
}

E4_PATTERN = re.compile(
    r'MESA provides (five) evaluation suites that isolate in-distribution performance '
    r'and (four) distinct axes of generalization: spatial configuration, object instance, '
    r'object category, and subtask composition, enabling researchers to diagnose '
    r'where and why policies fail, not just whether they fail\.'
)
E5_PATTERN = re.compile(
    r'We instantiate the framework on (two) platforms and release both: the '
    r'single-arm MESA suite, and BiMESA, the first large-scale benchmark for '
    r'bimanual generalization\.'
)
E6_PATTERN = re.compile(
    r'We evaluate (seven) baseline methods spanning diffusion policies, VLM-based '
    r'approaches, and pretrained VLAs, finding that the strongest model achieves '
    r'only (\d{1,3})% on MESA and (\d{1,3})% on BiMESA, providing meaningful '
    r'signal while leaving ample room for progress\.'
)
WORD_COUNTS = {'two': 2, 'four': 4, 'five': 5, 'seven': 7}


def digest(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def checked_abstract(source: dict) -> dict[str, str]:
    if not isinstance(source, dict):
        raise ValueError('Input must be a JSON object')
    item = source.get('item')
    if not isinstance(item, dict):
        raise ValueError('Source item must be an object')
    expected = {
        'id': ARCHIVE_ID, 'title': SOURCE_TITLE, 'url': SOURCE_URL,
        'publisher_id': 'arxiv', 'source_id': 'arxiv-robotics',
        'status': 'excerpts_available', 'kind': 'arxiv_api', 'body_read': False,
    }
    for key, value in expected.items():
        if item.get(key) != value:
            raise ValueError(f'Unexpected archived arXiv metadata: {key}')
    parsed = urlsplit(item['url'])
    if (parsed.scheme, parsed.hostname, parsed.path) != ('https', 'arxiv.org', '/abs/2611.05567') or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Unexpected arXiv URL')
    rows = item.get('evidence_spans')
    if not isinstance(rows, list) or len(rows) != len(SNIPPET_DIGESTS):
        raise ValueError('R3 requires exactly six pinned author-abstract snippets')
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Snippet is not an object')
        key, content = row.get('id'), row.get('text')
        if key not in SNIPPET_DIGESTS or key in result or not isinstance(content, str):
            raise ValueError('Unexpected, duplicated, or malformed snippet')
        actual_hash = digest(content)
        if actual_hash != SNIPPET_DIGESTS[key] or actual_hash != row.get('sha256'):
            raise ValueError(f'Edited or unapproved arXiv author snippet: {key}')
        result[key] = content
    if set(result) != set(SNIPPET_DIGESTS):
        raise ValueError('Missing pinned author-abstract evidence')
    return result


def _author_fact(fid: str, metric: str, role: str, raw: str, value: int,
                 unit: str, evidence_id: str, spans: dict, note: str,
                 context: str | None = None) -> dict:
    if raw not in ('two', 'four', 'five', 'seven') and not re.fullmatch(r'\d{1,3}', raw):
        raise ValueError('Unexpected value in fixed abstract')
    if value < 0 or value > 100:
        raise ValueError('Value outside R3 expected bounds')
    return {
        'fact_id': fid,
        'metric': metric,
        'measurement_role': role,
        'value_original': raw,
        'value_normalized': value,  # deterministic word->integer translation only
        'unit_original': unit,
        'source_evidence_id': evidence_id,
        'source_span_sha256': digest(spans[evidence_id]),
        'claim_attribution': 'authors_abstract_self_report',
        'independently_verified': False,
        'peer_review_confirmed': False,
        'metric_definition_verified': False if unit == 'percent (%)' else None,
        'interpretation_limit': note,
        'context': context,
    }


def _build(source: dict) -> dict:
    item = source['item']
    spans = checked_abstract(source)
    group_match = E4_PATTERN.fullmatch(spans['E4'])
    platforms_match = E5_PATTERN.search(spans['E5'])
    scores_match = E6_PATTERN.fullmatch(spans['E6'])
    if not group_match or not platforms_match or not scores_match:
        raise ValueError('Abstract wording does not match the reviewed R3 MESA grammar')
    suites_word, axes_word = group_match.groups()
    platforms_word = platforms_match.group(1)
    baselines_word, mesa_score, bimesa_score = scores_match.groups()
    if not 0 <= int(mesa_score) <= 100 or not 0 <= int(bimesa_score) <= 100:
        raise ValueError('Percent outside expected range')

    facts = [
        _author_fact('ARXIV-F001', 'mesa_evaluation_suite_count', 'authors_described_framework_design',
                     suites_word, WORD_COUNTS[suites_word], 'evaluation suites', 'E4', spans,
                     'Five suites include in-distribution performance and four generalization axes; the axes are not five extra suites.'),
        _author_fact('ARXIV-F002', 'mesa_generalization_axis_count', 'authors_described_framework_design',
                     axes_word, WORD_COUNTS[axes_word], 'generalization axes', 'E4', spans,
                     'Four axes are spatial configuration, object instance, object category, and subtask composition.'),
        _author_fact('ARXIV-F003', 'mesa_platform_count', 'authors_described_release',
                     platforms_word, WORD_COUNTS[platforms_word], 'platforms', 'E5', spans,
                     'Authors describe single-arm MESA and bimanual BiMESA; this is not a count of real-world deployments.'),
        _author_fact('ARXIV-F004', 'baseline_method_count', 'authors_described_experiment',
                     baselines_word, WORD_COUNTS[baselines_word], 'baseline methods', 'E6', spans,
                     'Seven methods reported by the authors; not an independent method comparison.'),
        _author_fact('ARXIV-F005', 'mesa_best_baseline_reported_performance', 'authors_reported_best_result',
                     mesa_score, int(mesa_score), 'percent (%)', 'E6', spans,
                     'Authors say strongest model achieves 52% on MESA; metric definition, denominator and validity not in archived abstract.',
                     context='MESA'),
        _author_fact('ARXIV-F006', 'bimesa_best_baseline_reported_performance', 'authors_reported_best_result',
                     bimesa_score, int(bimesa_score), 'percent (%)', 'E6', spans,
                     'Authors say strongest model achieves 49% on BiMESA; do NOT relabel as accuracy or task-success rate.',
                     context='BiMESA'),
    ]
    return {
        'schema_version': SCHEMA_VERSION,
        'publication_allowed': False,
        'human_approved': False,
        'review_status': 'authors_abstract_only_not_peer_reviewed_or_independently_verified',
        'source': {
            'publisher_id': 'arxiv',
            'source_id': 'arxiv-robotics',
            'source_url': SOURCE_URL,
            'source_title': SOURCE_TITLE,
            'source_rss_published_at': item.get('published_at'),
            'source_archived_retrieved_at': item.get('retrieved_at'),
            'source_kind': 'arxiv_author_abstract_snippets_not_full_paper',
            'excerpt_sha256': {key: digest(spans[key]) for key in sorted(spans)},
            'rights_note': 'User-provided private artifact excerpt only; internal offline validation',
        },
        'facts': facts,
        'claim_groups': [
            {'kind': 'benchmark_design', 'suite_count_fact_id': 'ARXIV-F001',
             'axis_count_fact_id': 'ARXIV-F002',
             'axes_as_written': ['spatial configuration', 'object instance', 'object category', 'subtask composition'],
             'author_explains_in_distribution': True},
            {'kind': 'benchmark_platforms', 'platform_count_fact_id': 'ARXIV-F003',
             'platform_labels': ['single-arm MESA', 'BiMESA (bimanual)']},
            {'kind': 'baseline_results', 'baseline_count_fact_id': 'ARXIV-F004',
             'mesa_result_fact_id': 'ARXIV-F005', 'bimesa_result_fact_id': 'ARXIV-F006',
             'metric_name': 'not_specified_in_archived_abstract',
             'denominator': 'not_specified_in_archived_abstract',
             'winner_identity': 'not_specified_in_archived_abstract'},
        ],
        'qualitative_author_claims_not_verified': [
            {'evidence_id': 'E3', 'claim': 'MESA introduced as an evaluation framework', 'status': 'author_stated'},
            {'evidence_id': 'E5', 'claim': 'BiMESA described as the first large-scale benchmark for bimanual generalization',
             'status': 'priority_claim_not_independently_verified'},
        ],
        'raw_excerpts': [{'id': key, 'text': spans[key]} for key in sorted(spans)],
        'audit': [
            'Fixed arXiv abstract excerpts are author self-reports, not independently confirmed experimental results',
            'Reported 52% and 49% must not be called success rate, accuracy, or validated deployment performance',
            'Five evaluation suites consist of in-distribution plus four generalization axes, not nine suites',
            'Two experimental platforms must not be recast as two production robots, clients or sites',
            'The abstract does not establish peer-review status, metric denominator, CI, benchmark difficulty or external replication',
            'Source snippet hashes protect archived-fixture consistency only; no fresh original-source verification',
            'No AI/API calls, network requests, background work, paid use or website publication',
        ],
    }


def extract(source: dict) -> dict:
    result = _build(source)
    validate(result, source)
    return result


def validate(bundle: dict, source: dict) -> None:
    if bundle != _build(source):
        raise ValueError('Output differs from pinned author evidence; refuse edits, added facts or auto-approval')


def render_html(bundle: dict) -> str:
    if bundle.get('publication_allowed') is not False or bundle.get('human_approved') is not False:
        raise ValueError('Unapproved R3 report cannot show published/approved status')
    esc = lambda x: html.escape(str(x), quote=True)
    trs = []
    for f in bundle['facts']:
        ctx = f['context'] or '—'
        value = f"{f['value_original']} → {f['value_normalized']} {f['unit_original']}"
        trs.append('<tr>' + ''.join(f'<td>{esc(x)}</td>' for x in (
            f['fact_id'], f['metric'], f['measurement_role'], value, ctx,
            f['source_evidence_id'], f['interpretation_limit']
        )) + '</tr>')
    extracts = ''.join(
        f'<details><summary>{esc(s["id"])}｜作者摘要摘錄</summary><p>{esc(s["text"])}</p></details>'
        for s in bundle['raw_excerpts']
    )
    url = esc(bundle['source']['source_url'])
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGNAL｜R3 arXiv 作者摘要證據對照</title>
<style>body{{max-width:1220px;margin:auto;padding:30px;background:#101721;color:#f1eddf;font:15px/1.75 system-ui,"Microsoft JhengHei",sans-serif}}h1,h2{{color:#d8b46d}}h1{{font-size:28px}}article{{background:#1b2938;padding:23px;margin:20px 0;border:1px solid #42546a;border-radius:12px}}a{{color:#eac77d}}.warning{{background:#3b2c24;border-left:5px solid #efbc68;padding:16px}}table{{width:100%;border-collapse:collapse;font-size:13px}}td,th{{padding:10px 8px;border-bottom:1px solid #45566d;vertical-align:top;text-align:left}}th{{color:#e9c47b}}details{{padding:8px;border-bottom:1px solid #485467}}summary{{cursor:pointer;color:#e9c47b}}@media(max-width:850px){{table{{display:block;overflow-x:auto}}}}@media print{{body{{background:white;color:black}}article{{background:white;color:black}}a{{color:#483311}}}}</style></head><body>
<h1>視界 SIGNAL｜Evidence Rebuild R3</h1>
<p class="warning"><strong>僅供離線驗收｜不可發布</strong>　此頁保留 arXiv 論文的<strong>作者摘要自述</strong>，不是全文閱讀、同儕審查證明、研究成果獨立驗證或投資訊號。未呼叫 AI/API。</p>
<article><h2>研究來源</h2><p>論文：{esc(bundle['source']['source_title'])}</p><p><a href="{url}" target="_blank" rel="noopener noreferrer">arXiv 原始頁面 ↗</a>（本次離線測試未重新連線）</p><p>資料：使用先前 GitHub Actions 保存的 E1–E6 作者摘要摘錄；hash 只用於確認沒有更改儲存的摘錄，不代表真實性或可重現性已經證明。</p></article>
<article><h2>結構化待核對資訊（6 項）</h2><table><thead><tr><th>Fact ID</th><th>量化項目</th><th>資料角色</th><th>來源文字 → 整理</th><th>範圍</th><th>證據</th><th>限制</th></tr></thead><tbody>{''.join(trs)}</tbody></table></article>
<article><h2>必須保留的研究語義</h2><p><strong>研究設計：</strong>作者描述 5 個 evaluation suites：1 個 in-distribution 評估，及 4 個泛化軸（空間配置、物件實例、物件類別、子任務組合）。不能誤寫成 5＋4＝9 個 suite。</p><p><strong>方法：</strong>摘要稱評估了 7 種基準方法；作者描述 2 個平台：單臂 MESA、雙臂 BiMESA。</p><p><strong>研究結果：</strong>摘要所述最佳模型為 MESA 52%、BiMESA 49%。摘要沒有足夠資訊讓我們確認這兩個百分比的測量定義、分母、統計信賴程度、泛化效果或實際場域表現；不得稱為「準確率」或「成功率」。</p><p><strong>宣稱限制：</strong>「第一個大規模雙臂泛化基準」是作者提出的優先性宣稱，目前未獨立比對文獻。</p></article>
<article><h2>保存的作者摘要摘錄 E1–E6</h2>{extracts}</article>
<article><h2>人工品質驗收</h2><p>□ 摘錄與原文一致　□ 五個 suite 的分類沒有誤讀　□ 兩種平台概念準確　□ 七種方法與比較條件需查閱全文</p><p>□ 52%/49% 的精確指標與分母尚待論文全文確認　□ 不把作者主張稱為已驗證研究　□ 仍不得上線發布</p></article></body></html>'''


def main() -> None:
    ap = argparse.ArgumentParser(description='OFFLINE pinned arXiv author abstract R3; NO AI or network')
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--report', required=True)
    args = ap.parse_args()
    source = json.loads(Path(args.input).read_text(encoding='utf-8'))
    result = extract(source)
    output, report = Path(args.output), Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    report.write_text(render_html(result), encoding='utf-8')
    print(f"PASS R3: {len(result['facts'])} author-attributed records; no AI, no web, publication_allowed=false")


if __name__ == '__main__':
    main()
