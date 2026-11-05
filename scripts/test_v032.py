#!/usr/bin/env python3
"""V0.3.2 offline acceptance: 10 channels/8 orgs, probes, zero-entry feed, rights firewall."""
from __future__ import annotations
import sys,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from refresh import parse_xml
from probe_sources import inspect_one,probe
from audit_sources import audit_registry
BASE=Path(__file__).resolve().parents[1]
cfg=json.loads((BASE/'data/v032_candidates.json').read_text(encoding='utf-8'))
rows=cfg['sources']; assert len(rows)==10 and len(set(r['publisher_id'] for r in rows))==8
assert all(not r['enabled'] and not r['live_verified'] and r['permission_status']=='needs_review' for r in rows)
assert all(r['url'].startswith('https://') for r in rows)
rss=b'<rss version="2.0"><channel><title>Empty</title></channel></rss>'
assert parse_xml(rss, {'id':'test','name':'Test','category':'科技','kind':'official'}, allow_empty=True)==[]
try:parse_xml(b'<foo></foo>', {'id':'test','name':'Test','category':'科技','kind':'official'}, allow_empty=True)
except ValueError:pass
else:raise AssertionError('reject unrecognized root')
def fx(s):return (BASE/'tests/fixtures/example-rss.xml').read_bytes()
result=probe(rows,fx)
assert result['meta']['reachable']==10 and result['meta']['rights_cleared']==0
assert all(row['legal_approved'] is False for row in result['sources'])
assert all('title' not in row and 'summary' not in row for row in result['sources'])
registry=json.loads((BASE/'data/source_registry.json').read_text(encoding='utf-8'))
production={'sources':[dict(r,enabled=True,activation_status='candidate',limit=16) for r in rows]}
assert len(audit_registry(registry,production,production=True)['errors'])>=10
bad=inspect_one(dict(rows[0],url='http://unknown.test/rss'),fx)
assert bad['state']=='unavailable'
print('PASS V0.3.2: eight independent candidate publishers; real endpoint statuses only; zero-entry feeds; new candidates cannot bypass formal authorization.')
