#!/usr/bin/env python3
"""V0.5.2a: independent publish-time quality ledger (no source content verification).

Unparseable/missing publication times are quarantined from all 'latest' surfaces.
first_seen_at only expresses when SIGNAL first encountered an item.
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
from daily_candidate_v050 import as_utc, RIGHTS
from collect_v034 import atomic_json
from intelligence_v040 import ROOT, verified_input

WINDOW=7*86400
FUTURE=3600

def publication_state(row, now):
    published=as_utc(row.get('published_at'))
    if published is None: return 'missing_date'
    age=(now-published).total_seconds()
    if age < -FUTURE: return 'future_date'
    if age > WINDOW: return 'older_than_7_days'
    return 'recent_7_days'

def build(doc, *, now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None: raise ValueError('Time must include a timezone')
    now=now.astimezone(dt.timezone.utc).replace(microsecond=0)
    meta=doc.get('meta',{})
    if meta.get('rights_scope')!=RIGHTS or meta.get('mode')!='official_metadata':
        raise ValueError('Only approved, descriptive public metadata may be audited')
    rows=verified_input(doc)
    counters={k:0 for k in ('recent_7_days','older_than_7_days','missing_date','future_date')}
    quarantine=[]
    for x in rows:
        status=publication_state(x,now)
        counters[status]+=1
        if status in ('missing_date','future_date'):
            quarantine.append({k:x.get(k) for k in ('id','title','url','source','source_id','publisher_id','published_at','first_seen_at')}
                              | {'reason':status, 'verification_status':'未查證／日期待核對'})
    return {'meta':{'version':'0.5.2a','type':'publication_date_quality_only',
                'generated_at':now.isoformat(timespec='seconds'),'rights_scope':RIGHTS,
                'total_checked':len(rows),'counts':counters,'quarantined':len(quarantine),
                'verified_claims':0,'importance_scores':0,
                'notice':'首次採集時間不是新聞發布日期；沒有可信發布時間或時間超前超過1小時，不得放入最新情報。'},
            'quarantine':quarantine[:60]}

def validate(report,doc):
    m=report.get('meta',{})
    if m.get('version')!='0.5.2a' or m.get('rights_scope')!=RIGHTS or m.get('verified_claims')!=0 or m.get('importance_scores')!=0:
        raise ValueError('Invalid date-audit provenance or claims')
    when=as_utc(m.get('generated_at'))
    if when is None: raise ValueError('Missing audit timestamp')
    expected=build(doc,now=when)
    if expected!=report: raise ValueError('Date-audit report disagrees with source metadata')
    return True

def main():
    live=json.loads((ROOT/'data/live_items.json').read_text(encoding='utf-8'))
    report=build(live)
    validate(report,live)
    atomic_json(ROOT/'data/date_quality_v052a.json',report)
    c=report['meta']['counts']
    print('Publication time: recent={recent_7_days}; older={older_than_7_days}; unknown={missing_date}; future={future_date}'.format(**c))
if __name__=='__main__':main()
