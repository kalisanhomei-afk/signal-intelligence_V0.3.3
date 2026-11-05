#!/usr/bin/env python3
"""Print a local public-source health and data recency report; no credentials."""
import json
import datetime as dt
from pathlib import Path
p=Path(__file__).resolve().parents[1]
d=json.loads((p/'data/discovered.json').read_text(encoding='utf-8'))
m=d.get('meta',{})
print('SIGNAL V0.3 / source collection status')
print('last attempt :',m.get('last_attempt_at') or 'not run')
print('last success :',m.get('last_success_at') or 'not run')
print('sources OK   :',m.get('successful_sources',0),'/',m.get('source_count',0))
print('saved titles :',len(d.get('items',[])))
if m.get('last_success_at'):
 last=dt.datetime.fromisoformat(m['last_success_at'].replace('Z','+00:00'))
 age=dt.datetime.now(dt.timezone.utc)-last
 print('time since success :',round(age.total_seconds()/3600,1),'hours')
 print('freshness :','STALE (>48h)' if age.total_seconds()>48*3600 else 'WITHIN 48h')
for s in d.get('sources',[]):
 print(('OK  ' if s.get('ok') else 'FAIL'),s.get('source_id'),str(s.get('count') or 0).rjust(3),'title(s)',('error: '+str(s.get('error'))) if s.get('error') else '')
