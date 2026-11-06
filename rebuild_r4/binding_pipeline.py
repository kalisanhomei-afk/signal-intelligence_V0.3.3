#!/usr/bin/env python3
"""SIGNAL Evidence Rebuild R4: offline AI selection => code-rendered facts.

R4 has no model call. All numerical claims rendered to users are composed by
trusted code from R1/R2/R3 extracted fixtures. The hypothetical model output is
STRICTLY a selection of source-local IDs and approved analysis themes.

Limitation: selected themes are qualitative hypotheses, not independently
verified conclusions. This is a constrained mock contract, not a production LLM.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
from pathlib import Path

SCHEMA_VERSION = 'signal-rebuild-bound-review-r4'
SELECTION_VERSION = 'signal-analysis-selection-r4'
REQUIRED_CASES = ('bea', 'eia', 'arxiv')
BEA_PINNED_E7_SHA256 = 'b82a1000d2506b6faaa86cb70f0b2078a426ca49d1592516b469306906fe02f7'

THEMES = {
    'bea': {
        'trade_structure_monitor': '若相關貿易結構變化持續，值得核對統計定義、主要商品與其他月份的比較；不能僅由這段摘錄推論原因。',
        'trade_policy_watch': '這段統計可作為後續政策研究的線索，但不能直接證明政策改變已發生或由此數據造成。',
    },
    'eia': {
        'refinery_yield_mix': '可追蹤煉油廠產品組合的變化；典型範圍與門檻描述不是當月精確測值。',
        'fuel_price_risk': '產出結構可能是研究供需的重要線索，但現有摘錄不足以推定油價方向或漲跌幅。',
    },
    'arxiv': {
        'robotics_generalization_gap': '作者的研究結果可能有助於辨識泛化能力瓶頸，但指標定義與外部可重現性仍需閱讀全文確認。',
        'benchmark_interpretation': '評估設計可作為未來研究的參考，惟摘要中的報告百分比不等於已驗證的準確率或實場成功率。',
    },
}
QUESTIONS = {
    'bea': {
        'compare_periods': '能否從官方完整統計表核對前期與修訂值？',
        'check_scope': '出口與進口的地理範圍及統計口徑為何？',
        'confirm_drivers': '變化涉及哪些商品類別？目前尚不能判斷原因。',
    },
    'eia': {
        'find_actual_monthly_yields': '官方月度原始表中的汽油與航空燃油實際產出率為何？',
        'check_duration': '這項產品結構變化是否延續至後續月份？',
        'check_driver': '若要評估價格影響，還需要哪些供需和利潤數據？',
    },
    'arxiv': {
        'read_metric_definition': '論文全文如何定義報告百分比、評估分母與統計不確定性？',
        'check_reproduction': '評估方法與實驗結果是否有獨立重現或同儕審查？',
        'compare_baselines': '不同方法的比較是否控制了任務難度與訓練資料差異？',
    },
}
LABELS = {
    'taiwan_reported_deficit': '對台灣的文中貿易逆差',
    'reported_exports': '文中出口金額（範圍待核）',
    'reported_imports': '文中進口金額（範圍待核）',
    'us_refinery_motor_gasoline_yield': '美國煉油廠汽油產出率',
    'us_refinery_jet_fuel_yield': '美國煉油廠航空燃油產出率',
    'mesa_evaluation_suite_count': 'MESA 評估套件數量（作者自述）',
    'mesa_generalization_axis_count': 'MESA 泛化評估軸數量（作者自述）',
    'mesa_platform_count': 'MESA／BiMESA 平台數量（作者自述）',
    'baseline_method_count': '比較基準方法數量（作者自述）',
    'mesa_best_baseline_reported_performance': 'MESA 作者報告的最佳模型表現',
    'bimesa_best_baseline_reported_performance': 'BiMESA 作者報告的最佳模型表現',
}
CASE_TITLES = {'bea':'BEA｜貿易統計', 'eia':'EIA｜煉油廠能源資料', 'arxiv':'arXiv｜機器人研究作者摘要'}


def _root(path: str | Path | None = None) -> Path:
    return Path(path).resolve() if path is not None else Path(__file__).resolve().parent.parent


def _load_py(path: Path, unique_name: str):
    if not path.is_file():
        raise ValueError(f'Prerequisite R1/R2/R3 module missing: {path}')
    spec = importlib.util.spec_from_file_location(unique_name, path)
    if spec is None or spec.loader is None:
        raise ValueError('Unable to read prerequisite Python source')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_verified_bundles(root: Path) -> dict:
    """Re-extract from pinned fixtures, NOT user editable out/*.json files."""
    cfg = {
        'bea': ('rebuild_r1', 'fact_pipeline.py', 'bea_e7.json'),
        'eia': ('rebuild_r2', 'eia_pipeline.py', 'eia_yields_e2_e5.json'),
        'arxiv': ('rebuild_r3', 'arxiv_pipeline.py', 'arxiv_mesa_abstract_e1_e6.json'),
    }
    bundles = {}
    for key, (directory, filename, fixture) in cfg.items():
        base = root / directory
        mod = _load_py(base / filename, f'signal_r4_{key}_extraction')
        src_path = base / 'fixtures' / fixture
        if not src_path.is_file():
            raise ValueError(f'Missing original fixture: {src_path}')
        source = json.loads(src_path.read_text(encoding='utf-8'))
        if key == 'bea':
            # R1 validates SHA against fixture, but does not pin it to a hard-coded
            # digest. R4 additionally pins the originally archived E7 content.
            e7 = source['item']['evidence_spans'][0]
            if hashlib.sha256(e7['text'].encode('utf-8')).hexdigest() != BEA_PINNED_E7_SHA256:
                raise ValueError('BEA archived E7 changed; reject even if fixture SHA updated')
        bundle = mod.extract(source)
        mod.validate(bundle, source)
        if bundle.get('publication_allowed') is not False or bundle.get('human_approved') is not False:
            raise ValueError(f'Automatic approval prohibited for {key}')
        facts = bundle.get('facts')
        if not isinstance(facts, list) or not facts:
            raise ValueError(f'No facts for {key}')
        if len({f['fact_id'] for f in facts}) != len(facts):
            raise ValueError(f'Duplicate fact IDs in {key}')
        bundles[key] = bundle
    return bundles


def fact_value(case: str, fact: dict) -> str:
    """Only the PROGRAM can render numerals, never the AI selection."""
    value = fact['value_normalized'] if case == 'arxiv' else fact['value_original']
    if case == 'bea':
        role = {'current_level':'本期', 'increase':'較前期增加'}.get(fact['measurement_role'])
        if role is None: raise ValueError('Unknown BEA measurement role')
        return f'{role} {value} billion USD（原始單位）'
    if case == 'eia':
        role = fact['measurement_role']
        if role == 'typical_range_lower_bound': return f'典型範圍下界 {value}%（不是當月實測值）'
        if role == 'typical_range_upper_bound': return f'典型範圍上界 {value}%（不是當月實測值）'
        if role == 'first_exceeded_threshold': return f'首次超過 {value}%（不是精確測值）'
        if role == 'continued_at_or_above_threshold': return f'持續至少 {value}%（不是精確測值）'
        raise ValueError('Unknown EIA measurement role')
    if case == 'arxiv':
        u = fact['unit_original']
        if u == 'percent (%)':
            return f'{value}%（作者摘要自述；未確認指標定義）'
        return f'{value} {u}（作者摘要自述）'
    raise ValueError('Unsupported source')


def standard_facts(bundles: dict) -> dict:
    """Unified schema preserves original role, source, time and limitations."""
    result = {}
    for case in REQUIRED_CASES:
        bundle = bundles[case]
        mapping = {}
        for f in bundle['facts']:
            label = LABELS.get(f['metric'])
            if label is None: raise ValueError(f'Unknown metric: {f["metric"]}')
            row = {
                'case_id': case,
                'fact_id': f['fact_id'],
                'label': label,
                'measurement_role': f['measurement_role'],
                'value_display': fact_value(case, f),
                'value_original': f['value_original'],
                'unit_original': f['unit_original'],
                'source_evidence_id': f['source_evidence_id'],
                'source_span_sha256': f['source_span_sha256'],
                'source_url': bundle['source']['source_url'],
                'period_as_written': f.get('period_as_written'),
                'qualifier': f.get('qualifier') or f.get('interpretation_limit'),
                'attribution': 'authors_abstract_self_report' if case == 'arxiv' else 'official_source_excerpt_not_independently_verified',
                'independently_verified': False,
            }
            mapping[f['fact_id']] = row
        result[case] = mapping
    if sum(map(len, result.values())) != 16:
        raise ValueError('Expected 6+4+6 pinned facts')
    return result


def validate_model_selection(raw: object, facts: dict) -> list[dict]:
    """Model may select enums & IDs; it may NOT author facts or free-form claims."""
    if not isinstance(raw, dict) or set(raw) != {'schema_version', 'cases'} or raw['schema_version'] != SELECTION_VERSION:
        raise ValueError('Unapproved model output schema or extra top-level field')
    entries = raw['cases']
    if not isinstance(entries, list) or len(entries) != len(REQUIRED_CASES):
        raise ValueError('Exactly three source-local case selections required')
    if {c.get('case_id') for c in entries if isinstance(c, dict)} != set(REQUIRED_CASES):
        raise ValueError('Missing, duplicate or unknown case ID')
    out = []
    for draft in entries:
        if not isinstance(draft, dict) or set(draft) != {'case_id','priority','focus_fact_ids','theme_id','question_ids'}:
            raise ValueError('Additional model fields, including raw numbers/prose, are forbidden')
        case = draft['case_id']
        if draft['priority'] not in ('先讀','追蹤','一般','資料不足'):
            raise ValueError('Invalid attention tier')
        ids = draft['focus_fact_ids']
        if (not isinstance(ids, list) or not 1 <= len(ids) <= 4 or
            any(not isinstance(v, str) for v in ids) or len(set(ids)) != len(ids) or
            any(v not in facts[case] for v in ids)):
            raise ValueError(f'Unknown, cross-source, duplicated or excessive fact IDs for {case}')
        theme = draft['theme_id']
        if not isinstance(theme, str) or theme not in THEMES[case]:
            raise ValueError('Unknown or cross-source hypothesis theme')
        questions = draft['question_ids']
        if (not isinstance(questions, list) or not 1 <= len(questions) <= 2 or
            any(not isinstance(v, str) for v in questions) or len(set(questions)) != len(questions) or
            any(v not in QUESTIONS[case] for v in questions)):
            raise ValueError('Unknown or cross-source review question ID')
        out.append({
            'case_id':case, 'priority':draft['priority'], 'focus_fact_ids':list(ids),
            'theme_id':theme, 'hypothesis':THEMES[case][theme],
            'review_questions':[QUESTIONS[case][q] for q in questions],
            'model_generated_numerical_claims':0,
            'selection_is_not_factual_verification':True,
        })
    return out


def build_review(bundles: dict, selection: object) -> dict:
    facts = standard_facts(bundles)
    choices = validate_model_selection(selection, facts)
    cases = []
    for c in choices:
        case = c['case_id']
        cases.append({
            **c, 'case_title': CASE_TITLES[case],
            'source_title': bundles[case]['source'].get('source_title'),
            'source_url':bundles[case]['source']['source_url'],
            'selected_facts': [facts[case][fid] for fid in c['focus_fact_ids']],
            'human_approved':False, 'publication_allowed':False,
            'independently_verified_claims':0,
        })
    return {
        'schema_version':SCHEMA_VERSION,
        'source_basis':'R1/R2/R3 pinned offline archived excerpts (not freshly verified)',
        'run_mode':'offline_simulated_ai_selection',
        'api_calls':0,
        'publication_allowed':False,
        'human_approved':False,
        'independently_verified_claims':0,
        'catalog_fact_count':sum(map(len,facts.values())),
        'cases':cases,
        'limitations':[
            'AI output only selects known IDs, themes and questions; wording is program-authored predefined text.',
            'Selected themes are hypotheses, not a source-derived cause-and-effect claim.',
            'Hash matching proves archived input integrity, not live source truth or independent verification.',
            'R4 has no real AI call; full usefulness and quality require R5/R6/R7 tests.',
        ],
    }


def render_review(report: dict) -> str:
    if (report.get('publication_allowed') is not False or
        report.get('human_approved') is not False or report.get('api_calls') != 0):
        raise ValueError('Refuse non-offline, published or preapproved report')
    esc = lambda v: html.escape(str(v),quote=True)
    blocks = []
    for c in report['cases']:
        rows = []
        for f in c['selected_facts']:
            rows.append('<tr>' + ''.join(f'<td>{esc(val)}</td>' for val in (
                f['fact_id'],f['label'],f['value_display'],
                f['period_as_written'] or '須參照原文', f['source_evidence_id'],
                f['qualifier'] or '來源摘錄待人工核對'
            )) + '</tr>')
        q_html = ''.join(f'<li>{esc(q)}</li>' for q in c['review_questions'])
        blocks.append(f'''<section><small>{esc(c['case_id'].upper())} / {esc(c['priority'])} / 未查證</small>
<h2>{esc(c['case_title'])}</h2><p><a href="{esc(c['source_url'])}" target="_blank" rel="noopener noreferrer">原始資料（本次未重新讀取）↗</a></p>
<p><strong>離線模擬選擇的分析角度：</strong>{esc(c['hypothesis'])}</p>
<h3>由程式綁定的原始事實（非模型撰寫數值）</h3><div class="scroller"><table><thead><tr><th>Fact ID</th><th>指標</th><th>原值／含義</th><th>時間</th><th>來源證據</th><th>限制</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h3>人工核對問題</h3><ul>{q_html}</ul><p class="review">□ 核對原始文章　□ 單位／定義正確　□ 檢查因果推論　□ 查找獨立佐證　□ 評估是否值得追蹤</p></section>''')
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>視界 SIGNAL｜R4 AI 事實引用離線驗收</title><style>
:root{{--bg:#0f151d;--panel:#1b2735;--edge:#394a60;--gold:#d6b16c;--text:#f4efe2}}*{{box-sizing:border-box}}
body{{max-width:1200px;margin:auto;padding:32px 20px;background:var(--bg);color:var(--text);font:15px/1.8 system-ui,'Microsoft JhengHei',sans-serif}}
h1,h2,h3{{color:var(--gold)}}h1{{font-size:29px}}h2{{font-size:21px}}h3{{font-size:16px}}section{{border:1px solid var(--edge);background:var(--panel);border-radius:13px;padding:24px;margin:22px 0}}small{{color:var(--gold)}}
a{{color:#f4d191}}.warn{{background:#473025;border-left:5px solid #e8ae53;padding:16px}}
.scroller{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;min-width:720px;font-size:13px}}td,th{{border-bottom:1px solid var(--edge);padding:9px;text-align:left;vertical-align:top}}th{{color:var(--gold)}}.review{{background:#243443;padding:12px}}@media print{{body{{background:white;color:black}}section{{background:white;color:black}}}}</style></head><body>
<h1>視界 SIGNAL｜Evidence Rebuild R4</h1>
<p class="warn"><strong>僅供離線驗收｜非 AI 已查證情報</strong>。已固定的 R1～R3 摘錄轉成事實 ID；此處所有數值由程式依事實資料呈現。模擬模型只選擇 ID 與預設分析角度。沒有呼叫 OpenAI、沒有重新讀取網頁、不得發佈或當成投資訊號。</p>
<p>來源：BEA／EIA／arXiv；總事實數：{esc(report['catalog_fact_count'])}；本次示範顯示每則挑選的少數事實。所有證據仍待人工核對。</p>
{''.join(blocks)}<section><h2>下一步驗收</h2><p>R5 測試更多模擬模型回覆、錯誤邊界、版本漂移與組裝結果。R6 才允許一次性真實模型試驗。R7 進行人工品質比較；通過以前不得合併到 main。</p></section></body></html>'''


def write_demo(root: Path, selection: dict, output: Path) -> dict:
    bundles = load_verified_bundles(root)
    catalog = standard_facts(bundles)
    report = build_review(bundles, selection)
    output.mkdir(parents=True, exist_ok=True)
    files = {
        'fact_catalog.json': {'schema_version':'signal-unified-fact-catalog-r4',
                              'publication_allowed':False,'fact_count':report['catalog_fact_count'],
                              'sources': catalog},
        'analysis_review.json':report,
    }
    for filename,data in files.items():
        (output / filename).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output / 'offline_review.html').write_text(render_review(report),encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description='SIGNAL R4: pinned fixtures + simulated AI selection, offline only')
    parser.add_argument('--root', default=None, help='Repository root containing rebuild_r1, rebuild_r2, rebuild_r3')
    parser.add_argument('--selection', default=None, help='Model mock JSON. Defaults to R4/fixtures/mock_ai_selection.json')
    parser.add_argument('--output-dir', default=None, help='Directory for offline preview files')
    args = parser.parse_args()
    root = _root(args.root)
    selected = Path(args.selection) if args.selection else root / 'rebuild_r4' / 'fixtures' / 'mock_ai_selection.json'
    output = Path(args.output_dir) if args.output_dir else root / 'rebuild_r4' / 'out'
    draft = json.loads(selected.read_text(encoding='utf-8'))
    report = write_demo(root,draft,output)
    print(f'PASS R4: cases={len(report["cases"])}; catalog_facts={report["catalog_fact_count"]}; api_calls=0; publication_allowed=false')
    print(f'Report: {output / "offline_review.html"}')


if __name__ == '__main__':
    main()
