#!/usr/bin/env python3
"""SIGNAL V0.4.2 — conservative primary-evidence metadata enrichment.

Only enrich an arXiv *metadata* candidate with its matching abstract returned by
arXiv's official API. An author's abstract is a SELF-REPORTED description, NOT
an independent replication or verification. Other publishers remain at M0.

No paper PDFs, third-party news articles, or full-text extraction.
No AI, no importance/sentiment/investment scoring. Fail closed.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from evidence_v041 import ROOT, RIGHTS, load, write

ATOM = '{http://www.w3.org/2005/Atom}'
ARXIV_ABS_RE = re.compile(r'^https://(?:www\.)?arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?/?$')
API_HOST = 'export.arxiv.org'
API = 'https://export.arxiv.org/api/query'
MAX_BYTES=750_000
MAX_BATCH=8
MAX_ABSTRACT=4000


def paper_id(url):
    if not isinstance(url,str):return None
    m=ARXIV_ABS_RE.fullmatch(url)
    return m.group(1) if m else None


def normalized_title(s):
    return ' '.join(re.sub(r'[^\w]+',' ',s or '',flags=re.UNICODE).lower().split())


def parse_api_atom(payload, allowed_ids):
    if len(payload)>MAX_BYTES:raise ValueError('arXiv metadata reply is oversized')
    root=ET.fromstring(payload)
    if root.tag != ATOM+'feed':raise ValueError('Not an official Atom feed')
    found={}
    for entry in root.findall(ATOM+'entry'):
        rawid=(entry.findtext(ATOM+'id') or '').strip()
        # API can return http://arxiv.org/abs/..., but it must be an arXiv record.
        m=re.fullmatch(r'https?://(?:www\.)?arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?',rawid)
        if not m or m.group(1) not in allowed_ids:continue
        pid=m.group(1)
        title=' '.join((entry.findtext(ATOM+'title') or '').split())
        abstract=' '.join((entry.findtext(ATOM+'summary') or '').split())
        if not title or not abstract or len(abstract)>MAX_ABSTRACT:continue
        # This metadata is the author's self-report; no claim of independent review.
        if pid in found:continue
        found[pid]={'title':title,'abstract':abstract,'record_id':pid,
                    'record_url':'https://arxiv.org/abs/'+pid}
    return found


def fetch_arxiv_metadata(ids):
    if not ids:return {}
    if len(ids)>MAX_BATCH or len(ids)!=len(set(ids)) or not all(re.fullmatch(r'\d{4}\.\d{4,5}',x) for x in ids):
        raise ValueError('Invalid arXiv metadata batch')
    url=API+'?'+urllib.parse.urlencode({'id_list':','.join(ids),'max_results':len(ids)})
    req=urllib.request.Request(url,headers={
       'User-Agent':'SIGNAL-MetadataResearch/0.4.2 (https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3)',
       'Accept':'application/atom+xml,application/xml;q=0.9',
    })
    with urllib.request.urlopen(req,timeout=18) as resp:
        final=urllib.parse.urlsplit(resp.url)
        if resp.status!=200 or final.scheme!='https' or final.hostname!=API_HOST:
            raise ValueError('Unsafe API redirect or HTTP status')
        body=resp.read(MAX_BYTES+1)
    return parse_api_atom(body,set(ids))


def build(m0, previous, fetcher=fetch_arxiv_metadata, *, now=None, max_batch=MAX_BATCH):
    m=m0.get('meta',{})
    if (m.get('rights_scope')!=RIGHTS or m.get('status')!='metadata_gap_audit_only'
        or m.get('verified_claims')!=0 or m.get('independently_confirmed_claims')!=0):
        raise ValueError('Evidence base is not explicitly M0 only')
    old_by_id={x.get('id'):x for x in previous.get('items',[]) if isinstance(x,dict)}
    items=[];missing=[];ids=[]
    for src in m0.get('items',[]):
        if src.get('verification_status')!='未查證' or src.get('evidence_level')!='M0':
            raise ValueError('Unsafe source evidence elevation')
        row=dict(src);row.update({'evidence_level':'M0','body_read':False,'importance_assessed':False,
            'independent_confirmation_count':0,'peer_review_confirmed':False,
            'author_abstract':None,'metadata_read':False,'primary_source_kind':None,
            'original_document_verified':False,'verification_status':'未查證'})
        cached=old_by_id.get(src.get('id'))
        if (src.get('publisher_id')=='arxiv' and paper_id(src.get('url'))
            and cached and cached.get('fingerprint')==src.get('fingerprint')
            and cached.get('evidence_level')=='M0A' and cached.get('original_document_verified') is False
            and cached.get('independent_confirmation_count')==0
            and cached.get('verification_status')=='未查證'
            and cached.get('metadata_title_match') is True and cached.get('metadata_read') is True
            and paper_id(cached.get('metadata_record_url'))==paper_id(src.get('url'))
            and isinstance(cached.get('author_abstract'),str)
            and 0<len(cached['author_abstract'])<=MAX_ABSTRACT):
            row.update({k:cached.get(k) for k in ('author_abstract','metadata_read',
                'primary_source_kind','metadata_record_url','metadata_title_match','metadata_retrieved_at',
                'evidence_level','reading_scope')})
            row['reading_scope']='已取得 arXiv 官方 API 作者摘要元資料；未閱讀論文全文'
        elif src.get('publisher_id')=='arxiv' and paper_id(src.get('url')):
            missing.append((len(items),paper_id(src.get('url'))));ids.append(paper_id(src.get('url')))
        items.append(row)
    max_batch=max(0,min(MAX_BATCH,int(max_batch)))
    distinct=list(dict.fromkeys(ids))[:max_batch]
    errors=[];matched=0
    if distinct:
        try:
            fetched=fetcher(distinct)
            if not isinstance(fetched,dict):raise ValueError('Invalid arXiv API response')
            for index,pid in missing:
                if pid not in distinct:continue
                x=items[index];rec=fetched.get(pid)
                if (not isinstance(rec,dict) or rec.get('record_id')!=pid
                    or rec.get('record_url')!='https://arxiv.org/abs/'+pid
                    or not normalized_title(x['title'])
                    or normalized_title(rec.get('title'))!=normalized_title(x['title'])
                    or not isinstance(rec.get('abstract'),str)
                    or not (0<len(rec['abstract'])<=MAX_ABSTRACT)):
                    continue
                x.update({'evidence_level':'M0A','metadata_read':True,
                    'primary_source_kind':'arxiv_author_submitted_abstract_metadata',
                    'metadata_record_url':rec['record_url'],
                    'metadata_title_match':True,'author_abstract':rec['abstract'],
                    'metadata_retrieved_at':now or dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                    'reading_scope':'已取得 arXiv 官方 API 作者摘要元資料；未閱讀論文全文',
                    'original_document_verified':False,'verification_status':'未查證'})
                matched+=1
        except Exception as exc:
            errors.append((type(exc).__name__+': '+str(exc))[:150])
    # Cache may only carry M0A for same record id, title and fingerprint. Never claim M2.
    enriched=sum(x['evidence_level']=='M0A' for x in items)
    output={'meta':{
        'version':'0.4.2','generated_at':now or dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'rights_scope':RIGHTS,'status':'primary_metadata_enrichment_only',
        'candidate_count':len(items),'publisher_count':m.get('publisher_count',0),
        'm0_count':len(items)-enriched,'m0a_count':enriched,'fetched_in_run':matched,
        'api_queries_this_run':int(bool(distinct)),'api_errors':errors,
        'verified_claims':0,'independently_confirmed_claims':0,'read_bodies':0,'importance_assessments':0,
        'coverage_warning':m.get('coverage_warning'),
        'note':'M0A 只代表已核對 arXiv 官方 API 的作者投稿摘要元資料。不是全文、同儕審查、獨立重現或主張驗證。Fed/BEA 仍在 M0。',
        'rights_note':'arXiv 描述性元資料依官方 CC0 政策；不讀取或轉載各論文 PDF／圖表。',
        'limitations':['三家發布主體無法構成全球覆蓋','arXiv 摘要為作者自述','無獨立佐證','未給予全球重要性或投資評分'],
    },'items':items}
    return output


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',default=str(ROOT/'data/evidence_audit.json'))
    ap.add_argument('--previous',default=str(ROOT/'data/evidence_enriched.json'))
    ap.add_argument('--output',default=str(ROOT/'data/evidence_enriched.json'))
    ap.add_argument('--max-new',type=int,default=8)
    ap.add_argument('--offline',action='store_true',help='Skip network, retain verified matching previous metadata only')
    args=ap.parse_args(argv)
    def no_fetch(_):return {}
    m0=load(args.input,{})
    # The collector previously queries the arXiv RSS channels: preserve the
    # official one-request-per-three-seconds limit across RSS + legacy API.
    if not args.offline and args.max_new>0 and any(
        x.get('publisher_id')=='arxiv' and paper_id(x.get('url'))
        for x in m0.get('items',[])):
        time.sleep(4.0)
    out=build(m0,load(args.previous,{}),fetcher=no_fetch if args.offline else fetch_arxiv_metadata,max_batch=0 if args.offline else args.max_new)
    write(args.output,out)
    print('V0.4.2 primary metadata: M0A={} M0={} new={} api_error={} verified=0'.format(
        out['meta']['m0a_count'],out['meta']['m0_count'],out['meta']['fetched_in_run'],len(out['meta']['api_errors'])))
    return 0

if __name__=='__main__':raise SystemExit(main())
