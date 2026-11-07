#!/usr/bin/env python3
"""SIGNAL R8-B: gated, one-request BEA narrative prototype.

- --mock: 100% offline; uses an explicitly HAND_WRITTEN R8-A fixture.
- --live: one POST to Responses API, no retries, opt-in env gate required.
- User-authored narratives are NEVER treated as verified facts or published.
- The R8-A fact catalog is hashed and all claims validated with R8-A rules.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import html
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from typing import Any

import r8_offline as r8a

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / 'out'
MODEL = 'gpt-4.1-mini'
ENDPOINT = 'https://api.openai.com/v1/responses'
PROJECT_LABEL = 'SIGNAL R8-B BEA fixed 2026 snapshot'

class R8BError(RuntimeError):
    def __init__(self, code: str, detail: str = '') -> None:
        super().__init__(f'{code}: {detail}')
        self.code, self.detail = code, detail


def obj(props: dict) -> dict:
    return {'type': 'object', 'additionalProperties': False,
            'properties': props, 'required': list(props)}


def schema_for_bea(catalog: dict) -> dict:
    ids = sorted(catalog['sources']['bea'])
    id_arr = {'type': 'array', 'items': {'type': 'string', 'enum': ids}}
    def claim(tag: str) -> dict:
        return obj({'text': {'type': 'string'},
                    'claim_type': {'type': 'string', 'enum': [tag]},
                    'fact_ids': id_arr,
                    'assumptions': {'type': 'array', 'items': {'type': 'string'}}})
    return obj({
        'schema_version': {'type': 'string', 'enum': ['signal-r8-analysis-draft-v1']},
        'case_id': {'type': 'string', 'enum': ['bea']},
        # The model chooses fact IDs, but NEVER authors the factual observation text.
        # This prevents Chinese-number spellings and unit conversions from entering
        # the published (still unverified) fact observation.
        'observation': obj({'fact_ids': id_arr}),
        'interpretation': claim('inference'),
        'impact': claim('hypothesis'),
        'importance': obj({'tier': {'type': 'string', 'enum': ['高', '中', '低', '待評估']},
                           'reason': {'type': 'string'}, 'fact_ids': id_arr}),
        'limitations': {'type': 'array', 'items': {'type': 'string'}},
        'next_checks': {'type': 'array', 'items': obj({
                'question': {'type': 'string'}, 'target_source': {'type': 'string'},
                'decision_test': {'type': 'string'}})},
        'publication_allowed': {'type': 'boolean', 'enum': [False]},
    })


def build_payload(catalog: dict, model: str = MODEL) -> dict:
    facts = []
    for fact_id, f in catalog['sources']['bea'].items():
        facts.append({k: f.get(k) for k in (
            'fact_id', 'label', 'measurement_role', 'value_original',
            'unit_original', 'value_display', 'source_evidence_id',
            'period_as_written', 'qualifier', 'attribution')})
    instructions = '''你是「視界 SIGNAL」資料約束的情報研究助手。只分析使用者提供的 BEA 固定歷史事實快照，不可上網。
產出六個區塊（observation、interpretation、impact、importance、limitations、next_checks）。
重要：observation 僅能填 fact_ids，不得包含 text、claim_type、assumptions 等其他欄位。程式將自行組合觀察文字並從資料表呈現原始數字；你不能改寫、換算或轉譯這些數字。
interpretation、impact、importance、limitations、next_checks 所有自由文字均禁止阿拉伯數字、中文數字及中文數量詞（例如『二十一點九十億美元』、『三點六十億美元』）、年份、日期、百分比，以及 F001 這類事實 ID；事實 ID 只能放在 fact_ids 陣列，不得寫在文字段落。需要引用數據，只能填 fact_ids。
interpretation 是推論並必須列假設；impact 是條件式待證假說並必須列假設。
重要性應以證據強弱、變化是否顯著、比較基準是否足夠、可影響的決策說明，避免只說「值得關注」。如無足夠背景，選「待評估」。
必須指出至少一項「去哪裡查、查什麼、何種結果會改變判斷」；內容要具體，不可空泛。
注意：事實表的 period_as_written 若為 null，不能自行補年份、月份或完整統計期間；F003～F006 的統計範圍尚待核，不得把不同口徑直接相比；不得推測特定台灣企業受益、歸因特定關稅政策或提供投資建議。
不要把推論寫成已獲獨立驗證；不能聲稱可發布。所有 factual 句必須由選取的 fact_ids 能支持。請使用繁體中文，觀察與機制清楚、短而具體。'''
    return {
        'model': model,
        'store': False,
        'temperature': 0,
        'max_output_tokens': 2500,
        'input': [
            {'role': 'system', 'content': instructions},
            {'role': 'user', 'content': json.dumps({
                'snapshot_context': '歷史固定快照；資訊摘錄未獨立查證；不宣稱最新消息',
                'case_id': 'bea',
                'source_name': 'BEA',
                'facts': facts,
                'task': 'observation 僅列 fact_ids，其他區塊可撰寫有分析價值的短文，但禁止以任何形式撰寫數字、數值、中文數字或在文字中出現 F001 等 ID；引用只放 fact_ids 陣列。'
            }, ensure_ascii=False)},
        ],
        'text': {'format': {'type': 'json_schema', 'name': 'signal_r8b_bea_analysis',
                            'strict': True, 'schema': schema_for_bea(catalog)}},
    }


def raw_response_text(api_json: dict) -> str:
    if api_json.get('status') != 'completed':
        raise R8BError('INCOMPLETE_RESPONSE', str(api_json.get('incomplete_details') or api_json.get('status'))[:180])
    texts = []
    for part in api_json.get('output', []):
        if part.get('type') != 'message':
            continue
        for content in part.get('content', []):
            if content.get('type') == 'refusal':
                raise R8BError('MODEL_REFUSAL', 'model refused to complete the request')
            if content.get('type') == 'output_text':
                texts.append(content.get('text', ''))
    if not texts:
        raise R8BError('EMPTY_OUTPUT', 'no output_text received')
    return '\n'.join(texts)


def parse_response(api_json: dict) -> dict:
    try:
        value = json.loads(raw_response_text(api_json))
    except json.JSONDecodeError as exc:
        raise R8BError('MODEL_JSON_INVALID', f'position {exc.pos}') from exc
    if not isinstance(value, dict):
        raise R8BError('MODEL_JSON_INVALID', 'expected object')
    return value


def one_api_request(payload: dict, api_key: str, timeout: int = 60,
                    opener: Any = None) -> dict:
    """Exactly one urllib request; never retries or prints API credentials."""
    if not api_key:
        raise R8BError('NO_API_KEY', 'OPENAI_API_KEY not configured')
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    request = urllib.request.Request(ENDPOINT, data=body, method='POST', headers={
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    })
    do_open = opener or urllib.request.urlopen
    try:
        with do_open(request, timeout=timeout) as resp:
            data = resp.read(750_000)
            if not data or len(data) >= 750_000:
                raise R8BError('API_RESPONSE_SIZE', 'response empty or exceeded safe limit')
            return json.loads(data.decode('utf-8'))
    except urllib.error.HTTPError as exc:
        # Do not log body: it may accidentally echo secret material or source inputs.
        raise R8BError('API_HTTP_ERROR', f'HTTP {exc.code}') from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise R8BError('API_TRANSPORT_ERROR', type(exc).__name__) from None
    except (UnicodeError, json.JSONDecodeError):
        raise R8BError('API_RESPONSE_PARSE_ERROR', 'invalid API JSON') from None


# The model is never permitted to author the observation prose.
# Keep this fixed sentence human-readable but never claim full source verification.
PROGRAM_OBSERVATION_TEXT = (
    '本案列示來源摘錄所載的事實項目；原始數值、單位與證據出處由程式從下方資料表帶入，統計口徑仍須人工核對。'
)


def bind_model_observation(raw_draft: dict) -> dict:
    """Build the fact observation from selected IDs, never from model wording.
    Model-supplied factual prose is rejected, NOT silently discarded. This also
    keeps the R8-A fixture/validator unchanged for existing offline tests.
    """
    if not isinstance(raw_draft, dict):
        raise R8BError('MODEL_OBSERVATION_SCHEMA_MISMATCH', 'draft must be a JSON object')
    obs = raw_draft.get('observation')
    if not isinstance(obs, dict) or set(obs) != {'fact_ids'}:
        raise R8BError('MODEL_OBSERVATION_SCHEMA_MISMATCH', 'observation may contain only fact_ids')
    result = copy.deepcopy(raw_draft)
    result['observation'] = {
        'text': PROGRAM_OBSERVATION_TEXT,
        'claim_type': 'fact',
        'fact_ids': obs['fact_ids'],
        'assumptions': [],
    }
    return result


def safe_schema_and_fact_draft(draft: dict, catalog: dict) -> dict:
    try:
        verified = r8a.validate_draft(draft, catalog)
    except r8a.DraftError as exc:
        raise R8BError(f'VALIDATION_{exc.code}', exc.field) from None
    if verified['case_id'] != 'bea':
        raise R8BError('WRONG_CASE', 'only BEA allowed in R8B smoke test')
    # The lexical R8-A validator is a fail-closed structural guard, not semantic proof.
    return verified


def report_bundle(draft: dict, catalog: dict, mode: str, usage: dict | None = None) -> dict:
    draft = copy.deepcopy(draft)
    verified = safe_schema_and_fact_draft(draft, catalog)
    ids = verified['fact_refs']
    fact_map = catalog['sources']['bea']
    return {
        'schema_version': 'signal-r8b-review-v1',
        'mode': mode,
        'source_snapshot_sha256': r8a.sha_file(r8a.FIX / 'fact_catalog_snapshot.json'),
        'snapshot_origin': 'R4 fixed historical excerpts; not refreshed or independently verified',
        'model': MODEL if mode == 'LIVE_MODEL_UNVERIFIED' else None,
        'case_id': 'bea',
        'api_calls_attempted': 1 if mode == 'LIVE_MODEL_UNVERIFIED' else 0,
        'usage': usage,
        'draft': draft,
        'observation_text_origin': ('PROGRAM_RENDERED_FROM_FACT_IDS'
                                    if mode == 'LIVE_MODEL_UNVERIFIED'
                                    else 'HAND_WRITTEN_OFFLINE_FIXTURE'),
        'facts_bound_by_code': {f: fact_map[f] for f in ids},
        'fact_ids': ids,
        'structural_validation': 'PASSED_NOT_SEMANTIC_VERIFICATION',
        'human_approved': False,
        'independently_verified': False,
        'publication_allowed': False,
    }


def esc(text: Any) -> str:
    return html.escape(str(text), quote=True)


def render_html(bundle: dict) -> str:
    if bundle.get('error'):
        title = '模型測試未通過'
        main = f'<section class="panel"><h2>狀態：{esc(bundle["error"]["code"])}</h2><p>{esc(bundle["error"].get("detail", ""))}</p><p>不發布；不要反覆重新執行付費工作，應先排查錯誤分類。</p></section>'
    else:
        d = bundle['draft']
        facts = ''.join(
            '<div class="fact"><span class="fid">'+esc(fid)+'</span><div><b>'+esc(f['label'])+
            '</b><p class="v">'+esc(f['value_display'])+'</p><small>證據 '+esc(f['source_evidence_id'])+
            ' · '+esc(f.get('attribution'))+' · <a rel="noopener noreferrer" target="_blank" href="'+esc(f['source_url'])+'">官方來源</a></small>'+
            ('<p class="alert">統計期間／口徑仍須人工核對</p>' if not f.get('period_as_written') or '範圍待核' in f.get('label','') else '')+
            '</div></div>' for fid, f in bundle['facts_bound_by_code'].items())
        labels = [('observation','核心觀察','來源事實'),('interpretation','可能機制','推論'),('impact','條件式影響','待證假說')]
        claims = ''
        for key, title, typ in labels:
            b = d[key]
            assumptions = ''.join('<li>'+esc(a)+'</li>' for a in b['assumptions'])
            claims += (f'<div class="claim"><span class="tag">{esc(typ)}</span><h3>{esc(title)}</h3>'+
                       f'<p>{esc(b["text"])}</p><small>事實索引：{esc(", ".join(b["fact_ids"]))}</small>'+
                       ('<ul>'+assumptions+'</ul>' if assumptions else '')+'</div>')
        follow = ''.join('<div class="follow"><b>待查核事項：</b>'+esc(item['question'])+
                         '<p><b>目標資料：</b>'+esc(item['target_source'])+'</p><p><b>改變判斷的條件：</b>'+esc(item['decision_test'])+'</p></div>' for item in d['next_checks'])
        limits = ''.join('<li>'+esc(s)+'</li>' for s in d['limitations'])
        main = (f'<section class="panel"><h2>BEA｜美台貿易變化 <span class="tag">{esc(d["importance"]["tier"])}</span></h2>'+
                '<div class="alert">固定歷史快照／尚未獨立查證／人工審閱前禁止發布</div><h3>事實卡：原始數值由程式填入</h3>'+
                '<div class="facts">'+facts+'</div><h3>AI 自由分析（需人工審查語義）</h3>'+claims+
                '<div class="claim"><span class="tag">重要性理由</span><p>'+esc(d['importance']['reason'])+
                '</p><small>事實索引：'+esc(', '.join(d['importance']['fact_ids']))+'</small></div>'+
                '<h3>資訊缺口</h3><ul>'+limits+'</ul><h3>可執行的後續追蹤</h3>'+follow+
                '<div class="score"><h3>人工品質評分（模型草稿，非已驗證情報）</h3><div class="scores">'+
                ''.join('<label>'+esc(t)+'<select data-score="'+esc(k)+'"><option value="">未評估</option>'+
                        ''.join('<option value="'+str(n)+'">'+str(n)+'</option>' for n in range(6))+'</select></label>'
                        for k,t in [('evidence_accuracy','證據正確性'),('analytic_depth','分析深度'),('importance_reasoning','重要性理由'),('uncertainty_disclosure','不確定性'),('follow_up_usefulness','後續追蹤')])+
                '</div><label>人工備註<textarea id="note" placeholder="列出具體正誤與是否有實用洞察"></textarea></label>'+
                '<label><input id="source-read" type="checkbox"> 我已核對官方原始資料（自我回報）</label></div></section>')
    mode_badge = ('<div class="alert">離線人工範例（非模型輸出，零 API 呼叫）</div>' if bundle.get('mode') == 'HAND_WRITTEN_MOCK_NOT_MODEL' else '<div class="alert">真實模型草稿或錯誤診斷（未通過人工品質驗收）</div>')
    return '''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>SIGNAL R8-B｜AI深度分析人工審閱</title>
<style>*{box-sizing:border-box}body{margin:0;background:#0e1114;color:#ebe5d8;font:15px/1.72 system-ui,"Microsoft JhengHei",sans-serif}header{padding:47px max(20px,calc((100vw - 1050px)/2));background:linear-gradient(120deg,#272117,#101519 75%);border-bottom:1px solid #8a713d}main{max-width:1050px;margin:auto;padding:25px 18px 95px}h1{font-size:30px;margin:6px 0}h2{color:#f1d593;margin:6px 0 17px}h3{color:#dfc789;margin:19px 0 10px;font-size:16px}.kicker{color:#c7a45b;letter-spacing:.18em}.lead{color:#c4c4c4}.pill,.tag{border:1px solid #806b38;color:#edcc81;border-radius:20px;padding:3px 10px;font-size:12px}.panel{background:#1a1f23;border:1px solid #444035;padding:24px;border-radius:16px;margin:20px 0}.alert{color:#ecd092;background:#362817;padding:11px 14px;border-left:3px solid #d1ad61}.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:10px}.fact,.claim,.follow{border:1px solid #3c4242;background:#242a2f;border-radius:9px;padding:14px;margin:11px 0}.fact{display:flex;gap:14px}.fid{color:#e4c47b;font:700 14px monospace}.v{color:#f6d18a;font-weight:700}.claim p{font-size:16px}.tag{display:inline-block}small{color:#bec3be}a{color:#eaca79}.score{background:#2a261b;border:1px solid #776034;border-radius:12px;padding:17px;margin-top:26px}.scores{display:grid;grid-template-columns:repeat(auto-fit,minmax(156px,1fr));gap:14px}select,textarea{width:100%;padding:8px;border:1px solid #847044;border-radius:6px;background:#14181b;color:white;font:inherit}label{display:block;color:#dec88d;margin:7px 0}textarea{min-height:70px}footer{position:sticky;bottom:0;border-top:1px solid #816d40;background:#15191b;padding:12px;text-align:center}button{padding:11px 20px;border:0;border-radius:7px;background:#caab68;color:#171717;cursor:pointer;font-weight:700}button:disabled{opacity:.4}.note{padding:15px;border:1px solid #68532c;background:#221e18;border-radius:9px}li{margin:5px 0}@media print{footer,.score{display:none}body{background:#fff;color:#222}.panel,.claim,.fact{background:#fff;color:#222;border-color:#ccc}h2,h3{color:#555}}</style></head><body>
<header><span class="kicker">SIGNAL / EVIDENCE REBUILD / R8-B</span><h1>受證據約束的 AI 深度分析</h1><p class="lead">固定 BEA 歷史案例 · 模型自由敘述 · 結構化事實引用 · 人工審閱</p><span class="pill">NOT VERIFIED</span> <span class="pill">NO AUTO PUBLISH</span></header><main><div class="note"><b>重要界線：</b>模型輸出通過的是格式及引用 ID 的程式檢查，不表示它的因果推論、重要性或分析價值已獨立驗證。事實資料仍為固定歷史摘錄，非最新新聞。</div>''' + mode_badge + main + '''</main><footer><button id="export" type="button">匯出人工評分 JSON</button></footer><script>
const c=document.getElementById('export');c.addEventListener('click',()=>{let scores={};document.querySelectorAll('[data-score]').forEach(x=>scores[x.dataset.score]=x.value?Number(x.value):null);const data={schema_version:'signal-r8b-human-review-v1',case_id:'bea',scores,original_source_read:!!document.getElementById('source-read')?.checked,note:document.getElementById('note')?.value||'',human_publication_approval:false,publication_allowed:false,created_at:new Date().toISOString()};const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='SIGNAL_R8B_人工審閱.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
</script></body></html>'''


def failure_bundle(code: str, detail: str, calls: int, snapshot_hash: str | None,
                   rejected_draft: dict | None = None) -> dict:
    result = {'schema_version': 'signal-r8b-review-v1',
            'mode': 'LIVE_ERROR_NO_PUBLISH', 'error': {'code': code, 'detail': detail},
            'case_id': 'bea', 'api_calls_attempted': calls,
            'source_snapshot_sha256': snapshot_hash,
            'human_approved': False, 'independently_verified': False,
            'publication_allowed': False}
    if rejected_draft is not None:
        result['rejected_draft_for_diagnostics_only_not_verified'] = rejected_draft
    return result


def save(bundle: dict, suffix: str) -> tuple[pathlib.Path, pathlib.Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    target_json, target_html = OUT / f'r8b_{suffix}.json', OUT / f'r8b_{suffix}.html'
    target_json.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    target_html.write_text(render_html(bundle), encoding='utf-8')
    return target_json, target_html


def run_mock() -> dict:
    cat = r8a.fact_catalog()
    mock = r8a.read_json(r8a.FIX / 'mock_analysis_drafts.json')['drafts'][0]
    bundle = report_bundle(mock, cat, 'HAND_WRITTEN_MOCK_NOT_MODEL', None)
    save(bundle, 'offline_preview')
    return bundle


def run_live() -> dict:
    if os.getenv('SIGNAL_R8B_ALLOW_PAID_CALL') != 'YES':
        raise R8BError('PAID_GATE_CLOSED', 'SIGNAL_R8B_ALLOW_PAID_CALL must be YES')
    if os.getenv('GITHUB_RUN_ATTEMPT') and os.getenv('GITHUB_RUN_ATTEMPT') != '1':
        raise R8BError('RERUN_NOT_ALLOWED', 'paid request blocked on workflow reruns')
    if os.getenv('GITHUB_REF') and os.getenv('GITHUB_REF') != 'refs/heads/signal-evidence-rebuild':
        raise R8BError('WRONG_BRANCH', 'live mode allowed only in isolated branch')
    approval = (HERE / 'APPROVE_R8B_ONE_CALL.txt').read_text(encoding='utf-8').strip()
    if approval != 'APPROVE_R8B_ONE_CALL=YES':
        raise R8BError('APPROVAL_FILE_CLOSED', 'R8B approval file must explicitly say YES')
    cat = r8a.fact_catalog()
    sha = r8a.sha_file(r8a.FIX / 'fact_catalog_snapshot.json')
    calls = 0
    draft = None
    try:
        key = os.environ.get('OPENAI_API_KEY', '')
        if not key:
            raise R8BError('NO_API_KEY', 'GitHub secret OPENAI_API_KEY missing')
        payload = build_payload(cat)
        # Strict cap: exactly one request; the request function contains no retry loop.
        calls = 1  # conservative: may have been sent even on HTTP or network exception
        api = one_api_request(payload, key)
        raw_draft = parse_response(api)
        draft = raw_draft  # retained solely for safe failed-validation diagnostics
        draft = bind_model_observation(raw_draft)
        bundle = report_bundle(draft, cat, 'LIVE_MODEL_UNVERIFIED', api.get('usage'))
        bundle['api_response_id_suffix'] = (api.get('id') or '')[-8:]
        save(bundle, 'live_result')
        return bundle
    except (R8BError, r8a.DraftError) as exc:
        code = exc.code
        detail = exc.detail if isinstance(exc, R8BError) else exc.field
        # Rejected draft in artifact ONLY, never published to Pages and never printed to logs.
        rejected = (draft if isinstance(draft, dict) and
                    (code.startswith('VALIDATION_') or code == 'MODEL_OBSERVATION_SCHEMA_MISMATCH')
                    else None)
        save(failure_bundle(code, detail, calls, sha, rejected), 'live_result')
        raise
    except Exception as exc:
        # Unexpected errors are diagnostically classified, never silently turned into green Success.
        # Never store exception values or API bodies; they might reveal request material.
        save(failure_bundle('UNEXPECTED_RUNTIME_ERROR', type(exc).__name__, calls, sha), 'live_result')
        raise R8BError('UNEXPECTED_RUNTIME_ERROR', type(exc).__name__) from None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description='SIGNAL R8-B isolated BEA live gate / offline mock')
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--mock', action='store_true', help='no API; built-in hand-written fixture')
    mode.add_argument('--live', action='store_true', help='one paid API request with gate')
    args = p.parse_args(argv)
    try:
        result = run_mock() if args.mock else run_live()
        print(f'R8-B: {result["mode"]}; model calls {result["api_calls_attempted"]}; publication_allowed=false')
        return 0
    except (R8BError, r8a.DraftError) as exc:
        print(f'R8-B FAILED [{getattr(exc, "code", "ERROR")}] without publishing', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
