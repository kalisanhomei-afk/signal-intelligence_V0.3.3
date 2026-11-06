#!/usr/bin/env python3
"""SIGNAL V0.5.4: MANUAL pilot, bounded evidence extraction from 3 first-party sources.

No publishing to GitHub Pages. No broad crawling, no PDFs, no paywalls, no 3rd-party
articles. Excerpts are only review leads, NOT independently verified claims.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
from html import unescape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

from intelligence_v040 import ROOT, atomic_write, norm
from impact_review_v052 import validate as validate_review
from evidence_v042 import fetch_arxiv_metadata, paper_id, normalized_title

VERSION='0.5.4'
MAX_BYTES=1_200_000
MAX_SPANS=9
MAX_SPAN_CHARS=360
MAX_AGE_DAYS=30
# Three specific articles used in the V0.5.3 paid pilot; avoid silently changing
# the comparison group merely because newer headlines entered the feed.
PINNED_URLS={
 'bea':'https://www.bea.gov/news/2026/us-international-trade-goods-and-services-september-2026',
 'eia':'https://www.eia.gov/todayinenergy/detail.php?id=68424',
 'arxiv':'https://arxiv.org/abs/2611.05567',
}
ALLOWED={
 'bea-news':('bea','www.bea.gov',r'/news/20\d{2}/[a-z0-9\-]+','html'),
 'eia-energy':('eia','www.eia.gov',r'/todayinenergy/detail\.php','html'),
 'arxiv-robotics':('arxiv','arxiv.org',r'/abs/\d{4}\.\d{4,5}','arxiv_api'),
 'arxiv-ai':('arxiv','arxiv.org',r'/abs/\d{4}\.\d{4,5}','arxiv_api'),
}
SKIP_TAGS={'script','style','nav','footer','header','aside','noscript','svg','form'}
BLOCKS={'p','li','h1','h2','h3','tr'}
NUMBER=re.compile(r'\b(?:\d[\d,]*(?:\.\d+)?%?)\b')
THEMES=('trade','deficit','surplus','imports','exports','refiner','gasoline','distillat',
        'jet fuel','production','million','billion','percent','robot','evaluation',
        'benchmark','models','dataset','results','research','year','increase','decrease')


def allowed_link(row):
    sid=row.get('source_id');spec=ALLOWED.get(sid)
    if not spec or row.get('publisher_id')!=spec[0]:return None
    p=urlsplit(row.get('url',''))
    if (p.scheme!='https' or p.hostname!=spec[1] or p.port is not None or p.username
        or p.password or p.fragment or not re.fullmatch(spec[2],p.path)):
        return None
    if sid=='eia-energy' and not re.fullmatch(r'id=\d{3,7}',p.query):return None
    if sid!='eia-energy' and p.query:return None
    return spec[3]


class SameHostRedirect(HTTPRedirectHandler):
    def __init__(self,host):self.host=host
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        p=urlsplit(newurl)
        if p.scheme!='https' or p.hostname!=self.host or p.username or p.password:
            raise ValueError('Redirect outside reviewed publisher')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def fetch_html(row):
    if allowed_link(row)!='html':raise ValueError('Source URL is not on HTML allowlist')
    p=urlsplit(row['url']);opener=build_opener(SameHostRedirect(p.hostname))
    req=Request(row['url'],headers={
        'User-Agent':'SIGNAL-evidence-review/0.5.4 (manual official-publication pilot)',
        'Accept':'text/html,application/xhtml+xml;q=0.8',
    })
    with opener.open(req,timeout=15) as response:
        final=urlsplit(response.url);ctype=response.headers.get('Content-Type','')
        if (response.status!=200 or final.scheme!='https' or final.hostname!=p.hostname
            or 'html' not in ctype.lower()):raise ValueError('Unsafe response, redirect, or content type')
        body=response.read(MAX_BYTES+1)
    if len(body)>MAX_BYTES:raise ValueError('Document exceeds evidence pilot limit')
    return body.decode('utf-8',errors='replace')


class Paragraphs(HTMLParser):
    """Extract visible text blocks. Prefer main/article blocks; retain fallback blocks."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[];self.active=[];self.sections=[];self.general=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        parent_skip=any(x[1] for x in self.stack)
        skip=parent_skip or tag in SKIP_TAGS
        main=bool(attrs.get('role')=='main' or tag in ('main','article')
                  or attrs.get('id') in ('main-content','main','content-main')
                  or attrs.get('class','').find('main-content')>=0)
        parent_main=any(x[2] for x in self.stack)
        self.stack.append((tag,skip,main or parent_main))
        if tag in BLOCKS and not skip:
            self.active.append({'tag':tag,'main':main or parent_main,'text':[],'depth':len(self.stack)})
    def handle_data(self,data):
        if not self.stack or any(x[1] for x in self.stack):return
        for block in self.active:block['text'].append(data)
    def handle_endtag(self,tag):
        # Close the matching tag and any malformed nested tags safely.
        found=-1
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:found=i;break
        if found<0:return
        while self.active and self.active[-1]['depth']>=found+1:
            block=self.active.pop()
            text=' '.join(''.join(block['text']).split())
            if 24<=len(text)<=2000:
                (self.sections if block['main'] else self.general).append((block['tag'],text))
        self.stack=self.stack[:found]


