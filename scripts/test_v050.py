#!/usr/bin/env python3
"""V0.5.0 independent offline regression/abuse cases; no API calls."""
from __future__ import annotations
import copy
import datetime as dt
import json
import tempfile
from pathlib import Path
from daily_candidate_v050 import build, validate, RIGHTS
from collect_v034 import checked_sources

ROOT=Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'data/v034_sources.json').read_text(encoding='utf-8'))
sources=checked_sources(config)
now=dt.datetime(2026,11,6,1,0,tzinfo=dt.timezone.utc)
rows=[]
for j,src in enumerate(sources):
  for k in range(3):
    date=now-dt.timedelta(hours=(j%4)*4+k)
    rows.append(dict(id=f'id-{j}-{k}',title=f'Demonstration policy or research item {j} unique {k}',
      url=f'https://example.com/articles/{j}-{k}',source_id=src['id'],publisher_id=src['publisher_id'],
      source=src['name'],source_kind=src['kind'],category=src['category'],
      published_at=date.isoformat(),summary=None))
doc={'meta':{'mode':'official_metadata','rights_scope':RIGHTS,
             'last_success_at':now.isoformat()},'items':rows}
quality={'meta':{'status':'input_coverage_diagnostic_only','domains_no_observed_publisher':5}}
report=build(doc,config,quality=quality,now=now)
assert len(report['items'])==8,report['meta']
assert validate(report,doc,config)
assert report['meta']['global_event_recall'] is None
assert report['meta']['verified_claims']==0
assert len({x['publisher_id'] for x in report['items']})>=4
assert all(x['verification_status']=='未查證' for x in report['items'])
# No news over past 3 days is not an error and never replaced with older items.
old=copy.deepcopy(doc)
for x in old['items']:x['published_at']=(now-dt.timedelta(days=5)).isoformat()
assert build(old,config,now=now)['items']==[]
# Invalid date and implausibly future-dated items must not enter a current-news preview.
corrupt=copy.deepcopy(doc)
corrupt['items'][0]['published_at']='2026-13-99'
corrupt['items'][1]['published_at']=(now+dt.timedelta(days=3)).isoformat()
assert not any(x['id'] in {corrupt['items'][0]['id'],corrupt['items'][1]['id']} for x in build(corrupt,config,now=now)['items'])
# Unknown publisher/forged summary bypasses no input gate.
unsafe=copy.deepcopy(doc)
unsafe['items'][0]['publisher_id']='forged'
unsafe['items'][1]['summary']='A suspicious scraped article body'
selected=build(unsafe,config,now=now)
assert all(x['id'] not in {unsafe['items'][0]['id'],unsafe['items'][1]['id']} for x in selected['items'])
# Attempts to upgrade evidence to verified claims must fail before deployment.
fake=copy.deepcopy(report); fake['meta']['verified_claims']=1
try:validate(fake,doc,config)
except ValueError:pass
else:raise AssertionError('Unchecked verified claim was accepted')
# Changes to link/source/title cannot be propagated from a generated brief.
fake=copy.deepcopy(report); fake['items'][0]['url']='https://evil.invalid/claim'
try:validate(fake,doc,config)
except ValueError:pass
else:raise AssertionError('Brief metadata link poisoning was accepted')
print('PASS V0.5.0: bounded recency/diversity, publisher IDs, no false verification, stale/future skip, rights, and traceable source links')
