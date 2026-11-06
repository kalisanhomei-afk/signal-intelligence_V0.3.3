#!/usr/bin/env python3
"""V0.4.4 offline acceptance. Never requires public networks or OpenAI API."""
import json,sys,copy,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from source_expansion_v044 import build,check_report,approved_config,FROZEN
from collect_v034 import checked_sources,collect
from refresh import parse_xml
ROOT=Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'data/v044_candidates.json').read_text(encoding='utf-8'))
live=json.loads((ROOT/'data/v034_sources.json').read_text(encoding='utf-8'))
by=approved_config(config,live)
assert len(checked_sources(live))==8
assert len({i['publisher_id'] for i in checked_sources(live)})==7
assert {'eia-energy','nasa-news'}<=set(x['id'] for x in live['sources'])
assert {'boj-news','ecb-press','twse-news'}.isdisjoint(x['id'] for x in live['sources'])
for sid in ('boj-news','ecb-press','twse-news'):
    x=copy.deepcopy(config)
    next(row for row in x['candidates'] if row['id']==sid)['publish_status']='trial_active'
    try:approved_config(x,live);raise AssertionError('Rights hold was bypassed: '+sid)
    except ValueError:pass
src={x['id']:x for x in checked_sources(live)}
for sid in ('eia-energy','nasa-news'):
    assert src[sid]['status']=='metadata_only' and src[sid]['evidence_url'].startswith('https://')
# Capture only counts, not unreleased news text.
seen=[]
def fetch(row):
    seen.append(row['id'])
    if row['id']=='boj-news':raise PermissionError('simulated 403')
    return [{'title':'fake - MUST NOT be stored','url':'https://example.invalid/secret','id':'fake'}]
result=build(config,live,fetcher=fetch,now='2026-11-05T16:00:00+00:00')
assert seen==['eia-energy','nasa-news','boj-news','ecb-press']
assert result['meta']['source_connection_successes']==3
assert result['meta']['rights_held_sources']==3
assert check_report(result)
serialized=json.dumps(result,ensure_ascii=False)
assert 'fake - MUST NOT be stored' not in serialized
assert 'secret' not in serialized
assert result['sources'][-1]['test_state']=='not_attempted'
# Unauthorized alteration fails the public-report guard.
for field,val in [('verified_claims',1),('event_recall',0.9),('rights_scope','anything')]:
    bad=copy.deepcopy(result);bad['meta'][field]=val
    try:check_report(bad);raise AssertionError('Report forgery passed')
    except RuntimeError:pass
# New channel 403s must NOT delete or degrade valid old-source history.
import datetime as dt
now=dt.datetime(2026,11,5,16,tzinfo=dt.timezone.utc)
xml=lambda sid:(f'<rss version="2.0"><channel><item><title>PROBE {sid}</title>'
    f'<link>https://example.org/{sid}</link><pubDate>Thu, 05 Nov 2026 15:00:00 GMT</pubDate></item></channel></rss>').encode()
all_sources=checked_sources(live)
first=collect(all_sources,{'meta':{},'items':[],'sources':[]},lambda s:parse_xml(xml(s['id']),s),now=now,pause=lambda n:None)
assert len(first['items'])==8
second=collect(all_sources,first,lambda s:(_ for _ in ()).throw(PermissionError('simulated 403')) if s['id'] in ('eia-energy','nasa-news') else parse_xml(xml(s['id']),s),now=now+dt.timedelta(hours=4),pause=lambda n:None)
assert second['meta']['status']=='partial' and len(second['items'])==8
assert second['meta']['successful_sources']==6
assert second['meta']['new_items_in_run']==0
print('PASS V0.4.4: exact host/rights gating, 2 legal-metadata trials, 3 held, no article republishing, failure preserves history.')

# Old-than-retention RSS titles must not be repeatedly counted as new additions.
old_xml=b'<rss version="2.0"><channel><item><title>OUTDATED ANNOUNCEMENT</title><link>https://example.org/old</link><pubDate>Thu, 01 Jan 2026 10:00:00 GMT</pubDate></item></channel></rss>'
stale=collect(all_sources,{'meta':{},'items':[],'sources':[]},lambda s:parse_xml(old_xml,s),now=now,pause=lambda n:None)
assert stale['meta']['new_items_in_run']==0 and stale['meta']['item_count']==0
print('PASS V0.4.4: new-items metric excludes expired feed entries.')
