#!/usr/bin/env python3
"""V0.5.0: conservative DAILY REVIEW CANDIDATES (not verified news).

Input: audited title/link/time metadata from the existing V0.3.4 collector.
Output: a bounded, traceable, recency/diversity-sampled review queue.
No AI model, paid content, article body, fabricated importance rating, or claims of completeness.
"""
from __future__ import annotations
import argparse
from collections import Counter
import datetime as dt
import json
from pathlib import Path

from intelligence_v040 import ROOT, norm, verified_input, atomic_write

RIGHTS = 'descriptive_public_metadata_only'
MAX_DAILY = 8
MAX_PER_PUBLISHER = 2
MAX_PER_CATEGORY = 3

# These are editorial CHECK QUESTIONS for reviewing primary source material,
# not conclusions purportedly drawn from the article.
PROMPTS = {
    'official': '查核公告範圍、生效時間及是否存在後續修訂；官方發布不等於獨立驗證。',
    'research': '查核研究方法、實驗限制、是否通過同儕審查，以及可否獨立重現。',
    'institutional_news': '查核原始研究或產品文件，區分機構宣傳、客觀證據與商業化程度。',
}

def as_utc(raw):
    if not raw or not isinstance(raw, str):
        return None
    try:
        value = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        return None
    if value.tzinfo is None:
        return None
    return value.astimezone(dt.timezone.utc)

def valid_source_map(config):
    from collect_v034 import checked_sources
    return {src['id']:src for src in checked_sources(config)}

