#!/usr/bin/env python3
"""SIGNAL R6: fail-closed, one-request, BEA-only real-model contract smoke test.

Not a news verifier. No publishing. R5's SHA-pinned archived fixtures are inputs.
A real model can choose only BEA local IDs / predefined priority, theme, questions.
The validated values and prose in the human-facing report are code-owned.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
from typing import Any

API_ENDPOINT = 'https://api.openai.com/v1/responses'
MODEL = 'gpt-4.1-mini'
MAX_API_CALLS = 1
MAX_MODEL_RESPONSE_BYTES = 40_000
BEA_FIELDS = ('case_id','priority','focus_fact_ids','theme_id','question_ids')
ROOT = Path(__file__).resolve().parent.parent

# Only R4 published, source-local BEA theme / question IDs are permitted.
BEA_THEMES = ('trade_structure_monitor', 'trade_policy_watch')
BEA_QUESTIONS = ('compare_periods', 'check_scope', 'confirm_drivers')
PRIORITIES = ('先讀', '追蹤', '一般', '資料不足')


class R6Error(ValueError):
    pass


def _load_dependencies(root: Path):
    # Add module paths rather than importing extra packages; reuses exact R4/R5.
    for folder in ('rebuild_r4', 'rebuild_r5'):
        path = str(root / folder)
        if path not in sys.path:
            sys.path.insert(0, path)
    import binding_pipeline as r4
    import qa_gate as r5
    return r4, r5


def json_no_duplicate_keys(pairs: list[tuple[str,Any]]) -> dict:
    out={}
    for k, v in pairs:
        if k in out:
            raise R6Error('duplicate_json_keys')
        out[k]=v
    return out


def parse_model_response(response: dict) -> dict:
    if not isinstance(response,dict):
        raise R6Error('api_response_not_object')
    if response.get('status')!='completed':
        raise R6Error('api_response_not_completed')
    candidates=[]
    for item in response.get('output', []):
        if item.get('type') != 'message':
            continue
        for content in item.get('content', []):
            if content.get('type')=='refusal' or content.get('refusal'):
                raise R6Error('api_refusal')
            if content.get('type')=='output_text' and isinstance(content.get('text'),str):
                candidates.append(content['text'])
    if len(candidates)!=1:
        raise R6Error('api_output_text_cardinality_invalid')
    raw=candidates[0].encode('utf-8')
    if len(raw)>MAX_MODEL_RESPONSE_BYTES:
        raise R6Error('api_output_oversized')
    try:
        doc=json.loads(raw.decode('utf-8'), object_pairs_hook=json_no_duplicate_keys)
    except (ValueError, TypeError) as exc:
        raise R6Error('api_output_json_invalid') from exc
    if not isinstance(doc,dict):
        raise R6Error('api_output_schema_invalid')
    return doc


def model_schema(fact_ids:list[str]) -> dict:
    return {
      'type': 'object',
      'properties': {
        'case_id': {'type':'string','enum':['bea']},
        'priority': {'type':'string','enum':list(PRIORITIES)},
        'focus_fact_ids': {'type':'array','items':{'type':'string','enum':fact_ids}},
        'theme_id': {'type':'string','enum':list(BEA_THEMES)},
        'question_ids': {'type':'array','items':{'type':'string','enum':list(BEA_QUESTIONS)}},
      },
      'required':list(BEA_FIELDS),
      'additionalProperties':False,
    }


def build_request(bea_facts: dict, excerpt: str) -> dict:
    # Model is allowed to see stored source numbers but cannot write any in output.
    facts=[{
        'fact_id':id_, 'label':f['label'], 'value':f['value_display'],
        'role':f['measurement_role'], 'source_evidence_id':f['source_evidence_id'],
        'period_as_written':f['period_as_written'], 'source_limit':f['qualifier'],
    } for id_,f in bea_facts.items()]
    prompt={
        'status':'ARCHIVED_OFFICIAL_EXCERPT_ONLY_NOT_INDEPENDENTLY_VERIFIED',
        'excerpt_id':'E7', 'excerpt_text':excerpt, 'facts':facts,
        'allowed_themes':{
          'trade_structure_monitor':'觀察貿易結構變化，仍需其他期間與定義',
          'trade_policy_watch':'政策影響只是研究線索，不是因果結論',
        },
        'allowed_questions':{
          'compare_periods':'核對前期與修訂值',
          'check_scope':'核對出口與進口口徑',
          'confirm_drivers':'核對商品類別與變化原因',
        },
    }
    return {
      'model':MODEL, 'store':False, 'max_output_tokens':320,
      'instructions':(
        '你是嚴格的實驗性新聞編輯分類器，僅根據所給的歷史存檔摘錄選取選項。'
        '只回傳符合 JSON schema 的 enum 與事實 ID；禁止自行輸出數值、年份、分析文字、原始文章引用或未給定欄位。'
        '資料尚未獨立查證；沒有足夠資料時選「資料不足」。'
        'focus_fact_ids 選 1 至 4 個，question_ids 選 1 至 2 個，且不可重複。'
        '注意資料只是 E7 的片段，無法得知整體新聞相對重要性；勿將假說當成已發生的政策影響。'
      ),
      'input':json.dumps(prompt, ensure_ascii=False, separators=(',',':')),
      'text': {'format': {'type':'json_schema','name':'signal_r6_bea_selection',
                          'strict':True, 'schema':model_schema(list(bea_facts))}}
    }


def validate_selection(selection: dict, catalog: dict, r4, root:Path) -> dict:
    if set(selection) != set(BEA_FIELDS):
        raise R6Error('model_output_extra_or_missing_fields')
    if selection.get('case_id')!='bea':
        raise R6Error('model_output_wrong_case')
    # Exact R4 contract check (the other two sources are TRUSTED MOCK only).
    # This does not classify EIA or arXiv as live-model successes.
    fixed=json.loads((root / 'rebuild_r4' / 'fixtures' / 'mock_ai_selection.json').read_text(encoding='utf-8'))
    fixed['cases'][0]=selection
    try:
        choices=r4.validate_model_selection(fixed,catalog)
    except (ValueError,KeyError,TypeError) as exc:
        raise R6Error('model_selection_rejected_by_r4') from exc
    return choices[0]


def make_report(bundles:dict, catalog:dict, selection:dict, r4, *, live: bool, response:dict|None, root:Path) -> dict:
    choice=validate_selection(selection,catalog,r4,root)
    priority=choice['priority']
    return {
      'schema_version':'signal-r6-one-bea-contract-v1',
      'model':MODEL if live else 'OFFLINE_MOCK',
      'status':'TECHNICAL_SMOKE_PASSED_HUMAN_REVIEW_REQUIRED' if live else 'OFFLINE_MOCK_ONLY',
      'run_mode':'live_one_api_call' if live else 'offline_mock',
      'source_basis':'fixed R1 BEA E7 archived excerpt; not a current web read',
      'case_id':'bea',
      'priority':priority,
      'focus_fact_ids':selection['focus_fact_ids'],
      'theme_id':choice['theme_id'],
      'hypothesis':choice['hypothesis'],
      'question_ids':selection['question_ids'],
      'review_questions':choice['review_questions'],
      'facts':[catalog['bea'][fid] for fid in choice['focus_fact_ids']],
      'source_url':bundles['bea']['source']['source_url'],
      'publication_allowed':False, 'human_approved':False,
      'independent_confirmations':0, 'importance_accuracy':None,
      'ai_value_added_verified':False,
      'model_generated_numerical_claims':0,
      'api_calls_attempted':1 if live else 0,
      'request_id':str(response.get('id') or '')[:100] if response else None,
      'usage':{
         k:v for k,v in (response.get('usage') or {}).items()
         if k in ('input_tokens','output_tokens','total_tokens') and isinstance(v,int)
      } if response else {},
      'limitations':[
        '模型只選擇來源內 ID／預設分析角度，沒有產生自由文字的深度洞察。',
        '數字由程式按 R1 事實表帶入，並不是獨立外部事實查證。',
        '優先程度只是 AI 的試驗選擇；本次無全球事件重要性準確率。',
        '沒有重新擷取原始網頁，引用資料是固定歷史快照。',
        '本次不得發布到 SIGNAL 正式網站。',
      ],
    }


def render_html(report:dict) -> str:
    if report.get('publication_allowed') is not False or report.get('human_approved') is not False:
        raise R6Error('unsafe_publishing_flag')
    e=lambda v: html.escape(str(v),quote=True)
    facts=''.join('<tr>'+''.join(f'<td>{e(x)}</td>' for x in (
        f['fact_id'],f['label'],f['value_display'],f['source_evidence_id'],
        f.get('period_as_written') or '待核',f.get('qualifier') or '來源摘錄待核'))+'</tr>'
        for f in report['facts'])
    questions=''.join(f'<li>{e(x)}</li>' for x in report['review_questions'])
    limitations=''.join(f'<li>{e(x)}</li>' for x in report['limitations'])
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGNAL R6｜BEA AI 真實模型冒煙測試</title><style>
    :root{{--bg:#10161f;--card:#202d3c;--gold:#e3be7c;--text:#f5ecdd;--muted:#b1bcce;--line:#4a5b6b}}
    *{{box-sizing:border-box}}body{{max-width:1020px;margin:35px auto;padding:0 20px;background:var(--bg);color:var(--text);font:15px/1.8 system-ui,'Microsoft JhengHei',sans-serif}}
    h1,h2,h3{{color:var(--gold)}}a{{color:#f0d39c}}section{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:24px;margin:20px 0}}
    .warn{{border-left:5px solid #e4b569;padding:15px;background:#463726}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{color:var(--gold)}}.scroll{{overflow:auto}}
    .muted{{color:var(--muted)}}.review{{background:#283b4c;padding:15px}}@media print{{body{{background:white;color:black}}section{{background:white;color:black}}}}
    </style></head><body><h1>視界 SIGNAL｜R6 真實 AI 契約測試</h1>
    <p class="warn"><b>技術測試 ≠ 已查證情報</b>。執行模式：{e(report['run_mode'])}；測試結果：{e(report['status'])}。沒有更新正式網站，不可作為投資依據。</p>
    <section><h2>BEA｜貿易數據</h2><p>模型選擇的人工閱讀優先度：<b>{e(report['priority'])}</b>；Fact IDs：{e(', '.join(report['focus_fact_ids']))}</p>
    <p>程式提供的條件式分析角度：{e(report['hypothesis'])}</p><p><a href="{e(report['source_url'])}" target="_blank" rel="noopener noreferrer">來源網頁（此測試未重新開啟）</a></p>
    <h3>程式引用的原始數據</h3><div class="scroll"><table><thead><tr><th>事實 ID</th><th>指標</th><th>原始數值／角色</th><th>來源</th><th>統計期間</th><th>限制</th></tr></thead><tbody>{facts}</tbody></table></div>
    <h3>核查問題</h3><ul>{questions}</ul><p class="review">人工核查　□ 原始全文　□ 數值及口徑　□ 重要性　□ 推論是否有根據　□ 是否值得繼續開發</p></section>
    <section><h2>驗收邊界</h2><ul>{limitations}</ul><p class="muted">API 嘗試次數：{report['api_calls_attempted']}；模型：{e(report['model'])}；人工核准：否；獨立查證：0。</p></section></body></html>'''


def safe_write(out:Path, result:dict, html_doc:str|None=None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out/'r6_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if html_doc is not None:
        (out/'r6_review.html').write_text(html_doc,encoding='utf-8')


def _request_once(payload:dict, api_key:str, *, opener=urllib.request.urlopen) -> dict:
    if not isinstance(api_key,str) or not api_key.startswith('sk-'):
        raise R6Error('openai_api_key_missing_or_invalid_format')
    req=urllib.request.Request(API_ENDPOINT, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json','User-Agent':'SIGNAL-R6-OneCall/1.0'},
        method='POST')
    try:
        with opener(req,timeout=50) as resp:
            data=resp.read(MAX_MODEL_RESPONSE_BYTES+1)
    except urllib.error.HTTPError as exc:
        # NO raw server body in outputs/logs; auth keys & prompts are never copied.
        raise R6Error(f'api_http_{exc.code}') from None
    except (urllib.error.URLError,TimeoutError,ConnectionError) as exc:
        raise R6Error('api_connection_or_timeout') from None
    if len(data)>MAX_MODEL_RESPONSE_BYTES:
        raise R6Error('api_response_oversized')
    try:
        doc=json.loads(data)
    except (UnicodeError,ValueError) as exc:
        raise R6Error('api_response_json_invalid') from exc
    if not isinstance(doc,dict):
        raise R6Error('api_response_json_not_object')
    return doc


def run(root:Path, out:Path, *, live:bool=False, api_key:str|None=None, api_request=None, require_approval:bool=True) -> dict:
    r4,r5=_load_dependencies(root)
    base={'schema_version':'signal-r6-one-bea-contract-v1',
          'status':'STARTED', 'publication_allowed':False, 'human_approved':False,
          'api_calls_attempted':0, 'source_basis':'fixed R1 archived BEA excerpt',
          'model':MODEL if live else 'OFFLINE_MOCK', 'error_code':None,
          'run_at':datetime.now(timezone.utc).isoformat()}
    try:
        # Require R5 full regression gate BEFORE enabling one API request.
        qa=r5.run_gate(root,out/'_preflight')
        if qa['decision']!='OFFLINE_PASS_R6_CANDIDATE':
            raise R6Error('r5_gate_not_passed')
        bundles=r4.load_verified_bundles(root)
        catalog=r4.standard_facts(bundles)
        if set(catalog['bea'])!=set(('F001','F002','F003','F004','F005','F006')):
            raise R6Error('bea_catalog_ids_changed')
        if live:
            if require_approval and (root/'rebuild_r6'/'APPROVE_ONE_CALL.txt').read_text(encoding='utf-8').strip()!='APPROVE_ONE_CALL=YES':
                raise R6Error('explicit_payment_approval_not_set')
            key=api_key if api_key is not None else os.environ.get('OPENAI_API_KEY','')
            if not key or not key.startswith('sk-'):
                raise R6Error('openai_api_key_missing_or_invalid_format')
            excerpt=json.loads((root/'rebuild_r1'/'fixtures'/'bea_e7.json').read_text(encoding='utf-8'))['item']['evidence_spans'][0]['text']
            payload=build_request(catalog['bea'],excerpt)
            # Write attempt marker before network call: do not retry on unknown completion.
            base['api_calls_attempted']=1
            safe_write(out,base)
            response=(api_request or _request_once)(payload,key)
            selection=parse_model_response(response)
        else:
            response=None
            fixture=json.loads((root/'rebuild_r4'/'fixtures'/'mock_ai_selection.json').read_text(encoding='utf-8'))
            selection=fixture['cases'][0]
        report=make_report(bundles,catalog,selection,r4,live=live,response=response,root=root)
        merged={**base,**report,'error_code':None}
        safe_write(out,merged,render_html(merged))
        return merged
    except R6Error as exc:
        base.update(status='FAILED_NO_PUBLICATION',error_code=str(exc))
        safe_write(out,base)
        raise
    except Exception as exc:
        # The diagnostic only contains Python exception class, not raw network response.
        base.update(status='FAILED_NO_PUBLICATION',error_code='unexpected_'+type(exc).__name__)
        safe_write(out,base)
        raise R6Error(base['error_code']) from None


def main():
    parser=argparse.ArgumentParser(description='SIGNAL R6 evidence-bound AI model smoke test')
    parser.add_argument('--root',default=str(ROOT))
    parser.add_argument('--out',default='rebuild_r6/out')
    parser.add_argument('--live',action='store_true',help='Requires approval file and OPENAI_API_KEY; max one POST; no retry')
    args=parser.parse_args()
    root=Path(args.root).resolve()
    out=Path(args.out).resolve()
    try:
        report=run(root,out,live=args.live)
    except R6Error as exc:
        print('R6_BLOCKED: '+str(exc)+'; failed report in '+str(out), file=sys.stderr)
        return 2
    print(('R6_LIVE_CONTRACT_OK' if args.live else 'R6_OFFLINE_ONLY_PASS')+
          f": case=bea; API attempts={report['api_calls_attempted']}; public=false; review={out/'r6_review.html'}")
    return 0

if __name__=='__main__':
    sys.exit(main())
