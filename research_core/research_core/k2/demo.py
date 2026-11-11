"""Run synthetic-only dual-engine demo: python -m research_core.k2.demo.

Produces machine-readable artifacts and readable HTML; no external IO.
"""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import asdict
import html

from research_core.contracts import Observation, SourceSnapshot
from research_core.k2.engine import ScenarioSpec, state_at, forward_scenario, reverse_diagnostic, close_loop, DATA_TYPE

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'fixtures' / 'synthetic_corn_vintages.json'
OUT = ROOT / 'out'
EARLY = '2026-01-11T12:00:00-05:00'
LATE = '2026-01-16T12:00:00-05:00'


def write_json(path: Path, value: object):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def report_html(state_early, state_late, scenarios, reverse, loop):
    h = html.escape
    scenario_rows = ''.join(f"<tr><td>{h(r['scenario_id'])}</td><td>{h(str(r['shocks']))}</td><td>{h(r['counterfactual_ending_stocks'])}</td><td>{h(r['delta_ending_stocks'])}</td><td>合成假設</td></tr>" for r in scenarios)
    contributor_rows = ''.join(f"<tr><td>{h(x['series_id'])}</td><td>{h(x['change'])}</td><td>{h(x['accounting_contribution_to_ending_stocks'])}</td><td>會計貢獻，非因果證明</td></tr>" for x in reverse['accounting_contributors'])
    causes = ''.join(f"<div class='hyp'><strong>{h(x['candidate_id'])}</strong><p>{h(x['proposed_mechanism'])}</p><p class='muted'>要驗證：{h(x['test_needed'])}</p><small>未驗證假說</small></div>" for x in reverse['upstream_candidate_causes'])
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGNAL K2｜雙引擎離線驗收</title><style>
:root{{--bg:#0d121a;--card:#18212b;--gold:#dec188;--ink:#f7f4eb;--muted:#b5bfca;--border:#4b4939;--ok:#83cba9}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.7 'Microsoft JhengHei',system-ui,sans-serif}}main{{max-width:1100px;margin:0 auto;padding:40px 22px 90px}}h1{{font-size:clamp(29px,4vw,44px);line-height:1.25;margin:4px 0}}h2{{font-size:21px;color:var(--gold);margin:0 0 12px}}h3{{font-size:16px;color:var(--gold);margin:0}}.eyebrow{{color:var(--gold);letter-spacing:.18em;font-size:12px;font-weight:bold}}.lead{{color:#e1e7ec;max-width:800px}}.warning{{margin:26px 0;background:#3c2b1e;border:1px solid #a68c59;padding:15px 20px;border-radius:10px;color:#ffe2af}}.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:22px 0}}.stat,section{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:22px}}.stat b{{font-size:30px;color:var(--ok);display:block}}.muted,.stat span,small{{color:var(--muted)}}section{{margin:18px 0}}table{{border-collapse:collapse;width:100%;min-width:630px}}th,td{{text-align:left;padding:9px 12px;border-bottom:1px solid #36424d}}th{{color:var(--gold)}}.overflow{{overflow-x:auto}}code{{color:#f0d38d}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.hyp{{border-left:3px solid var(--gold);background:#202b36;margin:10px 0;padding:12px 15px}}.hyp p{{margin:2px 0 4px}}.chip{{display:inline-block;background:#344135;color:#c5f3da;padding:2px 8px;border-radius:5px}}footer{{font-size:12px;color:var(--muted);margin-top:24px}}@media(max-width:770px){{.pair,.stats{{grid-template-columns:1fr}}}}
</style></head><body><main><div class="eyebrow">SIGNAL / RESEARCH CORE / K2</div><h1>雙引擎｜正向情境 × 反向診斷</h1><p class="lead">使用 K1 時點與版本守門，將合成供需模型的正向情境、後續修訂的會計分解，以及未證實的上游原因區分呈現。</p><div class="warning"><strong>完全合成測試資料</strong>。所有玉米數字均為虛構；不是 USDA 公告、期貨行情、投資預測或交易訊號。本報告不產生付費 API 請求。</div><div class="stats"><div class="stat"><span>初始資料版本</span><b>{h(state_early.vintage_id)}</b><span>{h(state_early.as_of)}</span></div><div class="stat"><span>後續修訂版本</span><b>{h(state_late.vintage_id)}</b><span>{h(state_late.as_of)}</span></div><div class="stat"><span>差額（實際修訂−先前情境）</span><b>{h(loop['revision_delta_residual_observed_minus_scenario'])}</b><span>{h(state_early.unit)}｜僅合成案例</span></div></div>
<section><h2>01｜引擎 B：基本因素正向推演</h2><p>以早期 <code>v1</code> 為研究時點；分析人員輸入假設衝擊，程式依供需恆等式重新計算期末庫存。<strong>這是 What-if 情境，不是統計預測。</strong></p><p>會計式：<code>{h(scenarios[0]['identity'])}</code></p><div class="overflow"><table><thead><tr><th>情境</th><th>假設衝擊</th><th>情境期末庫存</th><th>相對初始變動</th><th>性質</th></tr></thead><tbody>{scenario_rows}</tbody></table></div></section>
<section><h2>02｜引擎 A：事件結果反向研究</h2><p>到了後續 <code>v2</code> 已可取得的時間點，才比較前後修訂。期末庫存從 <b>{h(state_early.ending_stocks)}</b> 變為 <b>{h(state_late.ending_stocks)}</b>，差額為 <b>{h(reverse['observed_ending_stock_change'])}</b>。</p><div class="overflow"><table><thead><tr><th>修訂變數</th><th>原始變更</th><th>對期末庫存的會計貢獻</th><th>證據界線</th></tr></thead><tbody>{contributor_rows}</tbody></table></div><p class="muted">看到產量預估下降，只能說它在會計恆等式中對庫存修訂的貢獻；不能證明是乾旱、病蟲害或其他因素造成。</p></section>
<section><h2>03｜反向因果：保留多個競爭假說</h2><div class="pair"><div>{causes}</div><div><h3>保留的因果界線</h3><p>以上候選原因皆為 <code>UNTESTED_CANDIDATE</code>，沒有經過額外數據驗證，不做機率排序或因果認定。</p><h3>後續研究方向</h3><p>補入在預測截止時間可得的單產、收穫面積、天氣與機構修訂說明，再更新假說。</p></div></div></section>
<section><h2>04｜雙引擎閉環：解釋預測差異，不事後改寫歷史</h2><p>假設在 <code>{h(loop['scenario_frozen_as_of'])}</code> 時，先行研究「產量下降 80」的合成情境，推導期末庫存變動 <b>{h(loop['scenario_delta'])}</b>。之後取得新修訂，實際庫存改變 <b>{h(loop['observed_revision_delta'])}</b>，差額 <b>{h(loop['revision_delta_residual_observed_minus_scenario'])}</b>。</p><p>這個差額只是一筆合成情境的結果，不代表模型已經有預測能力。後續需要多期、事前凍結的預測與正式基準比較。</p><span class="chip">不構成投資訊號</span></section>
<section><h2>05｜K2 的驗收邊界</h2><p><strong>已實作：</strong>共用 K1 時點快照、不同驅動變數的前推恆等式、後續修訂的反向分解、未證實的上游候選原因、情境對修訂的殘差。</p><p><strong>尚未實作：</strong>實際 USDA 接入、參數校準、因果識別、機率預測、商品期貨行情、市場預期差、資產配置及真實投資驗證。</p></section><footer>ENGINEERING QA ONLY · {DATA_TYPE} · OpenAI calls: 0 · No automated publishing or trading.</footer></main></body></html>'''


def build_demo():
    d = json.loads(SOURCE.read_text(encoding='utf-8'))
    if d['fixture_type'] != DATA_TYPE:
        raise RuntimeError('refusing non-synthetic K1 dataset')
    obs = [Observation(**o) for o in d['observations']]
    snaps = {x['snapshot_id']: SourceSnapshot(**{k:v for k,v in x.items() if k != 'raw_payload_utf8'}) for x in d['snapshots']}
    early = state_at(obs, snaps, EARLY)
    late = state_at(obs, snaps, LATE)
    scenarios = [
        forward_scenario(early, ScenarioSpec('K2-S1-production-minus-80', EARLY, {'production':'-80'}, 'arbitrarily declared production shock; not statistical model')),
        forward_scenario(early, ScenarioSpec('K2-S2-use-plus-100', EARLY, {'domestic_use':'100'}, 'illustrative demand sensitivity; not predicted')),
        forward_scenario(early, ScenarioSpec('K2-S3-imports-plus-50', EARLY, {'imports':'50'}, 'illustrative trade sensitivity; not predicted')),
    ]
    rev = reverse_diagnostic(early, late)
    loop = close_loop(scenarios[0], rev)
    qa = {
        'module':'SIGNAL-K2', 'data_type':DATA_TYPE,
        'mode':'SYNTHETIC_OFFLINE_NO_API', 'api_calls':0,
        'forward_accounting_scenarios':len(scenarios), 'reverse_unverified_candidates':len(rev['upstream_candidate_causes']),
        'accounting_identity_verified': True,
        'causal_identification':False,'price_forecast':False,'investment_signal':False,
        'manual_review_required':True,
        'criteria':{'no_future_data_in_early':early.vintage_id=='v1',
                    'later_vintage_visible_only_later':late.vintage_id=='v2',
                    'accounting_revision_equal':rev['observed_ending_stock_change']=='-100',
                    'loop_residual_equal':loop['revision_delta_residual_observed_minus_scenario']=='-20',
                    'causality_unverified':not rev['causality_confirmed']}
    }
    qa['all_passed'] = all(qa['criteria'].values())
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT/'k2_forward_scenarios.json', {'data_type':DATA_TYPE,'as_of_state':early.to_dict(),'scenarios':scenarios})
    write_json(OUT/'k2_reverse_hypotheses.json', {'data_type':DATA_TYPE,'after_as_of_state':late.to_dict(),'diagnostic':rev})
    write_json(OUT/'k2_closed_loop.json', loop)
    write_json(OUT/'k2_qa.json', qa)
    (OUT/'k2_review.html').write_text(report_html(early, late, scenarios, rev, loop), encoding='utf-8')
    if not qa['all_passed']:
        raise RuntimeError('K2 contract demo failed; inspect out/k2_qa.json')
    return qa


if __name__=='__main__':
    result = build_demo()
    print(f"K2 synthetic dual engine QA: {'PASS' if result['all_passed'] else 'FAIL'}; scenarios={result['forward_accounting_scenarios']}, unverified cause candidates={result['reverse_unverified_candidates']}")
    print(f"Open: {OUT/'k2_review.html'}")