def build(live, config, quality=None, evidence=None, *, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None: raise ValueError('now must have timezone')
    now = now.astimezone(dt.timezone.utc)
    scope = live.get('meta', {}).get('rights_scope')
    if scope != RIGHTS or live.get('meta', {}).get('mode') != 'official_metadata':
        raise ValueError('Unapproved input metadata scope')
    allowed = valid_source_map(config)
    evidence_by_id={}
    if evidence:
        em=evidence.get('meta',{})
        if (em.get('rights_scope') != RIGHTS or em.get('status') != 'primary_metadata_enrichment_only'
            or em.get('verified_claims') != 0 or em.get('independently_confirmed_claims') != 0):
            raise ValueError('Invalid evidence level data')
        evidence_by_id={row.get('id'): row for row in evidence.get('items',[]) if isinstance(row,dict)}

    fresh=[];skipped_future=0;skipped_invalid_dates=0
    seen=set()
    for item in sorted(verified_input(live), key=lambda x:(x.get('published_at') or '', x.get('id','')), reverse=True):
        src=allowed.get(item['source_id'])
        if not src or src['publisher_id']!=item['publisher_id']:
            continue
        published=as_utc(item.get('published_at'))
        if published is None:
            skipped_invalid_dates+=1
            continue
        age=(now-published).total_seconds()
        if age < -3600:  # clock skew or incorrect published date, never frame as today's development
            skipped_future+=1
            continue
        if age > 7*86400:continue
        key=norm(item['title'])
        if not key or key in seen:continue
        seen.add(key)
        fresh.append((item,published,src))

    daily=[row for row in fresh if (now-row[1]).total_seconds()<=72*3600]
    selected=[];pubs=Counter();cats=Counter()
    for row,published,src in daily:
        pub=row['publisher_id'];cat=row.get('category') or '其他'
        if pubs[pub]>=MAX_PER_PUBLISHER or cats[cat]>=MAX_PER_CATEGORY:continue
        evid=evidence_by_id.get(row['id'],{})
        level='M0'
        if (evid.get('evidence_level')=='M0A' and evid.get('source_id')==row['source_id']
            and evid.get('publisher_id')==pub and evid.get('url')==row['url']
            and evid.get('title')==row['title'] and evid.get('metadata_title_match') is True
            and evid.get('independent_confirmation_count')==0 and evid.get('verification_status')=='未查證'):
            level='M0A'
        out={
            'id':row['id'], 'source_id':row['source_id'], 'publisher_id':pub,
            'source':row.get('source') or src['name'],
            'title':row['title'],'url':row['url'],'published_at':published.isoformat(timespec='seconds'),
            'category':cat,'source_kind':src['kind'],'evidence_level':level,
            'verification_status':'未查證','importance_assessed':False,
            'independent_confirmation':False,
            'review_prompt':PROMPTS.get(src['kind'],'先閱讀原始出處，再核對主要數據、限制與第三方證據。'),
        }
        selected.append(out);pubs[pub]+=1;cats[cat]+=1
        if len(selected)>=MAX_DAILY:break

    quality_status=(quality or {}).get('meta',{})
    if quality_status.get('status')!='input_coverage_diagnostic_only':
        empty_domains=None
    else:
        empty_domains=quality_status.get('domains_no_observed_publisher')
    last_success=as_utc(live.get('meta',{}).get('last_success_at'))
    staleness=(now-last_success).total_seconds()/3600 if last_success else None
    report={
        'meta':{
            'version':'0.5.0','generated_at':now.isoformat(timespec='seconds'),
            'type':'daily_review_candidates_not_a_news_brief',
            'rights_scope':RIGHTS,'input_mode':'official_metadata',
            'source_last_success_at':last_success.isoformat(timespec='seconds') if last_success else None,
            'source_age_hours':round(staleness,1) if staleness is not None else None,
            'stale_source':staleness is None or staleness > 48,
            'review_window_hours':72,'reference_window_days':7,
            'max_daily_candidates':MAX_DAILY,
            'daily_candidate_count':len(selected),'seven_day_source_titles':len(fresh),
            'daily_publishers':len(pubs),'active_configured_publishers':len({s['publisher_id'] for s in allowed.values()}),
            'uncovered_domains_in_source_audit':empty_domains,
            'invalid_dates_skipped':skipped_invalid_dates,'future_dates_skipped':skipped_future,
            'selection_rule':'published within 72h, publisher<=2, category<=3; newest first; not importance',
            'verified_claims':0,'independent_confirmations':0,
            'importance_scores_created':0,'global_event_recall':None,
            'ai_generated_factual_summaries':0,
            'notice':'這是近72小時可溯源元資料的「選讀候選」，非查證新聞、非全球重大事件排行、非投資建議；來源缺口與時效限制不可由 AI 補寫。'
        },
        'items':selected
    }
    return report

def validate(brief, live, config):
    meta=brief.get('meta',{})
    if not (meta.get('version')=='0.5.0' and meta.get('rights_scope')==RIGHTS
        and meta.get('type')=='daily_review_candidates_not_a_news_brief'
        and meta.get('verified_claims')==0 and meta.get('independent_confirmations')==0
        and meta.get('importance_scores_created')==0 and meta.get('global_event_recall') is None
        and meta.get('ai_generated_factual_summaries')==0):
        raise ValueError('Daily briefing makes unsupported claims')
    pub=Counter();cat=Counter();seen=set()
    byid={x['id']:x for x in verified_input(live)}
    sources=valid_source_map(config)
    generated=as_utc(meta.get('generated_at'))
    if not generated:raise ValueError('Invalid generation timestamp')
    items=brief.get('items',[])
    if not isinstance(items,list) or len(items)>MAX_DAILY or meta.get('daily_candidate_count')!=len(items):
        raise ValueError('Invalid daily candidate count')
    for x in items:
        original=byid.get(x.get('id'))
        src=sources.get(x.get('source_id'))
        if not original or not src or x['id'] in seen:raise ValueError('Unknown/duplicated source')
        seen.add(x['id'])
        if any(x.get(k)!=original.get(k) for k in ('url','title','source_id','publisher_id','category')):
            raise ValueError('Source provenance drift')
        if x.get('source_kind')!=src['kind'] or x.get('verification_status')!='未查證' or x.get('importance_assessed') is not False or x.get('independent_confirmation') is not False:
            raise ValueError('Misleading evidence status')
        if x.get('evidence_level') not in ('M0','M0A') or x.get('review_prompt')!=PROMPTS.get(src['kind'],'先閱讀原始出處，再核對主要數據、限制與第三方證據。'):
            raise ValueError('Unsupported review prompt')
        ts=as_utc(x.get('published_at'))
        age=(generated-ts).total_seconds() if ts else float('inf')
        if not -3600 <= age <= 72*3600:
            raise ValueError('Stale/future record presented as today')
        pub[x['publisher_id']]+=1;cat[x['category']]+=1
    if max(pub.values(),default=0)>MAX_PER_PUBLISHER or max(cat.values(),default=0)>MAX_PER_CATEGORY:
        raise ValueError('Source/category diversity guard failed')
    return True

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--live',default=str(ROOT/'data/live_items.json'))
    ap.add_argument('--sources',default=str(ROOT/'data/v034_sources.json'))
    ap.add_argument('--quality',default=str(ROOT/'data/source_quality_v043.json'))
    ap.add_argument('--evidence',default=str(ROOT/'data/evidence_enriched.json'))
    ap.add_argument('--output',default=str(ROOT/'data/daily_brief_v050.json'))
    args=ap.parse_args(argv)
    def load(path):
        p=Path(path)
        return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else {}
    doc=load(args.live);cfg=load(args.sources)
    output=build(doc,cfg,quality=load(args.quality),evidence=load(args.evidence))
    validate(output,doc,cfg)
    atomic_write(args.output,output)
    m=output['meta']
    print('V0.5.0 review preview: {} recent items, {} independent publishers, {} 7-day title candidates (not verified news)'.format(m['daily_candidate_count'],m['daily_publishers'],m['seven_day_source_titles']))

if __name__=='__main__':main()
