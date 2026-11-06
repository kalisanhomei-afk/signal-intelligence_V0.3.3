#!/usr/bin/env python3
"""Generate a printable evidence-review checklist from a provenance-validated AI PILOT.

This workflow is a separate manual-only tool. It never publishes generated claims to Pages.
"""
from __future__ import annotations
import argparse,html,json
from pathlib import Path
from impact_review_v052 import validate as validate_review
ROOT=Path(__file__).resolve().parents[1]
def load(path):
    p=Path(path)
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else {}
def render(doc):
    e=html.escape
    rows=[]
    for i,x in enumerate(doc['items'],1):
        draft=x.get('ai_draft') if x.get('editorial_mode')=='ai_hypothesis_only' else None
        lines=[]
        if draft:
            for key,label in [('zh_title','草稿翻譯'),('attention_tier','暫定人工審閱'),('why_review','關注理由假說'),('potential_impact','條件式影響'),('impact_horizon','影響期間假說'),('unknowns','未知限制'),('check_question','核對問題')]:
                lines.append(f'<p><strong>{label}：</strong>{e(str(draft[key]))}</p>')
        else:
            lines.append('<p>無 AI 草稿；僅有原始來源元資料，不得補寫。</p>')
        rows.append(f"""<section><small>樣本 {i} · {e(x['source'])} · {e(x['evidence_level'])} · 未查證</small>
        <h2>{e(x['title'])}</h2><p>來源：<a href="{e(x['url'],quote=True)}" target="_blank" rel="noopener noreferrer">原始出處</a> · {e(x['published_at'])}</p>
        {''.join(lines)}<div class="check"><strong>人工核對欄（請先閱讀原始資料）</strong>
        <p>□ 核對發布日期　□ 原文可讀　□ 有數字／主張的來源　□ 有獨立反證或佐證</p>
        <p>人工優先順序：□ 高　□ 中　□ 低　　AI 是否誤導：□ 是　□ 否　□ 未評估</p>
        <p>人工作業備註：________________________________________________________</p></div></section>""")
    return """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>SIGNAL AI 審閱試驗｜僅供人工查核</title><style>
    body{background:#f8f6f0;color:#222;font:15px/1.7 system-ui,sans-serif;max-width:900px;margin:35px auto;padding:0 22px}
    h1{color:#8b6b2e}section{background:white;padding:25px;margin:19px 0;border:1px solid #d7c7a5;border-radius:12px;break-inside:avoid}
    h2{font-size:19px}small{color:#796338}.check{background:#f5f0e5;padding:12px 15px;border-radius:9px;margin-top:15px;font-size:13px}
    @media print{body{background:white}section{border-radius:0;box-shadow:none}}</style></head><body>
    <h1>SIGNAL V0.5.3｜AI 情報假說人工對照表</h1>
    <p><b>此文件不是已查證新聞、正式重要性評分或投資建議。</b>最多3則 AI 條件式草稿、其餘保留規則篩選。
    無法確認來源全文／統計值時，應評為「未評估」，不應追認 AI 猜測為事實。</p>""" + ''.join(rows) + '</body></html>'
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--review',required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args()
    doc=load(args.review)
    validate_review(doc,load(ROOT/'data/live_items.json'),load(ROOT/'data/v034_sources.json'),load(ROOT/'data/evidence_enriched.json'))
    p=Path(args.output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(render(doc),encoding='utf-8')
    print('PILOT ONLY: {} candidates, {} AI hypotheses. No content verified.'.format(len(doc['items']),doc['meta']['ai_drafts']))
if __name__=='__main__':main()
