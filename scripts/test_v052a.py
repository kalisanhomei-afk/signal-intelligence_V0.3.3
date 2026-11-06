#!/usr/bin/env python3
"""Offline V0.5.2a quality regression: no API, no network."""
import copy,datetime as dt,json,tempfile
from pathlib import Path
from date_quality_v052a import build,validate,publication_state
from collect_v034 import collect,checked_sources
from daily_candidate_v050 import build as daily
from impact_review_v052 import build as impact
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'data/v034_sources.json').read_text(encoding='utf-8'))
ss=checked_sources(cfg)
now=dt.datetime(2026,11,6,3,tzinfo=dt.timezone.utc)
rows=[]
for i,(published,seen) in enumerate([(None,now.isoformat()),
    ((now-dt.timedelta(days=28)).isoformat(),now.isoformat()),
    ((now+dt.timedelta(days=3)).isoformat(),now.isoformat()),
    ((now-dt.timedelta(hours=3)).isoformat(),now.isoformat())]):
    s=ss[i]
    rows.append(dict(id=f'sample-{i}',title='Policy and technology research evidence '+str(i),
       url='https://example.org/'+str(i),source_id=s['id'],publisher_id=s['publisher_id'],
       source=s['name'],source_kind=s['kind'],category=s['category'],published_at=published,
       first_seen_at=seen,summary=None))
live={'meta':{'mode':'official_metadata','rights_scope':'descriptive_public_metadata_only','last_success_at':now.isoformat()},'items':rows}
report=build(live,now=now)
assert report['meta']['counts']=={'recent_7_days':1,'older_than_7_days':1,'missing_date':1,'future_date':1}
assert validate(report,live)
assert publication_state(rows[0],now)=='missing_date' # FIRST SEEN TODAY is NOT publication date
assert {x['id'] for x in daily(live,cfg,now=now)['items']}=={'sample-3'}
assert {x['id'] for x in impact(live,cfg,now=now)['items']}=={'sample-3'}
changed=copy.deepcopy(report);changed['meta']['counts']['recent_7_days']+=1
try:validate(changed,live)
except ValueError:pass
else:raise AssertionError('Bad date report accepted')
# Older and undated records stay in collection for audit, not shown as fresh.
def fake_loader(src):
   if src['id']==ss[0]['id']:return [rows[0]]
   return []
col=collect(ss,{'items':[],'meta':{},'sources':[]},fake_loader,now=now,pause=lambda _:None)
assert col['items'] and col['items'][0]['date_status']=='unverified_missing'
assert col['items'][0]['first_seen_at']==now.isoformat(timespec='seconds')
assert publication_state(col['items'][0],now)=='missing_date'
# HTML archive lives in distinct view; legacy editorial cards not shown by default.
html=(ROOT/'index.template.html').read_text(encoding='utf-8')
assert 'id="page-archive"' in html and 'id="autoFeed"' in html
assert 'function dateState(item)' in html and "dateState(x)==='recent_7_days'" in html
assert html.index('id="page-archive"')<html.index('class="hero"')<html.index('id="page-discover"')
assert 'run_paid_ai' in (ROOT/'.github/workflows/signal-v053-ai-pilot.yml').read_text()
assert "SIGNAL_V052_AI_ENABLED: 'false'" in (ROOT/'.github/workflows/signal-live-v034.yml').read_text()
print('PASS V0.5.2a: no first-seen promotion, 7d/future quarantine, unaffected older metadata, human archive split, manual-only AI pilot.')