def extract_html_spans(raw,title):
    p=Paragraphs();p.feed(raw);p.close()
    all_rows=p.sections if len(p.sections)>=3 else p.sections+p.general
    # Headline containment avoids accepting a cookie/redirect/access denied page.
    combined=' '.join(text for _,text in p.sections+p.general)
    needle=re.sub(r'[^\w\u4e00-\u9fff]','',title.casefold())
    haystack=re.sub(r'[^\w\u4e00-\u9fff]','',combined.casefold())
    if not needle or (needle not in haystack and needle not in re.sub(
            r'[^\w\u4e00-\u9fff]','',unescape(re.sub(r'<[^>]*>',' ',raw)).casefold())):
        raise ValueError('Document heading/title not matched to metadata')
    # Selection is an extractive reading aid: prioritize numeric and relevant blocks.
    scored=[];seen=set()
    for i,(tag,text) in enumerate(all_rows):
        if tag.startswith('h'):continue
        if text in seen or len(text)<45:continue
        if text.lower().startswith(('browse by tag ', 'tags:',
            'exploration and reserves, storage,',
            'reserves, production, prices, employment')):continue
        seen.add(text)
        low=text.lower()
        if any(t in low for t in ('privacy policy','subscribe to','sign up for','cookie policy','accessibility')):
            continue
        relevance=sum(w in low for w in THEMES)
        digits=bool(NUMBER.search(text))
        score=(4 if digits else 0)+min(relevance,5)*2-max(0,i-20)//30
        if score<2:continue
        scored.append((score,i,text))
    scored.sort(key=lambda x:(-x[0],x[1]))
    picked=sorted(scored[:MAX_SPANS],key=lambda x:x[1])
    return [x[2][:MAX_SPAN_CHARS].strip() for x in picked]


def split_abstract(abstract, max_chunks=6):
    """Preserve short author abstract sections without claiming to have read the PDF."""
    text=' '.join(abstract.split())[:1800]
    sentences=re.split(r'(?<=[.!?])\s+',text)
    chunks=[];current=''
    for sentence in sentences:
        if not sentence:continue
        if current and len(current)+1+len(sentence)>MAX_SPAN_CHARS:
            chunks.append(current);current=''
        if len(sentence)>MAX_SPAN_CHARS:
            if current:chunks.append(current);current=''
            while len(sentence)>MAX_SPAN_CHARS:
                cut=sentence.rfind(' ',0,MAX_SPAN_CHARS)
                if cut<120:cut=MAX_SPAN_CHARS
                chunks.append(sentence[:cut]);sentence=sentence[cut:].lstrip()
        current=(' '.join([current,sentence])).strip()
        if len(chunks)>=max_chunks:break
    if current and len(chunks)<max_chunks:chunks.append(current)
    return chunks[:max_chunks]


def evidence_spans(texts):
    return [{'id':f'E{i}','text':t,
             'sha256':hashlib.sha256(t.encode('utf-8')).hexdigest()} for i,t in enumerate(texts,1)]


def validate_base(review,live,sources,enriched):
    validate_review(review,live,sources,enriched)
    if review.get('meta',{}).get('ai_enabled') or any(x.get('ai_draft') for x in review['items']):
        raise ValueError('V0.5.4 evidence pilot needs rules-only source snapshot')


