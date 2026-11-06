#!/usr/bin/env python3
"""SIGNAL V0.5.1: external-reference benchmark and human-adjudicated capture diagnostic.

DO NOT transform search results/old headlines into 'verified importance' or global recall.
A source-page anchor is a candidate; human review and explicit match review are mandatory.
All candidate suggestions are non-scoring. Missing matches without adjudication are UNKNOWN.
"""
from __future__ import annotations
import argparse
import datetime as dt
import difflib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
from daily_candidate_v050 import as_utc
from intelligence_v040 import ROOT, atomic_write, norm, verified_input

RIGHTS = 'descriptive_public_metadata_only'
MIN_EVENTS = 20
MIN_DOMAINS = 5
MIN_REGIONS = 3
MAX_PUBLIC_CANDIDATES = 30


def iso_datetime(value):
    return as_utc(value)


def url_ok(value):
    if not isinstance(value,str):return False
    try:
        parts=urlsplit(value)
        return parts.scheme=='https' and bool(parts.hostname) and not parts.username and not parts.password
    except ValueError:return False


def date_only(value):
    if not isinstance(value,str):return None
    try:
        date=dt.date.fromisoformat(value)
        if date.isoformat()!=value:return None
        return date
    except ValueError:return None


def is_index_only(url):
    # These are useful for discovery, but insufficient to verify one specific event.
    p=urlsplit(url)
    stem=p.path.lower().rstrip('/')
    return any(x in stem for x in (
        '/news/schedule','/whatsnew','/state_2026','/2026-press',
        '/monetarypolicy.htm','/press/press-releases','/tw/lp-'
    )) or stem.endswith('/news')

def normalized_url(value):
    if not url_ok(value):return ''
    p=urlsplit(value)
    return f'{p.hostname.lower()}{p.path.rstrip("/") or "/"}'


def check_seed(seed):
    if seed.get('schema_version')!='0.5.1' or not isinstance(seed.get('events'),list):
        raise ValueError('Incorrect V0.5.1 benchmark schema')
    seen=set()
    for e in seed['events']:
        if not isinstance(e,dict):raise ValueError('Event must be object')
        eid=e.get('id')
        if not isinstance(eid,str) or not eid or eid in seen:raise ValueError('Missing/repeated benchmark event ID')
        seen.add(eid)
        if (not date_only(e.get('date')) or not url_ok(e.get('reference_url'))
            or any(not isinstance(e.get(f),str) or not e[f].strip() for f in
                   ('title','domain','region','reference_publisher','editorial_question'))):
            raise ValueError(f'Unusable original evidence for {eid}')
        state=e.get('review_status')
        if state not in ('pending','approved','rejected'):
            raise ValueError('Unknown benchmark review status')
        match=e.get('match_status')
        if match not in ('pending','confirmed_present','confirmed_absent'):
            raise ValueError('Unknown coverage adjudication state')
        if state!='approved' and match!='pending':
            raise ValueError('Cannot match an unapproved candidate')
        if state=='approved':
            if (not e.get('evidence_audited') or not e.get('reviewed_by') or not iso_datetime(e.get('reviewed_at'))
                or len(e.get('impact_justification','').strip())<12):
                raise ValueError('Gold event requires primary-source audit, human identity, timestamp, and importance rationale')
            if is_index_only(e['reference_url']):
                raise ValueError('Index/schedule is not enough to approve a specific event; replace with direct evidence URL')
        if match!='pending':
            if state!='approved' or not e.get('match_reviewed_by') or not iso_datetime(e.get('match_reviewed_at')) or len(e.get('match_note','').strip())<12:
                raise ValueError('Confirmed presence/absence requires human adjudication and explanatory note')
            if match=='confirmed_present' and not e.get('match_item_id'):
                raise ValueError('Confirmed presence needs exact SIGNAL item ID')
            if match=='confirmed_absent' and e.get('match_item_id'):
                raise ValueError('Absent item cannot carry a matched ID')
    return True


def suggestions(event,live_items,top=3):
    """Low-trust candidate hints only. Never count similarity as a genuine match."""
    out=[]
    title=norm(event['title'])
    event_day=date_only(event['date'])
    for item in live_items:
        pub_day=iso_datetime(item.get('published_at'))
        if pub_day is None or abs((pub_day.date()-event_day).days)>10:
            continue
        score=difflib.SequenceMatcher(None,title,norm(item.get('title',''))).ratio()
        exact_url=normalized_url(item.get('url'))==normalized_url(event['reference_url'])
        if exact_url or score>=0.63:
            out.append({'item_id':item['id'],'title':item['title'],'publisher_id':item['publisher_id'],
                        'possible_same_url':exact_url,'title_similarity_hint':round(score,2)})
    return sorted(out,key=lambda x:(x['possible_same_url'],x['title_similarity_hint']),reverse=True)[:top]


