#!/usr/bin/env python3
"""V0.4.2 offline deterministic evidence provenance and public-export tests."""
from pathlib import Path
import json,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_v042 import build,parse_api_atom,paper_id
from evidence_v041 import build as build_m0,write
from build_public_site import build as site_build

FIXTURE=b'''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
 <id>https://export.arxiv.org/api/query</id>
 <entry><id>http://arxiv.org/abs/2611.12345v2</id>
 <title>Robots for Safer Navigation</title>
 <summary>We propose a navigation method and evaluate it in simulation. Real-world performance remains unknown.</summary></entry>
 <entry><id>https://arxiv.org/abs/2611.99999</id><title>Unrequested paper</title><summary>Injection.</summary></entry>
</feed>'''

def raw():
    a={'id':'x1','source_id':'arxiv-robotics','publisher_id':'arxiv',
       'title':'Robots for Safer Navigation','category':'知識','published_at':'2026-11-05T00:00:00+00:00',
       'url':'https://arxiv.org/abs/2611.12345','summary':None}
    b={'id':'x2','source_id':'bea-news','publisher_id':'bea',
       'title':'Trade data September 2026','category':'財經','published_at':'2026-11-05T00:00:00+00:00',
       'url':'https://www.bea.gov/news/example','summary':None}
    doc={'meta':{'mode':'official_metadata','rights_scope':'descriptive_public_metadata_only'},'items':[a,b]}
    tri={'meta':{'rights_scope':'descriptive_public_metadata_only'},'items':[
         dict(a,verification_status='待人工核對',independent_confirmation=False),
         dict(b,verification_status='待人工核對',independent_confirmation=False)]}
    return build_m0(doc,tri,now='2026-11-05T12:00:00+00:00')

def fake(ids):
    assert ids==['2611.12345']
    return parse_api_atom(FIXTURE,set(ids))

def test():
    m0=raw()
    assert paper_id('https://arxiv.org/abs/2611.12345v2')=='2611.12345'
    assert paper_id('https://arxiv.org.evil.test/abs/2611.12345') is None
    assert paper_id('http://arxiv.org/abs/2611.12345') is None
    out=build(m0,{},fetcher=fake,now='2026-11-05T12:30:00+00:00')
    assert out['meta']['m0a_count']==1 and out['meta']['m0_count']==1
    assert out['meta']['verified_claims']==out['meta']['independently_confirmed_claims']==0
    a,b=out['items']
    assert a['evidence_level']=='M0A' and a['metadata_title_match'] and a['metadata_read']
    assert a['author_abstract'].startswith('We propose') and not a['body_read']
    assert not a['original_document_verified'] and not a['peer_review_confirmed']
    assert b['evidence_level']=='M0' and b['author_abstract'] is None
    assert len(parse_api_atom(FIXTURE,{'2611.12345'}))==1
    assert build(m0,out,fetcher=lambda _: (_ for _ in ()).throw(Exception('Should use cache')))['meta']['m0a_count']==1
    def fail(_):raise TimeoutError('simulated blocked external request')
    degraded=build(m0,{},fetcher=fail)
    assert degraded['meta']['m0a_count']==0 and len(degraded['meta']['api_errors'])==1
    wrong=build(m0,{},fetcher=lambda _: {'2611.12345':dict(fake(['2611.12345'])['2611.12345'],title='Different paper')})
    assert wrong['meta']['m0a_count']==0
    forged=json.loads(json.dumps(out));forged['items'][0]['original_document_verified']=True
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)/'source'; root.mkdir();(root/'data').mkdir()
        # Entire root is copied to temporary directory for integration test. No web calls.
        base=Path(__file__).resolve().parents[1]
        import shutil
        for fn in ('index.html','source-console.html'):
            shutil.copyfile(base/fn,root/fn)
        for fn in ('feed.json','v032_candidates.json','v032_live_probe.json','live_items.json','intelligence.json','evidence_audit.json'):
            shutil.copyfile(base/'data'/fn,root/'data'/fn)
        live={'meta':{'rights_scope':'descriptive_public_metadata_only'},'items':[]}
        triage={'meta':{'rights_scope':'descriptive_public_metadata_only'},'items':[]}
        for source in m0['items']:
            x={k:source[k] for k in ('id','source_id','publisher_id','title','url','category','published_at')}
            live['items'].append(dict(x,summary=None))
            triage['items'].append(dict(x,verification_status='待人工核對',independent_confirmation=False,
                                       review_required=True,analysis_mode='rules_only'))
        write(root/'data/live_items.json',live)
        write(root/'data/intelligence.json',triage)
        write(root/'data/evidence_audit.json',m0)
        write(root/'data/evidence_enriched.json',out)
        site_build(Path(tmp)/'_site',source_root=root)
        assert (Path(tmp)/'_site/data/evidence_enriched.json').exists()
        write(root/'data/evidence_enriched.json',forged)
        try:site_build(Path(tmp)/'_site',source_root=root);raise AssertionError('Forged M2 passed public gate')
        except RuntimeError:pass
    print('PASS V0.4.2: arXiv API title+ID match, author abstract M0A, cache, network failure M0, hostile URL, no false independent verification, export gate')

if __name__=='__main__':test()
