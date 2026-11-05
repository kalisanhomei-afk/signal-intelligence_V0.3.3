#!/usr/bin/env python3
"""SIGNAL V0.3.2 — read-only network preflight for candidate RSS/Atom feeds.

Reads at most 2 MiB per endpoint, never stores article body/title, never approves a license.
Does not require a source to be approved merely to check a publisher-listed public RSS URL;
do NOT use this tool against sites forbidding even automated feed requests.
"""
from __future__ import annotations
import argparse,datetime as dt,json,os,sys,time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from refresh import MAX_BYTES,parse_xml
BASE=Path(__file__).resolve().parents[1]
UTC=dt.timezone.utc
MAX_RESPONSE=2_000_000

def inspect_one(s,loader=None):
    started=time.monotonic()
    result={'source_id':s['id'],'publisher_id':s['publisher_id'],'state':'unavailable',
            'url':s['url'],'reference_url':s['reference_url'],'items_seen':0,'error':None,
            'legal_approved':False,'latency_ms':0,'live_tested_at':None}
    try:
        u=urlsplit(s['url'])
        if u.scheme!='https' or not u.hostname or u.username or u.password:
            raise ValueError('feed URL requires https host without credentials')
        if loader is None:
            req=Request(s['url'],headers={'User-Agent':'SIGNAL-PrivateReader/0.3.2 (metadata RSS preflight)',
              'Accept':'application/rss+xml,application/atom+xml,application/xml,text/xml;q=0.8'})
            with urlopen(req,timeout=12) as r:
                if r.status!=200: raise RuntimeError('HTTP '+str(r.status))
                final=urlsplit(r.url)
                # Prevent unintended redirects to a different registered domain.
                if final.hostname!=u.hostname: raise ValueError('unexpected host redirect: '+str(final.hostname))
                body=r.read(MAX_RESPONSE+1)
        else: body=loader(s)
        if len(body)>MAX_RESPONSE: raise ValueError('feed too large')
        # parse_xml handles RSS and Atom; zero-entry valid feeds are allowed by new parser contract.
        records=parse_xml(body,{'id':s['id'],'name':s['name'],'publisher_id':s['publisher_id'],
                                'category':s['category'],'kind':s['kind'],'limit':s.get('fetch_limit',16)},allow_empty=True)
        result.update(state='reachable',items_seen=len(records),live_tested_at=dt.datetime.now(UTC).isoformat(timespec='seconds'))
    except Exception as e:
        result['error']=(type(e).__name__+': '+str(e))[:250]
    result['latency_ms']=round((time.monotonic()-started)*1000)
    return result

def probe(candidates,loader=None):
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda s:inspect_one(s,loader),candidates))
    return {'meta':{'version':'0.3.2','state':'checked',
                    'last_attempt_at':dt.datetime.now(UTC).isoformat(timespec='seconds'),
                    'reachable':sum(r['state']=='reachable' for r in results),
                    'total':len(results), 'rights_cleared':0,
                    'note':'連線成功≠合法自動使用或內容可信；不得自動放行正式採集。'}, 'sources':results}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixtures',default='',help='Offline fixtures: FILE source_id.xml; missing file is failure')
    p.add_argument('--output',default=str(BASE/'data/v032_live_probe.json'))
    p.add_argument('--timeout-sources',type=int,default=0,help='For programmatic dashboards only, not a network bypass')
    args=p.parse_args(argv)
    cfg=json.loads((BASE/'data/v032_candidates.json').read_text(encoding='utf-8'))
    selected=[s for s in cfg['sources'] if s.get('selected_for_probe')]
    if args.fixtures:
        folder=Path(args.fixtures)
        loader=lambda s:(folder/(s['id']+'.xml')).read_bytes()
    else: loader=None
    result=probe(selected,loader)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix(out.suffix+'.tmp')
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(tmp,out)
    print(json.dumps(result['meta'],ensure_ascii=False))
    for s in result['sources']:
        print(f"{s['source_id']:18} {s['state']:12} {str(s['items_seen']):3}  {s['error'] or '-'}")
    return 0 if result['meta']['reachable']==len(selected) else 2
if __name__=='__main__': sys.exit(main())
