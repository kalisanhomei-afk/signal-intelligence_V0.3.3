#!/usr/bin/env python3
"""V0.4.5: exact source-URL, privacy, audit guard tests. Offline only."""
import json,copy,tempfile,sys,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from collect_v034 import checked_sources,collect
from intelligence_v040 import verified_input
from evidence_v041 import build as audit
from refresh import parse_xml
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'data/v034_sources.json').read_text(encoding='utf-8'))
review=json.loads((ROOT/'data/v045_source_review.json').read_text(encoding='utf-8'))
assert len(checked_sources(cfg))==8
assert {s['id'] for s in cfg['sources']}=={'fed-monetary','bea-news','arxiv-ai','arxiv-robotics','eia-energy','nasa-news','eu-press','mit-research'}
assert len({s['publisher_id'] for s in cfg['sources']})==7
assert all(x['status']=='hold_licensing' or x['status']=='hold_metadata_license' for x in review['independent_journalism_holds'])
for sid in ('eu-press','mit-research'):
 for field,value in [('publisher_id','unlicensed'),('url','https://example.com/rss')]:
  mutated=copy.deepcopy(cfg); next(s for s in mutated['sources'] if s['id']==sid)[field]=value
  try:checked_sources(mutated);raise AssertionError('Unauthorized source modification passed')
  except ValueError:pass
clock=dt.datetime(2026,11,5,18,tzinfo=dt.timezone.utc)
def make(s):
 body=f'<rss version="2.0"><channel><item><title>VERIFIED? NO - {s["id"]}</title><link>https://{("ec.europa.eu" if s["id"]=="eu-press" else "news.mit.edu" if s["id"]=="mit-research" else "example.org")}/sample/{s["id"]}</link><pubDate>Thu, 05 Nov 2026 17:00:00 GMT</pubDate></item></channel></rss>'
 return parse_xml(body.encode(),s)
items=collect(checked_sources(cfg),{'meta':{},'items':[],'sources':[]},make,now=clock,pause=lambda x:None)
assert items['meta']['successful_sources']==8 and len(items['items'])==8
assert len(verified_input(items))==8
tr={'meta':{'rights_scope':'descriptive_public_metadata_only'},'items':[
 dict(it,verification_status='待人工核對',independent_confirmation=False) for it in items['items']]}
aud=audit(items,tr)
assert len(aud['items'])==2, 'Only correctly-hosted new publishers have evidence records; fake older hosts blocked'
assert {x['publisher_id'] for x in aud['items']}=={'mit_news','eu_commission'}
assert all(x['evidence_level']=='M0' and x['independent_confirmation_count']==0 for x in aud['items'])
print('PASS V0.4.5: exact host/URL gates, seven unique organizations, no newsroom unauthorized content, evidence only metadata')
