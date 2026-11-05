#!/usr/bin/env python3
"""Turn preflight metadata into a concise, safe GitHub Actions summary."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args()
report=json.loads(Path(a.input).read_text(encoding='utf-8'))
meta=report.get('meta',{});sources=report.get('sources',[])
lines=[
 '# SIGNAL RSS 端點探測結果',
 '',
 '**這只代表端點可讀，並非資訊內容可信或授權已通過。**',
 f"- 狀態：{meta.get('state','未執行')}",
 f"- 探測時間（UTC）：{meta.get('last_attempt_at') or '尚未執行'}",
 f"- 可讀來源：{meta.get('reachable',0)} / {meta.get('total',len(sources))}",
 '',
 '| 來源 | 連線 | 可解析條目 | 說明 |',
 '|---|---|---:|---|',
]
for s in sources:
    error=str(s.get('error') or '—').replace('|','/').replace('\n',' ')[:140]
    lines.append(f"| {s.get('source_id','')} | {s.get('state','')} | {s.get('items_seen',0)} | {error} |")
Path(a.output).write_text('\n'.join(lines)+'\n',encoding='utf-8')