def build(seed,live,daily,*,now=None,_checking=False):
    now=now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:raise ValueError('now must be timezone-aware')
    now=now.astimezone(dt.timezone.utc)
    check_seed(seed)
    lmeta=live.get('meta',{})
    dmeta=daily.get('meta',{})
    if (lmeta.get('rights_scope')!=RIGHTS or lmeta.get('mode')!='official_metadata'
        or dmeta.get('rights_scope')!=RIGHTS or dmeta.get('type')!='daily_review_candidates_not_a_news_brief'
        or dmeta.get('verified_claims')!=0 or dmeta.get('independent_confirmations')!=0
        or dmeta.get('global_event_recall') is not None):
        raise ValueError('Unsafe or missing provenance in comparison inputs')
    live_items=verified_input(live)
    by_id={item['id']:item for item in live_items}
    daily_ids={x.get('id') for x in daily.get('items',[])}
    if any(itemid not in by_id for itemid in daily_ids):
        raise ValueError('Daily item missing from captured feed')

    approved=[]; adjudicated=[];present=[];absent=[]
    eligible_daily=[];daily_selected=[]
    rows=[];domains=Counter();regions=Counter();outside_capture=0
    start=(now-dt.timedelta(days=45)).date()
    for e in seed['events'][:MAX_PUBLIC_CANDIDATES]:
        day=date_only(e['date'])
        approved_event=e['review_status']=='approved'
        in_capture_window=start<=day<=now.date()
        age_hours=(now-dt.datetime.combine(day,dt.time(23,59),tzinfo=dt.timezone.utc)).total_seconds()/3600
        in_daily_window=age_hours<=72 and age_hours>=-24
        if approved_event:
            approved.append(e);domains[e['domain']]+=1;regions[e['region']]+=1
            if not in_capture_window:outside_capture+=1
        status='待人工審閱'
        if e['review_status']=='rejected':status='已排除'
        elif approved_event:
            status='基準已審；尚待核對'
            if not in_capture_window:status='基準日期超出保存窗'
            if e['match_status']!='pending' and in_capture_window:
                adjudicated.append(e)
                if e['match_status']=='confirmed_present':
                    item=by_id.get(e['match_item_id'])
                    if item is None:raise ValueError('Human matched item ID not in current source history')
                    pub=iso_datetime(item.get('published_at'))
                    if pub is None or abs((pub.date()-day).days)>10:
                        raise ValueError('Human match has implausible event-time mismatch')
                    present.append(e)
                    status='人工確認已收錄'
                    if in_daily_window:
                        eligible_daily.append(e)
                        if e['match_item_id'] in daily_ids:
                            daily_selected.append(e)
                else:
                    absent.append(e);status='人工確認未收錄'
                    if in_daily_window:eligible_daily.append(e)
        rows.append({
            'id':e['id'],'date':e['date'],'title':e['title'],'domain':e['domain'],'region':e['region'],
            'reference_publisher':e['reference_publisher'],'reference_url':e['reference_url'],
            'editorial_question':e['editorial_question'],'review_status':e['review_status'],
            'matching_status':status,'benchmark_approved':approved_event,
            'in_45_day_history_window':in_capture_window,
            'reviewed_match':approved_event and in_capture_window and e['match_status']!='pending',
            'suggestions_not_verified':suggestions(e,live_items),
        })
    concentration=max(domains.values(),default=0)/len(approved) if approved else None
    threshold_met=(len(approved)>=MIN_EVENTS and len(adjudicated)>=MIN_EVENTS and
                   len(domains)>=MIN_DOMAINS and len(regions)>=MIN_REGIONS and outside_capture==0
                   and concentration is not None and concentration<=0.35)
    reviewed_capture=(round(100*len(present)/len(adjudicated),1) if threshold_met else None)
    daily_comparison=(round(100*len(daily_selected)/len(eligible_daily),1)
                      if threshold_met and len(eligible_daily)>=5 else None)
    # Fair comparison against newest-eight under the SAME 72h time window, with no importance claim.
    eligible_recent_items=[]
    for item in live_items:
        ts=iso_datetime(item.get('published_at'))
        if ts and 0<=(now-ts).total_seconds()<=72*3600:
            eligible_recent_items.append((ts,item['id']))
    latest_eight={itemid for timestamp,itemid in sorted(eligible_recent_items,reverse=True)[:8]}
    baseline_hits=sum(x['match_status']=='confirmed_present' and x['match_item_id'] in latest_eight
                      for x in eligible_daily)
    recency_baseline=(round(100*baseline_hits/len(eligible_daily),1)
                      if threshold_met and len(eligible_daily)>=5 else None)
    # This is purposely not a global recall or a machine-verified news accuracy score.
    result={'meta':{
        'version':'0.5.1','status':'human_reviewed_reference_benchmark_only',
        'generated_at':now.isoformat(timespec='seconds'),
        'rights_scope':RIGHTS,'global_news_recall':None,'overall_news_importance_accuracy':None,
        'verified_claims':0,'independent_confirmations':0,'ai_importance_scores':0,
        'gold_candidate_total':len(seed['events']),
        'reference_candidates_displayed':len(rows),'approved_benchmark_events':len(approved),
        'match_adjudications_within_retention':len(adjudicated),
        'reviewed_present':len(present),'reviewed_absent':len(absent),
        'reviewed_daily_eligible':len(eligible_daily),'reviewed_daily_selected':len(daily_selected),
        'approved_domains':len(domains),'approved_regions':len(regions),
        'largest_domain_share':round(concentration,3) if concentration is not None else None,
        'largest_domain_limit':0.35,
        'date_outside_retention':outside_capture,
        'minimum_approved_events':MIN_EVENTS,'minimum_domains':MIN_DOMAINS,'minimum_regions':MIN_REGIONS,
        'benchmark_ready':threshold_met,'audited_sample_capture_rate':reviewed_capture,
        'audited_daily_selection_rate':daily_comparison,
        'audited_recency_only_selection_rate':recency_baseline,
        'notice':'官方網頁標題已獨立整理成待審候選，不等於「重要事件」已核准。只有人工審定、人工判定匹配且跨足夠領域與地區，才允許顯示樣本命中率；永不等同全球重大事件召回率。'
    },'events':rows}
    if not _checking:
        validate(result,seed,live,daily)
    return result