def make(review, *, now=None, html_fetcher=fetch_html, arxiv_fetcher=fetch_arxiv_metadata, max_items=3):
    now=now or dt.datetime.now(dt.timezone.utc)
    max_items=max(0,min(3,int(max_items)))
    selected=[]
    # PIN 3 exact V0.5.3 articles, not a new daily sample. If a pinned article
    # falls out of the rolling 7-day review, display the gap; never replace it.
    rows=review.get('items',[])
    for publisher,url in PINNED_URLS.items():
        row=next((x for x in rows if x.get('publisher_id')==publisher
                  and x.get('url')==url and allowed_link(x)),None)
        if row:selected.append(row)
        if len(selected)>=max_items:break
    output=[]
    for row in selected:
        record={k:row.get(k) for k in ('id','title','url','source','source_id','publisher_id',
                                         'published_at','category','evidence_level')}
        record.update({'status':'unavailable','kind':allowed_link(row),'retrieved_at':None,
                       'evidence_spans':[],'body_read':False,'independent_confirmation_count':0,
                       'verification_status':'未經人工查核','error_type':None})
        try:
            if record['kind']=='html':
                raw=html_fetcher(row)
                spans=extract_html_spans(raw,row['title'])
                record['body_read']=True
            else:
                pid=paper_id(row['url'])
                if not pid:raise ValueError('Not a valid paper id')
                docs=arxiv_fetcher([pid]);doc=docs.get(pid)
                if (not isinstance(doc,dict) or doc.get('record_id')!=pid
                    or doc.get('record_url')!='https://arxiv.org/abs/'+pid
                    or normalized_title(doc.get('title'))!=normalized_title(row['title'])
                    or not isinstance(doc.get('abstract'),str)):
                    raise ValueError('arXiv metadata identity mismatch')
                spans=split_abstract(doc['abstract'])
                record['body_read']=False  # author's abstract metadata ONLY
            if not spans:raise ValueError('No relevant evidence excerpt extracted')
            record.update({'status':'excerpts_available','retrieved_at':now.isoformat(timespec='seconds'),
                           'evidence_spans':evidence_spans(spans),'error_type':None})
        except Exception as exc:
            record['error_type']=type(exc).__name__  # never pretend denied access was successful
        output.append(record)
    usable=sum(x['status']=='excerpts_available' for x in output)
    return {'meta':{'version':VERSION,'status':'private_primary_source_pilot_not_verification',
                    'generated_at':now.isoformat(timespec='seconds'),
                    'source_review_fingerprint':hashlib.sha256(json.dumps(
                       [(x['id'],x['url']) for x in selected],sort_keys=True).encode()).hexdigest(),
                    'selected_count':len(output),'source_readable_count':usable,
                    'source_unavailable_count':len(output)-usable,
                    'verified_claims':0,'independent_confirmations':0,'importance_accuracy':None,
                    'publication_allowed':False,'copyright_scope':'review_excerpts_only',
                    'warning':'官方原始頁面摘錄供人工審核；arXiv 是作者自述摘要。不能證明主張正確。'},
            'items':output}


def validate(doc,review):
    m=doc.get('meta',{});entries=doc.get('items',[])
    if (m.get('version')!=VERSION or m.get('status')!='private_primary_source_pilot_not_verification'
        or m.get('publication_allowed') is not False or m.get('verified_claims')!=0
        or m.get('independent_confirmations')!=0 or m.get('importance_accuracy') is not None
        or m.get('selected_count')!=len(entries) or len(entries)>3):raise ValueError('Unsafe evidence result')
    allowed_ids={x['id']:x for x in review.get('items',[])};used=set()
    for entry in entries:
        src=allowed_ids.get(entry.get('id'))
        if (not src or entry.get('publisher_id') in used or allowed_link(src)!=entry.get('kind')
            or PINNED_URLS.get(entry.get('publisher_id'))!=entry.get('url')):
            raise ValueError('Invalid evidence provenance/diversity')
        used.add(entry['publisher_id'])
        for k in ('id','title','url','source_id','publisher_id','published_at'):
            if entry.get(k)!=src.get(k):raise ValueError('Changed source provenance '+k)
        if entry.get('independent_confirmation_count')!=0 or entry.get('verification_status')!='未經人工查核':
            raise ValueError('Unauthorized elevation')
        spans=entry.get('evidence_spans',[])
        if entry.get('status')=='excerpts_available':
            if not 1<=len(spans)<=MAX_SPANS:raise ValueError('Bad excerpt count')
            if not entry.get('retrieved_at'):raise ValueError('Missing extraction timestamp')
            for i,x in enumerate(spans,1):
                if (x.get('id')!=f'E{i}' or not isinstance(x.get('text'),str)
                    or not 1<=len(x['text'])<=MAX_SPAN_CHARS
                    or x.get('sha256')!=hashlib.sha256(x['text'].encode('utf-8')).hexdigest()):
                    raise ValueError('Tampered or oversized excerpt')
        elif entry.get('status')!='unavailable' or spans or entry.get('retrieved_at'):
            raise ValueError('Unavailable evidence spoofed as read')
    if m.get('source_readable_count')!=sum(x['status']=='excerpts_available' for x in entries):
        raise ValueError('Evidence count incorrect')
    return True


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--review',required=True)
    ap.add_argument('--output',required=True)
    ap.add_argument('--max-items',type=int,default=3)
    args=ap.parse_args()
    def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
    review=load(args.review)
    validate_base(review,load(ROOT/'data/live_items.json'),load(ROOT/'data/v034_sources.json'),
                  load(ROOT/'data/evidence_enriched.json') if (ROOT/'data/evidence_enriched.json').is_file() else {})
    doc=make(review,max_items=args.max_items)
    validate(doc,review)
    atomic_write(args.output,doc)
    print('V0.5.4 evidence-only pilot: readable={} selected={} unavailable={} VERIFIED=0'.format(
          doc['meta']['source_readable_count'],doc['meta']['selected_count'],doc['meta']['source_unavailable_count']))
    return 0

if __name__=='__main__':raise SystemExit(main())
