#!/usr/bin/env python3
"""Add V0.4.4 rights-gated expansion results to GitHub step summary."""
from pathlib import Path
import json,os
from source_expansion_v044 import check_report
R=Path(__file__).resolve().parents[1]

def main():
    doc=json.loads((R/'data/source_expansion_v044.json').read_text(encoding='utf-8'))
    check_report(doc)
    lines=['\n## SIGNAL V0.4.4｜優質來源擴充（授權分流）\n',
       '> 技術可讀不等於可信、無償授權或獨立查證。候選僅記錄端點狀態，未儲存未授權全文。\n',
       '| 來源 | 入口 | 技術探測 | 可解析項目 | 使用權利 |','|---|---|---|---:|---|']
    for r in doc['sources']:
        label={'trial_active':'元資料試運行','probe_only':'僅連線檢測','manual_review_only':'僅人工審查'}[r['stage']]
        status={'reachable_parsed':'OK','unavailable':'不可讀','not_attempted':'未執行'}[r['test_state']]
        lines.append(f"| {r['name']} | {label} | {status} | {r['readable_entries'] if r['readable_entries'] is not None else '—'} | {r['rights_status']} |")
        if r['error']:lines.append('> '+r['id']+': '+r['error'].replace('|','/'))
    lines+=['\n**注意：** 本次只有 EIA、NASA 允許採集描述性元資料試運行。BOJ、ECB 尚待使用條款審核；TWSE 明確限制 RSS 僅供閱讀。',
         '目前全球重大事件遺漏率 **仍不可量測**；未知盲區不應以 AI 補寫。\n']
    content='\n'.join(lines)
    report=os.getenv('GITHUB_STEP_SUMMARY')
    if report:
        with open(report,'a',encoding='utf-8') as f:f.write(content)
    print(content)
if __name__=='__main__':main()
