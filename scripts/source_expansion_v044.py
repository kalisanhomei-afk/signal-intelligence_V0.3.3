#!/usr/bin/env python3
"""V0.4.4: authoritative candidate-source probe & enforceable rights gate.

The probe stores NO scraped headlines or body text. Successful HTTP/RSS checks
are NOT publication permission, verification, cross-source evidence or news recall.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
from urllib.parse import urlsplit
from collect_v034 import EXPECTED,fetch_metadata,checked_sources,atomic_json

ROOT=Path(__file__).resolve().parents[1]
FROZEN={
 'eia-energy':('eia','https://www.eia.gov/rss/todayinenergy.xml','approved_metadata_trial','trial_active'),
 'nasa-news':('nasa','https://www.nasa.gov/feed/','approved_metadata_trial','trial_active'),
 'boj-news':('boj','https://www.boj.or.jp/en/rss/whatsnew.xml','hold_commercial_permission','probe_only'),
 'ecb-press':('ecb','https://www.ecb.europa.eu/rss/press.html','hold_rights_review','probe_only'),
 'twse-news':('twse','','hold_reading_only','manual_review_only'),
}

def approved_config(config,live):
    if config.get('schema_version')!='0.4.4':raise ValueError('Candidate config version')
    if set(x.get('id') for x in config.get('candidates',[]))!=set(FROZEN) or len(config['candidates'])!=len(FROZEN):
        raise ValueError('Unexpected candidate sources')
    reviewed={s['id']:s for s in checked_sources(live)}
    by_id={x['id']:x for x in config['candidates']}
    for sid,(pub,url,rights,state) in FROZEN.items():
        row=by_id[sid]
        if (row.get('publisher_id')!=pub or row.get('feed_url')!=url or
            row.get('rights_status')!=rights or row.get('publish_status')!=state or
            not urlsplit(row['rights_url']).scheme=='https' or not row.get('reason')):
            raise ValueError('Source rights/host status was altered: '+sid)
        if state=='trial_active':
            if sid not in reviewed or reviewed[sid]['publisher_id']!=pub or reviewed[sid]['url']!=url:
                raise ValueError('Published source has not passed reviewed config: '+sid)
        elif sid in reviewed:
            raise ValueError('Unlicensed/review-only source must not be enabled: '+sid)
    return by_id

def build(config,live,fetcher=fetch_metadata,*,now=None):
    by_id=approved_config(config,live)
    started=now or datetime.now(timezone.utc).isoformat(timespec='seconds')
    rows=[]
    for sid in FROZEN:
        x=by_id[sid]; stage=x['publish_status']
        row={'id':sid,'publisher_id':x['publisher_id'],'name':x['name'],
          'category':x.get('category'),'stage':stage,'rights_status':x['rights_status'],
          'test_state':'not_attempted' if stage=='manual_review_only' else 'unavailable',
          'readable_entries':None,'error':None,'review_reference':x['rights_url'],
          'public_content_republished':False,'independent_confirmation':False}
        if stage!='manual_review_only':
            try:
                # Parse only in memory; do NOT serialize article text to the report.
                url=x['feed_url'];host=urlsplit(url).hostname
                data=fetcher({'id':sid,'url':url,'name':x['name'],
                    'publisher_id':x['publisher_id'],'kind':'official','category':x.get('category'),
                    'limit':8})
                if not isinstance(data,list):raise ValueError('Invalid probe result')
                row['test_state']='reachable_parsed'
                row['readable_entries']=len(data)
            except Exception as e:
                row['error']=(type(e).__name__+': '+str(e))[:180]
        rows.append(row)
    return {'meta':{'version':'0.4.4','status':'source_probing_not_news_verification',
        'rights_scope':'descriptive_public_metadata_only','generated_at':started,
        'candidate_publishers':len({x['publisher_id'] for x in rows}),
        'trial_active_sources':sum(x['stage']=='trial_active' for x in rows),
        'probe_only_sources':sum(x['stage']=='probe_only' for x in rows),
        'rights_held_sources':sum(x['rights_status'].startswith('hold_') for x in rows),
        'source_connection_successes':sum(x['test_state']=='reachable_parsed' for x in rows),
        'event_recall':None,'verified_claims':0,'importance_scores_created':0,
        'note':'新增來源技術探測不保留未授權標題、摘要或全文。狀態正常不表示取得內容重製授權或已獨立證實。'},
      'sources':rows}

def check_report(report):
    m=report.get('meta',{});rows=report.get('sources',[])
    if (m.get('version')!='0.4.4' or m.get('status')!='source_probing_not_news_verification'
        or m.get('rights_scope')!='descriptive_public_metadata_only' or m.get('event_recall') is not None
        or m.get('verified_claims')!=0 or m.get('importance_scores_created')!=0
        or len(rows)!=5 or {x.get('id') for x in rows}!=set(FROZEN)):
        raise RuntimeError('Invalid source admission report or fabricated performance')
    if m.get('trial_active_sources')!=2 or m.get('probe_only_sources')!=2 or m.get('rights_held_sources')!=3:
        raise RuntimeError('Rights gating metrics misreported')
    for x in rows:
        _,_,rights,stage=FROZEN[x['id']]
        if (x.get('stage')!=stage or x.get('rights_status')!=rights or
            x.get('public_content_republished') is not False or x.get('independent_confirmation') is not False or
            x.get('test_state') not in ('reachable_parsed','unavailable','not_attempted') or
            any(k in x for k in ('title','summary','article','body','headlines'))):
            raise RuntimeError('Unsafe source candidate metadata')
        if stage=='manual_review_only' and (x['test_state']!='not_attempted' or x['readable_entries'] is not None):
            raise RuntimeError('Reading-only TWSE must not be auto-probed')
    return True

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--candidates',default=str(ROOT/'data/v044_candidates.json'))
    ap.add_argument('--config',default=str(ROOT/'data/v034_sources.json'))
    ap.add_argument('--output',default=str(ROOT/'data/source_expansion_v044.json'))
    opts=ap.parse_args()
    config=json.loads(Path(opts.candidates).read_text(encoding='utf-8'))
    live=json.loads(Path(opts.config).read_text(encoding='utf-8'))
    report=build(config,live)
    check_report(report)
    atomic_json(Path(opts.output),report)
    print('V0.4.4: {} technical checks OK; {} rights held; no unsupported publication.'.format(
        report['meta']['source_connection_successes'],report['meta']['rights_held_sources']))
    return 0
if __name__=='__main__':raise SystemExit(main())
