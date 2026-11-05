#!/usr/bin/env python3
"""SIGNAL V0.3.1 — source governance gate.

Source registry is candidate publishers, NOT a list of approved API licenses.
`--production` refuses any active feed without explicit evidence of permission,
source signoff and live format test. Pilot retains legacy feeds with loud warnings.
No network, no external dependencies.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parents[1]
LEGACY_PILOT_IDS = frozenset({'fed-monetary','bls-latest','bbc-world','bbc-business','bbc-technology','bbc-science','hn-signal','arxiv-ai','arxiv-robotics','nasa-jpl'})

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def audit_registry(registry, config, production=False):
    pubs=registry.get('publishers', [])
    feeds=config.get('sources', [])
    errors=[];warnings=[]
    indexed={}
    known_priorities={'P0','P1','P2'}
    for p in pubs:
        key=p.get('publisher_id')
        if not key or key in indexed:
            errors.append(f'duplicate/missing publisher_id: {key}')
        indexed[key]=p
        if p.get('priority') not in known_priorities:
            errors.append(f'{key}: unknown priority')
        uri=p.get('reference_url','')
        u=urlsplit(uri)
        if u.scheme!='https' or not u.hostname or u.username or u.password:
            errors.append(f'{key}: missing secure reference URL')
        if p.get('automation_approved') and p.get('permission_status')!='approved':
            errors.append(f'{key}: automation_approved without permission approval')
    def valid_approval_evidence(obj):
        url=urlsplit(obj.get('permission_evidence_url') or '')
        return (url.scheme=='https' and bool(url.hostname)
                and bool(obj.get('permission_checked_at'))
                and bool(obj.get('approved_by'))
                and 'public_metadata' in (obj.get('approved_use_scope') or []))
    feed_ids=set(); publisher_counts=Counter(); active=0
    for f in feeds:
        sid=f.get('id')
        if not sid or sid in feed_ids:
            errors.append(f'duplicate/missing feed id: {sid}')
        feed_ids.add(sid)
        pid=f.get('publisher_id')
        if pid not in indexed:
            errors.append(f'{sid}: no parent publisher registered: {pid}')
            continue
        uri=urlsplit(f.get('url',''))
        if uri.scheme!='https' or not uri.hostname or uri.username or uri.password:
            errors.append(f'{sid}: insecure/unparseable feed URL')
        if not f.get('enabled', True):
            continue
        active+=1
        publisher_counts[pid]+=1
        p=indexed[pid]
        # Hard stop: not even pilots may silently claim a feed's material was verified.
        if f.get('claim_verified') is True:
            errors.append(f'{sid}: source titles must not be marked independently verified')
        authorized=(f.get('activation_status')=='approved'
                    and f.get('permission_status')=='approved'
                    and f.get('live_verified') is True
                    and p.get('permission_status')=='approved'
                    and p.get('automation_approved') is True
                    and valid_approval_evidence(f) and valid_approval_evidence(p)
                    and bool(f.get('live_tested_at')))
        if not authorized and sid not in LEGACY_PILOT_IDS:
            errors.append(f'{sid}: new feed cannot bypass rights/live review by selecting legacy_pilot')
        if production and not authorized:
            errors.append(f'{sid}: cannot enable in production; access/license/live-review missing')
        elif not authorized:
            warnings.append(f'{sid}: pilot only; automated-use terms and live test not yet cleared')
    for pid,count in publisher_counts.items():
        if count>=3:
            warnings.append(f'{pid}: {count} feeds but only ONE publisher; do not count as independent corroboration')
    if production and active==0:
        errors.append('production requires at least one authorized active feed')
    if not pubs:
        errors.append('empty candidate registry')
    if not feeds:
        errors.append('no feeds configured')
    by_layer=Counter(p['layer'].split('/')[0] for p in pubs)
    by_priority=Counter(p['priority'] for p in pubs)
    return {
        'schema_version':'0.3.1', 'mode':'production' if production else 'pilot',
        'publisher_candidates':len(pubs), 'active_feed_channels':active,
        'independent_active_publishers':len(publisher_counts),
        'publisher_coverage_by_layer':dict(by_layer), 'candidate_by_priority':dict(by_priority),
        'sources_requiring_review':len([f for f in feeds if f.get('enabled',True) and f.get('permission_status')!='approved']),
        'errors':errors, 'warnings':warnings,
        # The flag is conservative by design: unknown permissions == not approved.
        'approved_for_production':bool(production and not errors and active>0),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production',action='store_true',help='fail unless all enabled feeds have explicit legal and live access approval')
    parser.add_argument('--output',default='',help='optional audit JSON destination')
    args=parser.parse_args(argv)
    result=audit_registry(load(BASE/'data/source_registry.json'),load(BASE/'data/sources.json'),args.production)
    result['checked_at']=datetime.now(timezone.utc).isoformat(timespec='seconds')
    if args.output:
        out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('mode','publisher_candidates','active_feed_channels','independent_active_publishers','sources_requiring_review','approved_for_production','errors','warnings')},ensure_ascii=False,indent=2))
    return 1 if result['errors'] else 0

if __name__=='__main__':
    raise SystemExit(main())
