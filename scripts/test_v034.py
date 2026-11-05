#!/usr/bin/env python3
"""V0.3.4 offline acceptance; no remote network, no Github token."""
from __future__ import annotations
import datetime as dt, json, copy, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from collect_v034 import checked_sources,collect,atomic_json
from refresh import parse_xml
from build_public_site import build
P=Path(__file__).resolve().parents[1]
S=checked_sources(json.loads((P/'data/v034_sources.json').read_text(encoding='utf-8')))
assert len(S)==4 and len({s['publisher_id'] for s in S})==3
assert len({s['url'] for s in S})==4
assert all(s['status']=='metadata_only' and s['evidence_url'].startswith('https://') for s in S)
for edit in (lambda a:a.append(dict(a[0],id='bbc-world')),
             lambda a:a[0].update(url='https://www.federalreserve.gov/unreviewed.xml'),
             lambda a:a[0].update(status='anything')):
    cfg=json.loads((P/'data/v034_sources.json').read_text())
    edit(cfg['sources'])
    try:checked_sources(cfg)
    except ValueError:pass
    else:raise AssertionError('Unreviewed feed must be blocked')

moment=dt.datetime(2026,11,5,12,tzinfo=dt.timezone.utc)
xml=lambda i: (f'<rss version="2.0"><channel><title>TEST</title><item><title>TEST ONLY {i}</title>'
   f'<link>https://example.org/source/{i}?utm_source=demo</link>'
   '<pubDate>Thu, 05 Nov 2026 11:00:00 GMT</pubDate></item></channel></rss>').encode('utf-8')
loader=lambda s:parse_xml(xml(s['id']),s)
old={'meta':{},'items':[],'sources':[]}
first=collect(S,old,loader,now=moment,pause=lambda n:None)
assert first['meta']['successful_sources']==4
assert first['meta']['new_items_in_run']==4
assert len(first['items'])==4
assert all(x.get('summary') is None and x['title'].startswith('TEST ONLY') for x in first['items'])
assert all('utm_' not in x['url'] for x in first['items'])
second=collect(S,first,loader,now=moment+dt.timedelta(hours=12),pause=lambda n:None)
assert second['meta']['new_items_in_run']==0
assert first['items'][0]['first_seen_at']==second['items'][0]['first_seen_at']
partial=collect(S,second,lambda s:(_ for _ in ()).throw(OSError('test 403')) if s['id']=='bea-news' else loader(s),now=moment+dt.timedelta(days=1),pause=lambda n:None)
assert partial['meta']['successful_sources']==3 and partial['meta']['status']=='partial'
assert len(partial['items'])==4
assert any(s['source_id']=='bea-news' and not s['ok'] for s in partial['sources'])
all_fail=collect(S,partial,lambda s:(_ for _ in ()).throw(ConnectionError('test offline')),now=moment+dt.timedelta(days=2),pause=lambda n:None)
assert all_fail['meta']['status']=='unavailable' and len(all_fail['items'])==4
assert all_fail['meta']['last_success_at']==partial['meta']['last_success_at']
expired=collect(S,all_fail,lambda s:(_ for _ in ()).throw(ConnectionError('test offline')),now=moment+dt.timedelta(days=47),pause=lambda n:None)
assert len(expired['items'])==0

with tempfile.TemporaryDirectory() as d:
    root=Path(d)
    target=root/'public'
    out=build(target)
    assert 'data/discovered.json' in out
    assert 'data/v034_sources.json' not in out and 'data/source_registry.json' not in out
    public=json.loads((target/'data/discovered.json').read_text(encoding='utf-8'))
    # A production repository already contains live records from earlier runs.
    # The public site must preserve the approved snapshot; it must NOT be empty.
    orig=json.loads((P/'data/live_items.json').read_text(encoding='utf-8'))
    assert public['meta']['mode']=='official_metadata'
    assert public['meta']['rights_scope']=='descriptive_public_metadata_only'
    assert public['items']==orig['items'], 'Published metadata must match the approved live history'
    assert all(x['source_id'] in ('fed-monetary','bea-news','arxiv-ai','arxiv-robotics')
               and x.get('summary') is None for x in public['items'])
    # Building a site after a real collection must publish only reviewed metadata.
    copyroot=root/'testproject'
    (copyroot/'data').mkdir(parents=True)
    for file in ['index.html','source-console.html']:
        (copyroot/file).write_bytes((P/file).read_bytes())
    for file in ['feed.json','v032_candidates.json','v032_live_probe.json']:
        (copyroot/'data'/file).write_bytes((P/'data'/file).read_bytes())
    atomic_json(copyroot/'data/live_items.json',partial)
    from intelligence_v040 import prepare
    tri=prepare(partial,{},enabled=False,api_key=None)
    atomic_json(copyroot/'data/intelligence.json',tri)
    from evidence_v041 import build as build_evidence
    atomic_json(copyroot/'data/evidence_audit.json',build_evidence(partial,tri))
    rebuilt=build(root/'_site',source_root=copyroot)
    assert len(json.loads((root/'_site/data/discovered.json').read_text())['items'])==4
    bad=copy.deepcopy(partial)
    bad['items'][0]['source_id']='unreviewed-media'
    atomic_json(copyroot/'data/live_items.json',bad)
    try:build(root/'_site',source_root=copyroot)
    except RuntimeError:pass
    else:raise AssertionError('Unsafe public metadata should fail closed')
print('PASS V0.3.4: strict allowlist, metadata-only, dedup, 403 retention, 45d TTL, public export and rights firewall.')
