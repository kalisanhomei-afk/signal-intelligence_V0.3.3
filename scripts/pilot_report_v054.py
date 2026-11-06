#!/usr/bin/env python3
"""Produce offline human review sheet and summary for V0.5.4 evidence-only pilot."""
from __future__ import annotations
import argparse,html,json
from pathlib import Path
from evidence_analysis_v054 import validate as validate_ai
from evidence_pilot_v054 import validate as validate_evidence

E=lambda x:html.escape(str(x),quote=True)
ROOT=Path(__file__).resolve().parents[1]

def render(evidence,review):
    rows=[];ai={x['id']:x for x in review['items']}
    for i,source in enumerate(evidence['items'],1):
        a=ai[source['id']]
        snippets=''.join(f'<li id="s-{i}-{E(s["id"])}"><b>{E(s["id"])}：</b>{E(s["text"])}<br><small>SHA-256 {E(s["sha256"][:18])}…</small></li>'
                         for s in source['evidence_spans']) or '<li>無法取得足夠可核對之摘錄；請檢查原始頁面。</li>'
        report='''<p class="mute">未呼叫 AI，僅供人工研讀與評估。</p>'''
        if a['status']=='model_failed':
            report='<p class="warn">AI 草稿未通過驗收；錯誤分類：'+E(a.get('error_code') or a.get('error_type') or 'unknown')+'。未偽造結果。'+(' 不一致的數字：'+E(a['rejected_numeric_token'])+'。' if a.get('rejected_numeric_token') else '')+'</p>'
        if a['status']=='model_draft_unverified':
            draft=a['analysis']
            facts=''.join(f'<li>{E(f["statement"])} <b>摘錄ID：{E(", ".join(f["evidence_ids"]))}</b></li>'
                          for f in draft['key_facts']) or '<li>沒有可引用的具體事實</li>'
            hypotheses=''.join(f'<li><b>{E(z["horizon"])}：</b>{E(z["hypothesis"])}<br>前提：{E(z["assumptions"])}</li>'
                               for z in draft['impact_hypotheses']) or '<li>無</li>'
            report=f'''<h3>模型草稿（未查證）</h3><p><b>中文標題：</b>{E(draft['zh_title'])}</p>
<p><b>來源說法：</b>{E(draft['what_source_says'])}</p><p><b>優先建議：</b>{E(draft['reading_priority'])} ／ {E(draft['why_priority'])}</p>
<h4>引用來源摘錄的事實候選</h4><ol>{facts}</ol><h4>影響假說（非事實）</h4><ol>{hypotheses}</ol>
<p><b>關鍵未知：</b>{E(draft['unknowns'])}</p><p><b>下一步查證：</b>{E(draft['next_check'])}</p>'''
        rows.append(f'''<section>
<div class="tag">樣本 {i} · {E(source['publisher_id'])} · {E(source['status'])} · 證據仍未獲獨立驗證</div>
<h2>{E(source['title'])}</h2><p><a target="_blank" rel="noopener noreferrer" href="{E(source['url'])}">原始出處 ↗</a>　發布：{E(source['published_at'])}</p>
<p>擷取方法：{E(source['kind'])}；摘錄擷取時間：{E(source['retrieved_at'] or '未取得')}；錯誤：{E(source.get('error_type') or '—')}</p>
<details><summary>來源摘錄與ID（請點開核對，非完整全文）</summary><ol>{snippets}</ol></details>
{report}
<div class="audit"><b>人工對照（需人工填寫，不會自動回傳 GitHub）</b>
<p>□ 原始頁面可讀　□ 日期及資料期間一致　□ 數字逐項核對　□ 作者主張／原始數據已分開</p>
<p>□ 有其他獨立機構佐證　□ 發現反面證據　□ 摘錄不足無法判定　□ AI 引用ID錯誤</p>
<p>閱讀優先順序：□ 高　□ 中　□ 低 ／ 分析是否改善：□ 是　□ 否　□ 尚無法評估</p>
<p>備註：_______________________________________________________________________</p></div></section>''')
    meta=review['meta']; e_meta=evidence['meta']
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SIGNAL V0.5.4 來源證據驅動 AI 試驗</title><style>
:root{{--ink:#0b0b10;--gold:#c29b40;--sand:#ece6da;--paper:#faf8f3}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:#222;font:15px/1.8 system-ui,'Microsoft JhengHei',sans-serif}}header{{background:var(--ink);color:#fff;padding:30px max(25px,calc((100% - 1060px)/2))}}h1{{font-family:Georgia,serif;letter-spacing:1px}}h1 span{{color:var(--gold)}}main{{max-width:1060px;padding:28px 20px;margin:auto}}section{{background:white;margin:20px 0;padding:26px;border-radius:13px;border:1px solid #dcd2bf;box-shadow:0 6px 20px #0001}}h2{{line-height:1.45}}h3,h4{{color:#8b6b2e}}a{{color:#7e5c2c}}summary{{cursor:pointer;font-weight:700}}details{{background:var(--sand);padding:14px;border-radius:8px}}details li{{padding:9px 0;border-bottom:1px solid #d5c6aa}}.tag,.mute{{color:#786444}}.audit{{margin-top:18px;padding:15px;background:#f6f0e3;border-left:4px solid var(--gold)}}.warn{{color:#ad512b}}li{{margin-bottom:7px}}@media print{{header{{background:white;color:black}}section{{box-shadow:none;break-inside:avoid}}}}
</style></head><body><header><h1>SIGNAL <span>V0.5.4</span></h1><p>證據驅動 AI 試驗｜僅供私人研究與人工查核</p></header><main>
<h2>這不是已驗證情報，也不是投資建議</h2><p>選入 {e_meta['selected_count']} 則；來源可讀 {e_meta['source_readable_count']} 則；AI 分析草稿 {meta['draft_count']} 則；API 呼叫 {meta['api_calls_attempted']} 次；經獨立驗證主張 <strong>0</strong>。來源摘錄被限量保留，報告未部署至網站。</p>
<p><b>可追溯規則：</b>每個 AI 事實候選必須指向以下 E1、E2 等摘錄ID。但引用形式符合要求，<b>仍不代表 AI 的敘述已通過人類核對</b>。只有標題或作者摘要的結果也不能直接視為實質證據。</p>
{''.join(rows)}<p class="mute">本報告供7日內的 GitHub Artifact 私人試驗審閱；切勿將其誤用為正式來源驗證或交易指標。</p></main></body></html>'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',required=True);ap.add_argument('--analysis',required=True)
    ap.add_argument('--base',required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args()
    def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
    evidence=load(args.evidence);review=load(args.analysis);base=load(args.base)
    validate_evidence(evidence,base);validate_ai(review,evidence)
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(render(evidence,review),encoding='utf-8')
    print('V0.5.4 human review report: evidence_ready={} model_drafts={} verified=0'.format(
        evidence['meta']['source_readable_count'],review['meta']['draft_count']))
if __name__=='__main__':main()
