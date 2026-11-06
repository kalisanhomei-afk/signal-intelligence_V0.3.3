#!/usr/bin/env python3
"""V0.5.2 offline acceptance tests: no network or paid API calls."""
from __future__ import annotations
import copy
import datetime as dt
import json
from pathlib import Path
from collect_v034 import checked_sources
from impact_review_v052 import build,validate,validate_draft,sorted_pool,signal,RIGHTS,SCHEMA
ROOT=Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'data/v034_sources.json').read_text(encoding='utf-8'))
sources=checked_sources(config)
now=dt.datetime(2026,11,6,3,tzinfo=dt.timezone.utc)
titles={
 'fed-monetary':'Federal Open Market Committee announces monetary policy',
 'bea-news':'U.S. International Trade in Goods and Services, September 2026',
 'arxiv-ai':'Agent evaluation and artificial intelligence research',
 'arxiv-robotics':'Robotics planning under uncertainty',
 'eia-energy':'Electricity grid and battery energy storage research',
 'nasa-news':'Astronauts chat with students about space',
 'eu-press':'European Commission announces funding program for chips',
 'mit-research':'MIT researchers develop semiconductors for computing',
}
rows=[]
for i,src in enumerate(sources):
    title=titles.get(src['id'],'Engineering research technical findings')
    url='https://arxiv.org/abs/2601.01234' if src['id']=='arxiv-ai' else f'https://example.org/primary/{src["id"]}'
    rows.append({'id':f'record-{i}','source_id':src['id'],'publisher_id':src['publisher_id'],
       'title':title,'category':src['category'],'source':src['name'],'source_kind':src['kind'],
       'url':url,'published_at':(now-dt.timedelta(hours=i*3)).isoformat(), 'summary':None})
meta={'mode':'official_metadata','rights_scope':RIGHTS,'last_success_at':now.isoformat()}
live={'meta':meta,'items':rows}
base={'meta':{'type':'daily_review_candidates_not_a_news_brief','rights_scope':RIGHTS},
      'items':[{'id':rows[0]['id']},{'id':rows[5]['id']}]}
report=build(live,config,baseline=base,now=now)
assert validate(report,live,config)
assert report['meta']['review_count']>=5
assert report['meta']['ai_enabled'] is False and report['meta']['ai_drafts']==0
assert report['meta']['api_calls_attempted']==0
assert report['meta']['importance_accuracy'] is None and report['meta']['global_event_recall'] is None
assert report['meta']['verified_claims']==0
assert signal(rows[5])=='routine_activity'
assert next(i for i,x in enumerate(report['items']) if x['source_id']=='bea-news') < next(i for i,x in enumerate(report['items']) if x['source_id']=='nasa-news')
assert report['items'][0]['source_id'] in ('fed-monetary','bea-news','eu-press')
# A second API-free call with no secret must not be marked AI enabled.
no_key=build(live,config,now=now,enabled=True,api_key='')
assert no_key['meta']['ai_enabled'] is False

def mock_ai(item,scope,abstract,**kw):
    assert kw['api_key']=='test-token'
    assert scope in ('M0','M0A')
    return {'zh_title':'標題忠實翻譯','attention_tier':'一般追蹤',
      'why_review':'這可能涉及政策方向，值得閱讀原始公告。',
      'potential_impact':'若公告內容反映政策變動，可能影響產業判斷，仍須查證。',
      'impact_horizon':'尚不能判定',
      'check_question':'原始文件中是否提供數據與生效日？',
      'unknowns':'尚未讀取完整公告，無從判斷實際影響。'}
assert set(mock_ai(None,'M0',None,api_key='test-token'))==set(SCHEMA['required'])
assert validate_draft(mock_ai(None,'M0',None,api_key='test-token'))
ai=build(live,config,baseline=base,now=now,enabled=True,api_key='test-token',max_ai=2,annotator=mock_ai)
assert validate(ai,live,config)
assert ai['meta']['api_calls_attempted']==2
assert ai['meta']['ai_drafts']==2
assert ai['meta']['verified_claims']==0
assert ai['items'][0]['editorial_mode']=='ai_hypothesis_only'
# Reuse only a matching fingerprint (title, URL, evidence type and prompt version).
cached=build(live,config,previous=ai,now=now,enabled=True,api_key='test-token',max_ai=0,annotator=mock_ai)
assert cached['meta']['cached_ai_drafts']==2 and cached['meta']['api_calls_attempted']==0
assert validate(cached,live,config)
changed=copy.deepcopy(live);changed['items'][0]['title']+=' (revised)'
changed_report=build(changed,config,previous=ai,now=now,enabled=True,api_key='test-token',max_ai=0)
assert changed_report['meta']['cached_ai_drafts']<2
# Bad model schema or unsupported certainty must fall back to a rules-only row.
def bad_ai(*args,**kwargs):return {'zh_title':'已獨立查證必漲'}
bad=build(live,config,now=now,enabled=True,api_key='test-token',max_ai=1,annotator=bad_ai)
assert bad['meta']['api_failures']==1 and bad['meta']['ai_drafts']==0
assert all(x['editorial_mode']=='rules_only' for x in bad['items'])
# Tampering with source URL or claims must block deployment.
for field,value in [('verification_status','已證實'),('importance_verified',True),('url','https://invalid.example/new')]:
    forged=copy.deepcopy(ai);forged['items'][0][field]=value
    try:validate(forged,live,config)
    except ValueError:pass
    else:raise AssertionError('Unsafe edit accepted: '+field)
# M0A requires a matched official arXiv record; nonmatching evidence must be ignored.
ax=next(row for row in rows if row['publisher_id']=='arxiv')
enriched={'meta':{'rights_scope':RIGHTS,'status':'primary_metadata_enrichment_only',
     'verified_claims':0,'independently_confirmed_claims':0,'read_bodies':0},
     'items':[dict(id=ax['id'],publisher_id=ax['publisher_id'],source_id=ax['source_id'],
           url=ax['url'],title=ax['title'],evidence_level='M0A',metadata_title_match=True,
           metadata_read=True,body_read=False,original_document_verified=False,
           independent_confirmation_count=0,verification_status='未查證',
           metadata_record_url=ax['url'],author_abstract='Author-submitted preliminary results, not peer-reviewed.') ]}
with_evidence=build(live,config,enriched,now=now)
assert validate(with_evidence,live,config,enriched)
assert any(x['evidence_level']=='M0A' for x in with_evidence['items'])
tampered=copy.deepcopy(enriched);tampered['items'][0]['url']='https://arxiv.org/abs/2601.99999'
without_evidence=build(live,config,tampered,now=now)
assert all(x['evidence_level']=='M0' for x in without_evidence['items'])
# Stale-only / no-source inputs never fabricate daily significance.
stale=copy.deepcopy(live)
for row in stale['items']:
    row['published_at']=(now-dt.timedelta(days=10)).isoformat()
empty=build(stale,config,now=now)
assert empty['meta']['review_count']==0
# Fixed source report is NOT a reliable importance-accuracy benchmark.
assert report['meta']['importance_accuracy'] is None
print('PASS V0.5.2: editorial preselection, evidence scope, API off by default, capped mock AI, cache, invalidation, fail-closed, provenance, false certainty, stale handling.')
