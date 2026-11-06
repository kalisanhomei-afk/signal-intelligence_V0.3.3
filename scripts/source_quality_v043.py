#!/usr/bin/env python3
"""SIGNAL V0.4.3: independently auditable *input coverage* diagnostics.

This NEVER decides which real-world events are important, establishes a claim as
true, or claims a global recall rate from a small RSS source pool. Profiles are
capabilities of four rights-reviewed input channels, not audience reach.

Manual benchmark IDs are optional; exact primary URL overlaps are merely
candidate matches and do not independently verify an event.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from evidence_v041 import ROOT,RIGHTS,load,write

DIMENSIONS=(
 ('us_macro','美國貨幣政策與經濟統計',('fed','bea')),
 ('ai_preprint','AI／機器人研究預印本',('arxiv',)),
 ('world_politics','全球政治與外交事件',('eu_commission',)),
 ('industry','企業／產業與商業模式',()),
 ('engineering','工程產品／量產與技術商業化',('nasa','mit_news')), 
 ('energy','能源與商品市場',('eia',)),
 ('taiwan','台灣本地經濟／政治／科技',()),
 ('japan','日本經濟／產業／政策',()),
 ('brazil','巴西經濟／產業／政策',()),
 ('society','社會／公共衛生／教育',()),
)
# Source ID -> publisher authority is from the *existing rights-reviewed*
# V0.3.4 source allowlist; its independent source count comes from publisher_id.

def parse_time(value):
    if not isinstance(value,str) or not value:return None
    try:
        t=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        return t.astimezone(dt.timezone.utc) if t.tzinfo else None
    except ValueError:return None


def normalize_url(value):
    if not isinstance(value,str):return None
    try:
        p=urlsplit(value)
        if p.scheme!='https' or not p.hostname or p.username or p.password:return None
        host=p.hostname.lower()
        # Tracking parameters are intentionally ignored for *candidate* URL overlap.
        # Different documents / hosts must not be considered a match.
        return urlunsplit(('https',host,p.path.rstrip('/') or '/', '', ''))
    except ValueError:return None


def ensure_unverified(doc, expected_status):
    meta=doc.get('meta',{})
    if meta.get('rights_scope')!=RIGHTS or meta.get('status')!=expected_status:
        raise ValueError('Input evidence is not approved for coverage diagnostics')
    if any(meta.get(k,0)!=0 for k in ('verified_claims','independently_confirmed_claims','importance_assessments')):
        raise ValueError('Unjustified verification/importance promotion')


def build(live, evidence, channels, benchmark, *,now=None):
    if live.get('meta',{}).get('rights_scope')!=RIGHTS or live.get('meta',{}).get('mode')!='official_metadata':
        raise ValueError('Unapproved source data')
    ensure_unverified(evidence,'primary_metadata_enrichment_only')
    if channels.get('review_scope')!=RIGHTS:
        raise ValueError('Source configuration is not rights-reviewed')
    allowed={}
    for src in channels.get('sources',[]):
        if src.get('status')!='metadata_only' or src.get('id') in allowed or not src.get('publisher_id'):
            raise ValueError('Invalid or duplicated approved channel')
        allowed[src['id']]=src['publisher_id']
    if not allowed:raise ValueError('No approved source channel')
    now_dt=parse_time(now) if now else dt.datetime.now(dt.timezone.utc)
    if not now_dt:raise ValueError('Invalid time')
    rows=[];publisher_counts=defaultdict(int);source_counts=defaultdict(int);latest={}
    seen=set()
    for x in live.get('items',[]):
        if (not isinstance(x,dict) or x.get('source_id') not in allowed or
            x.get('publisher_id')!=allowed[x['source_id']] or
            x.get('summary') is not None or not normalize_url(x.get('url'))):
            raise ValueError('Unapproved or unsafe input item')
        if not x.get('id') or x['id'] in seen:raise ValueError('Missing or duplicate item ID')
        seen.add(x['id']);rows.append(x)
        source_counts[x['source_id']]+=1
        pub=x['publisher_id'];publisher_counts[pub]+=1
        when=parse_time(x.get('published_at'))
        if when and (pub not in latest or when>latest[pub]):latest[pub]=when
    evid_ids={x.get('id') for x in evidence.get('items',[]) if isinstance(x,dict)}
    if not evid_ids.issubset(seen):
        raise ValueError('Evidence must refer to an existing approved source item')
    for x in evidence.get('items',[]):
        if x.get('independent_confirmation_count')!=0 or x.get('verification_status')!='未查證':
            raise ValueError('Unsupported confirmation')
    publishers=set(publisher_counts)
    status=[]
    for key,label,capable in DIMENSIONS:
        observed=sorted(publishers.intersection(capable))
        status.append({'key':key,'label':label,'observed_publishers':observed,
                       'observed_publisher_count':len(observed),
                       'source_status':'no_reviewed_publisher_observed' if not observed else
                           ('single_publisher_only' if len(observed)==1 else 'multiple_publishers_not_same_claim'),
                       'claim_coverage_confirmed':False})
    seen_urls={normalize_url(x['url']) for x in rows}
    # Not a verified independent benchmark. Only manual, cited, specifically
    # reviewed entries qualify; unknown URLs are *not* proof of an omission.
    refs=benchmark.get('events',[])
    if not isinstance(refs,list):raise ValueError('Malformed benchmark')
    manual=[];keys=set()
    for e in refs:
        if not isinstance(e,dict):raise ValueError('Invalid benchmark row')
        k=e.get('id');url=normalize_url(e.get('original_url'))
        if not isinstance(k,str) or not k.strip() or k in keys or not url:
            raise ValueError('Missing ID / unsafe benchmark URL')
        keys.add(k)
        if e.get('human_reviewed') is not True or not e.get('reviewed_by') or not parse_time(e.get('reviewed_at')):
            raise ValueError('Benchmark items require recorded human verification')
        manual.append({'id':k,'title':str(e.get('title',''))[:200],
                       'original_url':e['original_url'],
                       'url_overlap':url in seen_urls,
                       'result':'same_primary_url_found' if url in seen_urls else 'not_same_url_manual_review_needed'})
    refreshed=live.get('meta',{}).get('last_success_at')
    last_success=parse_time(refreshed)
    latest_by_pub=[{'publisher_id':p,'item_count':publisher_counts[p],
                    'last_item_published_at':latest[p].isoformat() if p in latest else None,
                    'age_days_of_newest_item':round(max(0,(now_dt-latest[p]).total_seconds())/86400,1) if p in latest else None}
                   for p in sorted(publishers)]
    return {'meta':{
      'version':'0.4.3','generated_at':now_dt.isoformat(timespec='seconds'),
      'status':'input_coverage_diagnostic_only','rights_scope':RIGHTS,
      'observed_items':len(rows),'approved_channels':len(allowed),
      'observed_channels':len(source_counts),'observed_publishers':len(publishers),
      'publisher_ids':sorted(publishers),'last_collection_success_at':refreshed,
      'collection_last_success_age_hours':round(max(0,(now_dt-last_success).total_seconds())/3600,1) if last_success else None,
      'domains_no_observed_publisher':sum(x['observed_publisher_count']==0 for x in status),
      'domains_single_publisher':sum(x['observed_publisher_count']==1 for x in status),
      'benchmarked_event_count':len(manual),
      'benchmark_status':'not_measured_no_reference' if not manual else 'exact_url_overlap_only_not_event_recall',
      'global_news_recall':None,'benchmark_event_recall':None,'importance_scores_created':0,
      'verified_claims':0,'independently_confirmed_claims':0,'independent_corrob_evidence_items':0,
      'note':'僅診斷已接入資料來源的領域覆蓋與候選資料；不能量測全球重要新聞遺漏率或宣稱任何主張已驗證。',
      'anti_echo_warning':'多個 RSS 頻道若來自同一發布機構，不等於多個獨立證據。',
      'source_limitations':['配置已新增 EIA/NASA 官方 RSS，但須依本次來源狀態確認實際讀取成功','歐盟政策與 MIT 機構新聞可作為一手線索，但仍缺獨立國際媒體、商業產業情報及台日巴正式採集來源','不能用 AI 推論補齊未蒐集消息']
     },'dimensions':status,'publisher_activity':latest_by_pub,
     'benchmark_candidates':manual,
     'next_actions':[
        '先完成重要領域與不同地域的合法來源接入審核，不以付費/免費作為品質標準',
        '由人工建立有日期、原始連結與審查者的重大事件基準清單，才有資格量測遺漏',
        '跨發布機構的相同主張須拆解成可核對內容，不得僅以文章數量當作獨立佐證'
      ]}


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--live',default=str(ROOT/'data/live_items.json'))
    ap.add_argument('--evidence',default=str(ROOT/'data/evidence_enriched.json'))
    ap.add_argument('--sources',default=str(ROOT/'data/v034_sources.json'))
    ap.add_argument('--reference',default=str(ROOT/'data/quality_reference_events.json'))
    ap.add_argument('--output',default=str(ROOT/'data/source_quality_v043.json'))
    args=ap.parse_args(argv)
    output=build(load(args.live,{}),load(args.evidence,{}),load(args.sources,{}),load(args.reference,{'events':[]}))
    write(args.output,output)
    m=output['meta']
    print('V0.4.3 source coverage: publishers={} empty_domains={} benchmark={} (NOT global recall)'.format(
        m['observed_publishers'],m['domains_no_observed_publisher'],m['benchmark_status']))
    return 0
if __name__=='__main__':raise SystemExit(main())
