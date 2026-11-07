#!/usr/bin/env python3
"""SIGNAL R7 editorial QA intake. Offline only. Never calls APIs or publishes.

It inspects *what R6 output establishes*; it does NOT verify upstream claims,
assess real-world importance or certify content accuracy automatically.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def evaluate(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError('r6_result_must_be_object')
    if data.get('schema_version') != 'signal-r6-one-bea-contract-v1':
        raise ValueError('unexpected_r6_schema')
    facts = data.get('facts')
    if not isinstance(facts, list) or not facts:
        raise ValueError('missing_facts')
    ids = data.get('focus_fact_ids', [])
    if not isinstance(ids, list) or len(set(ids)) != len(ids):
        raise ValueError('fact_ids_invalid')
    actual_ids = [f.get('fact_id') for f in facts]
    if ids != actual_ids:
        raise ValueError('fact_list_does_not_match_focus_ids')
    if not all(isinstance(f, dict) for f in facts):
        raise ValueError('fact_must_be_object')
    if data.get('publication_allowed') is not False:
        raise ValueError('unsafe_publication_state')

    provenance_complete = all(all(f.get(k) for k in ('source_url','source_evidence_id','value_original','unit_original')) for f in facts)
    periods_missing = [f['fact_id'] for f in facts if not f.get('period_as_written')]
    scope_unresolved = [f['fact_id'] for f in facts if any(term in str(f.get('label','')) for term in ('待核','不明','未定'))
                        or any(term in str(f.get('qualifier','')) for term in ('待核','不明','未定'))]
    numeric_safe = data.get('model_generated_numerical_claims') == 0
    ai_freeform = False  # R6 contract only returns enum/IDs, per known source code & result limitations.
    human_approved = data.get('human_approved') is True
    confirmations = data.get('independent_confirmations',0)
    confirmation_present = isinstance(confirmations,int) and confirmations>0
    importance_assessed = isinstance(data.get('importance_accuracy'), (int,float)) and not isinstance(data.get('importance_accuracy'),bool)

    checks = [
      {'code':'tracked_provenance','label':'數據具有來源網址、E7 證據識別與原始單位','passed':provenance_complete,
       'note':'僅代表引用欄位存在，不代表已核對官方全文。'},
      {'code':'machine_bound_numbers','label':'未由模型自行生成新的數字主張','passed':numeric_safe,
       'note':'檢查 R6 結果中的契約旗標，不是獨立數字查證。'},
      {'code':'period_scope_clear','label':'全部選中事實的統計期間已確認','passed':not periods_missing,
       'note':'缺少期間的事實 ID：'+(', '.join(periods_missing) if periods_missing else '無')},
      {'code':'measurement_scope_clear','label':'全部選中事實的統計範圍已確認','passed':not scope_unresolved,
       'note':'存在範圍待核的事實 ID：'+(', '.join(scope_unresolved) if scope_unresolved else '無')},
      {'code':'analysis_depth','label':'存在模型提供、而非預設模板的實質解釋','passed':ai_freeform,
       'note':'R6 模型只選擇預設主題及提問；尚無自由分析文字。'},
      {'code':'importance_calibrated','label':'重要性分級已與人工基準比較','passed':importance_assessed,
       'note':'R6 importance_accuracy 為 null，無基準可以評分。'},
      {'code':'human_signoff','label':'人工已閱讀完整原始來源並核准','passed':human_approved,
       'note':'R6 尚未人工核准。'},
      {'code':'independent_confirmation','label':'至少有一項獨立確認','passed':confirmation_present,
       'note':'R6 independent_confirmations 為 0；仍須人工決定適當的驗證方法。'},
    ]
    return {
      'schema_version':'signal-r7-editorial-triage-v1',
      'case_id':data.get('case_id'),
      'source_basis':data.get('source_basis'),
      'input_status':data.get('status'),
      'run_mode':data.get('run_mode'),
      'input_model':data.get('model'),
      'input_publication_allowed':data.get('publication_allowed'),
      'r6_technical_pass':data.get('status')=='TECHNICAL_SMOKE_PASSED_HUMAN_REVIEW_REQUIRED'
                          and data.get('api_calls_attempted')==1 and provenance_complete and numeric_safe,
      'r7_editorial_quality_pass':False,
      'publication_allowed':False,
      'editorial_decision':'NO_GO_PEND_EVIDENCE_AND_HUMAN_REVIEW',
      'facts_selected':len(facts),
      'facts_missing_period':periods_missing,
      'facts_scope_unresolved':scope_unresolved,
      'importance_quality':'NOT_EVALUABLE_WITH_ONE_CASE',
      'analysis_quality':'PRESET_THEME_NOT_ORIGINAL_ANALYSIS',
      'checks':checks,
      'priority_for_next_stage':[
        '核對選中 BEA 事實的統計期間與統計範圍（特別是 F005、F006）。',
        '將 AI 角色從預設主題選擇擴展到受證據約束的可審核分析假說。',
        '建立至少 3 個不同領域的人工參考案例後，再評估重要性判斷。',
      ],
      'note':'這是規則式編輯預審，不等於已完成人工品質評估、官方全文驗證或新聞重要性測量。'
    }


def render_html(r:dict, data:dict)->str:
    esc=lambda v: html.escape(str(v),quote=True)
    rows=''.join('<tr>'+''.join(f'<td>{esc(x)}</td>' for x in [
        f['fact_id'],f['label'],f['value_display'],f['source_evidence_id'],
        f.get('period_as_written') or '待核',
        f.get('qualifier') or ('範圍待核' if '待核' in f['label'] else '未註記')])+'</tr>' for f in data['facts'])
    checks=''.join('<li class="'+('ok' if ch['passed'] else 'bad')+'"><strong>'+('✓ ' if ch['passed'] else '✕ ')+esc(ch['label'])+'</strong><small>'+esc(ch['note'])+'</small></li>' for ch in r['checks'])
    ratings=[('source','來源完整性與口徑'),('accuracy','數據與證據正確性'),('depth','分析深度與新資訊'),('priority','重要性判斷'),('action','可行的追蹤問題')]
    fields=''.join(f'<label>{esc(name)}<select data-rating="{code}"><option value="unrated">尚未評估</option>'+''.join(f'<option value="{n}">{n} / 5</option>' for n in range(6))+'</select></label>' for code,name in ratings)
    # No tracking, links only point to origin. JS creates local download only.
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SIGNAL R7｜情報品質審閱表（離線）</title><style>
:root{{--ink:#10151c;--panel:#18212a;--line:#715c38;--gold:#d9b575;--cream:#f8efdc;--muted:#c5baa8;--red:#eab9ab;--green:#b3dbc0}}
*{{box-sizing:border-box}}body{{background:var(--ink);color:var(--cream);font:15px/1.75 system-ui,'Microsoft JhengHei',sans-serif;margin:0;padding:30px 16px}}main{{max-width:980px;margin:auto}}h1{{color:var(--gold);margin:0 0 8px;font-size:30px}}h2{{color:var(--gold);font-size:21px;margin:0 0 12px}}p{{margin:10px 0}}.sub{{color:var(--muted)}}section{{border:1px solid var(--line);background:var(--panel);padding:22px 25px;margin:17px 0;border-radius:10px}}.badge{{display:inline-block;background:#5b251f;color:#ffdbc8;padding:6px 14px;border-radius:30px;font-weight:700}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}}.tile{{border:1px solid #746140;border-radius:8px;padding:16px}}.tile strong{{display:block;color:var(--gold);font-size:23px}}.ok{{color:var(--green)}}.bad{{color:var(--red)}}ul{{margin:0;padding-left:23px}}li{{margin:7px 0}}li small{{color:var(--muted);display:block;margin-left:0}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #39434a;text-align:left;padding:11px 9px}}th{{color:var(--gold)}}.tablewrap{{overflow:auto}}select,textarea{{width:100%;background:#0e171f;color:white;border:1px solid #8b734e;border-radius:6px;padding:8px;margin-top:8px}}label{{display:block;line-height:1.4;margin:14px 0}}button{{color:#201b14;background:var(--gold);border:0;border-radius:6px;padding:10px 18px;font-size:15px;font-weight:700;cursor:pointer}}a{{color:var(--gold)}}.hint{{background:#202e38;border-left:4px solid #d9b575;padding:10px 14px}}.fine{{color:var(--muted);font-size:12px}}@media print{{body{{background:white;color:#111}}section{{background:white;color:#111}}.tile strong,h1,h2,th{{color:#593e13}}button{{display:none}}}}
</style></head><body><main>
<p class="sub">視界 SIGNAL / Evidence Rebuild / R7 / 不連線、不收費、不發布</p><h1>情報品質審閱與准入門檻</h1>
<p><span class="badge">正式發佈：NO-GO</span></p><p>本報告使用 R6 真實 API 產出之固定快照進行<strong>規則式預審</strong>。R6 技術成功不等於新聞查證成功，也不等於重要性判斷正確。</p>
<section><h2>本次預審摘要</h2><div class="grid"><div class="tile">R6 工程狀態<strong>成功</strong>事實編號與 API 流程已測通</div><div class="tile">引用事實<strong>{r['facts_selected']} 筆</strong>數值由程式帶入</div><div class="tile">期間欄位待核<strong>{len(r['facts_missing_period'])} 筆</strong>不應直接對外解讀</div><div class="tile">口徑待核<strong>{len(r['facts_scope_unresolved'])} 筆</strong>不得推論比較關係</div></div><p class="hint">試驗來源：{esc(r['source_basis'])}；模型：{esc(r['input_model'])}。<br>重要性選「{esc(data.get('priority'))}」，但尚無人工基準可檢驗這個分類是否合理。</p></section>
<section><h2>客觀門檻檢查</h2><ul>{checks}</ul><p class="fine">勾選不代表已獨立查證；失敗表示資料不足或尚未滿足流程門檻。</p></section>
<section><h2>引用事實與待核資訊</h2><div class="tablewrap"><table><thead><tr><th>事實 ID</th><th>來源描述</th><th>原始數值</th><th>證據 ID</th><th>統計期間</th><th>口徑註記</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>AI 選擇的預設分析題目：<strong>{esc(data.get('theme_id'))}</strong>；顯示的分析文字：{esc(data.get('hypothesis'))}</p>
<p><strong>重要限制：</strong>這段文字是系統預先撰寫的內容，不應視為模型提出的原創分析。</p></section>
<section><h2>人工品質評分（由人填寫）</h2><p>請在閱讀 BEA 官方完整資料並核對原始統計口徑後再評分。下方預設皆為「尚未評估」，不會因下載報告而改變正式發布許可。</p><div class="grid">{fields}</div>
<label>人工結論<select id="decision"><option value="pending">待核實</option><option value="reject">不通過</option><option value="review_required">補證據後複審</option><option value="quality_acceptable_not_for_publish">分析品質可接受，但尚未批准發布</option></select></label>
<label>核對記錄／不足與改進方向<textarea id="notes" rows="5" placeholder="記錄核對到的統計期間、資料表、是否有未支持的推論、真正值得追蹤的問題。"></textarea></label>
<button type="button" onclick="exportReview()">匯出人工審閱 JSON（儲存在本機）</button><p class="fine">不會將審閱結果傳送到網路。此頁無權變更 GitHub Actions、API 授權或正式網站。</p></section>
<section><h2>R7 結論與下一關</h2><p><strong>R6 技術驗收已通過；R7 情報品質尚未通過。</strong>目前不存在充分證據，證明它比可追溯的數據整理多提供了具體洞察。</p><p>下一次開發只處理：統計口徑／期間核對、可審核的自由分析假說、以及三領域對照評分。避免新版本重新擴張 RSS、介面和付費呼叫。</p></section>
</main><script>
function exportReview(){{
 const ratings={{}}; document.querySelectorAll('[data-rating]').forEach(el=>ratings[el.dataset.rating]=el.value);
 const data={{schema_version:'signal-r7-human-review-v1',case_id:'bea',source:'R6 saved API result',ratings,
 decision:document.getElementById('decision').value,notes:document.getElementById('notes').value,
 export_time_local:new Date().toISOString(),publication_allowed:false,independently_verified:false}};
 const blob=new Blob([JSON.stringify(data,null,2)],{{type:'application/json;charset=utf-8'}});
 const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='signal_r7_human_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}}
</script></body></html>'''


def main()->None:
    p=argparse.ArgumentParser(description='offline SIGNAL R7 editorial triage')
    p.add_argument('--input',type=Path,default=ROOT/'fixtures/r6_live_result_sanitized.json')
    p.add_argument('--output',type=Path,default=ROOT/'out')
    args=p.parse_args()
    data=json.loads(args.input.read_text(encoding='utf8'))
    result=evaluate(data)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'r7_quality_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (args.output/'r7_quality_review.html').write_text(render_html(result,data),encoding='utf8')
    print('R7 editorial result:',result['editorial_decision'])
    print('R6 technical pass:',result['r6_technical_pass'])
    print('Selected facts:',result['facts_selected'])
    print('All artifacts written to',args.output)

if __name__=='__main__':main()
