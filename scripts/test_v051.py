#!/usr/bin/env python3
"""V0.5.1: tests must *not* convert synthetic/unknown news into verified events."""
import copy
import datetime as dt
import json
from pathlib import Path
from benchmark_v051 import build, check_seed, validate

BASE=Path(__file__).resolve().parents[1]
seed=json.loads((BASE/'data/benchmark_candidates_v051.json').read_text(encoding='utf-8'))
assert len(seed['events'])>=20
assert check_seed(seed)
# Test on an isolated pending sample; production reviewers may legitimately approve rows later.
seed={'schema_version':'0.5.1','events':copy.deepcopy(seed['events'][:20])}
for ev in seed['events']:
    ev.update(review_status='pending',evidence_audited=False,reviewed_by='',reviewed_at='',
              impact_justification='',match_status='pending',match_item_id='',
              match_reviewed_by='',match_reviewed_at='',match_note='')
NOW=dt.datetime(2026,11,6,12,tzinfo=dt.timezone.utc)
LIVE={'meta':{'rights_scope':'descriptive_public_metadata_only','mode':'official_metadata','last_success_at':NOW.isoformat()},'items':[]}
DAILY={'meta':{'rights_scope':'descriptive_public_metadata_only','type':'daily_review_candidates_not_a_news_brief','verified_claims':0,'independent_confirmations':0,'global_event_recall':None},'items':[]}
empty=build(seed,LIVE,DAILY,now=NOW)
assert empty['meta']['gold_candidate_total']==20
assert empty['meta']['approved_benchmark_events']==0
assert empty['meta']['global_news_recall'] is None
assert empty['meta']['audited_sample_capture_rate'] is None
assert not empty['meta']['benchmark_ready']
assert validate(empty,seed,LIVE,DAILY)

# A small reviewed set must not be reported as a meaningful global or sampled recall rate.
small=copy.deepcopy(seed)
small['events'][0].update(review_status='approved',reviewed_by='test_editor',reviewed_at=NOW.isoformat(),
                          impact_justification='A dated central bank decision can matter to financial conditions.',evidence_audited=True)
one=build(small,LIVE,DAILY,now=NOW)
assert one['meta']['approved_benchmark_events']==1 and one['meta']['audited_sample_capture_rate'] is None

# Index pages must not be mislabeled as fully audited, specific-event original evidence.
invalid=copy.deepcopy(seed)
invalid['events'][-1].update(review_status='approved',reviewed_by='test_editor',reviewed_at=NOW.isoformat(),
                             impact_justification='A trade report may be meaningful, needs exact primary URL.',evidence_audited=True)
try:check_seed(invalid);raise AssertionError('Index URL falsely passed full evidence audit')
except ValueError:pass

# Entirely synthetic unit fixtures; NONE of these are real-world news or production reference events.
full=copy.deepcopy(seed)
rows=[];recent=[]
for i,ev in enumerate(full['events']):
    day='2026-11-05' if i>=14 else ev['date']
    ev['date']=day
    ev['domain']=['財經','科技','政治','能源','社會'][i%5]  # test balanced audit coverage
    ev['reference_url']=f'https://example.org/primary/{ev["id"]}'
    item={'id':f'synthetic-item-{i}','title':f'SYNTHETIC TEST - {ev["title"]}',
          'url':ev['reference_url'],'source_id':'fed-monetary','publisher_id':'fed',
          'source':'SYNTHETIC UNIT TEST', 'category':'測試','published_at':day+'T12:00:00+00:00','summary':None}
    rows.append(item)
    ev.update(review_status='approved',reviewed_by='test_editor',reviewed_at=NOW.isoformat(),
              impact_justification='SYNTHETIC TEST: assumed material impact for coverage measurement.',
              evidence_audited=True,match_status='confirmed_present',match_item_id=item['id'],
              match_reviewed_by='test_matcher',match_reviewed_at=NOW.isoformat(),
              match_note='SYNTHETIC TEST: item URL and ID were explicitly cross-checked against a fixture.')
    if i>=14 and i%2==0:recent.append(item)
LIVE['items']=rows
DAILY['items']=recent
r=build(full,LIVE,DAILY,now=NOW)
assert r['meta']['benchmark_ready']
assert r['meta']['audited_sample_capture_rate']==100.0
assert r['meta']['reviewed_daily_eligible']==7, r['meta']
assert r['meta']['audited_daily_selection_rate']==42.9, r['meta']
assert r['meta']['audited_recency_only_selection_rate']==100.0
assert r['meta']['global_news_recall'] is None
assert validate(r,full,LIVE,DAILY)

# Reject fabricated match item ID, falsified rates, or unsupported per-event approval.
bad=copy.deepcopy(full);bad['events'][0]['match_item_id']='made-up-item'
try:build(bad,LIVE,DAILY,now=NOW);raise AssertionError('Untraceable claimed capture passed')
except ValueError:pass
bad=copy.deepcopy(full);bad['events'][0]['reviewed_by']=''
try:build(bad,LIVE,DAILY,now=NOW);raise AssertionError('Self-approved reference passed')
except ValueError:pass
badout=copy.deepcopy(empty);badout['meta']['global_news_recall']=99.9
try:validate(badout,seed,{'meta':LIVE['meta'],'items':[]},{'meta':DAILY['meta'],'items':[]});raise AssertionError('Fake global recall passed')
except ValueError:pass
print('PASS V0.5.1: 20 actual source reference candidates remain unapproved; separate human audit and match review; explicit ready gates, no fake global recall, synthetic coverage tests')