def validate(out,seed,live,daily):
    check_seed(seed)
    meta=out.get('meta',{})
    if (meta.get('rights_scope')!=RIGHTS or meta.get('global_news_recall') is not None
        or meta.get('overall_news_importance_accuracy') is not None
        or any(meta.get(k)!=0 for k in ('verified_claims','independent_confirmations','ai_importance_scores'))):
        raise ValueError('Misleading claims in benchmark audit')
    if len(out.get('events',[]))!=min(len(seed['events']),MAX_PUBLIC_CANDIDATES):
        raise ValueError('Bad benchmark event count')
    seen={e['id']:e for e in seed['events']}
    for item in out['events']:
        ref=seen.get(item.get('id'))
        if not ref or any(item.get(k)!=ref.get(k) for k in
                          ('date','title','domain','region','reference_url','reference_publisher','review_status')):
            raise ValueError('Reference event contamination')
        if not url_ok(item['reference_url']):raise ValueError('Insecure reference URL')
        if not isinstance(item.get('suggestions_not_verified'),list):raise ValueError('Invalid hint list')
    if not meta.get('benchmark_ready'):
        if (meta.get('audited_sample_capture_rate') is not None or meta.get('audited_daily_selection_rate') is not None
            or meta.get('audited_recency_only_selection_rate') is not None):
            raise ValueError('Premature audited sample score')
    if meta.get('approved_benchmark_events')>len(seed['events']):raise ValueError('Approval count overrun')
    generated=iso_datetime(meta.get('generated_at'))
    if not generated:raise ValueError('Missing benchmark time')
    canonical=build(seed,live,daily,now=generated,_checking=True)
    if out != canonical:
        raise ValueError('Generated benchmark claims diverge from audited inputs')
    return True


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--candidates',default=str(ROOT/'data/benchmark_candidates_v051.json'))
    ap.add_argument('--live',default=str(ROOT/'data/live_items.json'))
    ap.add_argument('--daily',default=str(ROOT/'data/daily_brief_v050.json'))
    ap.add_argument('--output',default=str(ROOT/'data/benchmark_audit_v051.json'))
    args=ap.parse_args()
    load=lambda path:json.loads(Path(path).read_text(encoding='utf-8'))
    doc=build(load(args.candidates),load(args.live),load(args.daily))
    atomic_write(args.output,doc)
    m=doc['meta']
    print(f'V0.5.1 audit: candidate references={m["gold_candidate_total"]}, human approved={m["approved_benchmark_events"]}, match adjudicated={m["match_adjudications_within_retention"]}, global recall=NOT CLAIMED')

if __name__=='__main__':main()
