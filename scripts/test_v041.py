#!/usr/bin/env python3
"""V0.4.1 schema, traceability, fail-closed checks; no network or paid API."""
import sys,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_v041 import build,write

def raw():
    a={'id':'x1','source_id':'arxiv-ai','publisher_id':'arxiv','title':'An illustrative engineering preprint',
       'category':'知識','published_at':'2026-11-05T00:00:00+00:00',
       'url':'https://arxiv.org/abs/2611.12345','summary':None}
    b={'id':'x2','source_id':'bea-news','publisher_id':'bea','title':'GDP released this quarter',
       'category':'財經','published_at':'2026-11-05T00:00:00+00:00',
       'url':'https://www.bea.gov/news/example','summary':None}
    return ({'meta':{'mode':'official_metadata','rights_scope':'descriptive_public_metadata_only'},'items':[a,b]},
       {'meta':{'rights_scope':'descriptive_public_metadata_only'},
        'items':[dict(a,verification_status='待人工核對',independent_confirmation=False),
                 dict(b,verification_status='待人工核對',independent_confirmation=False)]})

def test():
    doc,triage=raw()
    out=build(doc,triage,now='2026-11-05T12:00:00+00:00')
    assert len(out['items'])==2 and out['meta']['publisher_count']==2
    assert all(x['evidence_level']=='M0' and x['verification_status']=='未查證' and x['independent_confirmation_count']==0 for x in out['items'])
    assert any('同儕審查' in q for q in out['items'][0]['questions'])
    assert out['meta']['verified_claims']==0 and out['meta']['importance_assessments']==0
    # Duplicated same ID is NOT an independent source.
    triage['items'].append(dict(triage['items'][0]))
    assert len(build(doc,triage)['items'])==2
    triage['items'].pop()
    # Injected hostname cannot pass (including tricks like arxiv.org.evil.example).
    triage['items'][0]['url']='https://arxiv.org.evil.example/abs/foo'
    assert len(build(doc,triage)['items'])==1
    triage['items'][0]['url']=doc['items'][0]['url']
    triage['items'][0]['verification_status']='已查證'
    try:build(doc,triage);raise AssertionError('Unjustified evidence promotion allowed')
    except ValueError:pass
    triage['items'][0]['verification_status']='待人工核對'
    doc['meta']['rights_scope']='unknown'
    try:build(doc,triage);raise AssertionError('Wrong rights scope accepted')
    except ValueError:pass
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'audit.json';write(p,out)
        assert json.loads(p.read_text())['meta']['candidate_count']==2
    print('PASS V0.4.1: source binding, strict hosts, zero false verification, duplicate independence, scope & serialization')
if __name__=='__main__':test()
