#!/usr/bin/env python3
"""V0.4.3: honest domain blind spots, manual benchmark, and publication guard."""
from pathlib import Path
import json,sys,tempfile,shutil
sys.path.insert(0,str(Path(__file__).resolve().parent))
from source_quality_v043 import build,normalize_url
from build_public_site import build as site_build
from evidence_v041 import write

BASE=Path(__file__).resolve().parents[1]
TIME='2026-11-05T14:40:00+00:00'

def fixture():
    items=[
     {'id':'fed1','source_id':'fed-monetary','publisher_id':'fed','title':'Federal funds rate statement',
      'published_at':TIME,'category':'財經','url':'https://www.federalreserve.gov/newsevents/pressreleases/test.htm','summary':None},
     {'id':'bea1','source_id':'bea-news','publisher_id':'bea','title':'GDP initial estimate',
      'published_at':TIME,'category':'財經','url':'https://www.bea.gov/news/2026/gdp-test','summary':None},
     {'id':'ax1','source_id':'arxiv-ai','publisher_id':'arxiv','title':'Novel benchmark for evaluation',
      'published_at':TIME,'category':'知識','url':'https://arxiv.org/abs/2611.12345','summary':None},
     {'id':'ax2','source_id':'arxiv-robotics','publisher_id':'arxiv','title':'Robotics safety benchmark',
      'published_at':TIME,'category':'知識','url':'https://arxiv.org/abs/2611.88888','summary':None},
    ]
    live={'meta':{'rights_scope':'descriptive_public_metadata_only','mode':'official_metadata','last_success_at':TIME},'items':items,'sources':[]}
    en={'meta':{'rights_scope':'descriptive_public_metadata_only', 'status':'primary_metadata_enrichment_only',
                'verified_claims':0,'independently_confirmed_claims':0,'importance_assessments':0},'items':[
           {'id':'ax1','publisher_id':'arxiv','verification_status':'未查證','independent_confirmation_count':0}]}
    channels=json.loads((BASE/'data/v034_sources.json').read_text(encoding='utf-8'))
    return live,en,channels

def test():
    live,en,ch=fixture()
    r=build(live,en,ch,{'events':[]},now=TIME)
    assert r['meta']['observed_publishers']==3 and r['meta']['observed_channels']==4
    assert r['meta']['benchmarked_event_count']==0 and r['meta']['global_news_recall'] is None
    assert r['meta']['benchmark_event_recall'] is None and r['meta']['verified_claims']==0
    assert r['meta']['domains_no_observed_publisher']==8
    assert r['meta']['domains_single_publisher']==1
    assert r['meta']['importance_scores_created']==0
    assert next(x for x in r['dimensions'] if x['key']=='ai_preprint')['observed_publisher_count']==1
    assert next(x for x in r['dimensions'] if x['key']=='world_politics')['observed_publisher_count']==0
    assert normalize_url('https://www.bea.gov/news/2026/gdp-test?utm_source=example')=='https://www.bea.gov/news/2026/gdp-test'
    assert normalize_url('https://www.bea.gov.evil.test/news/2026/gdp-test') not in {normalize_url(i['url']) for i in live['items']}
    assert normalize_url('http://www.bea.gov/news/test') is None
    refs={'events':[{'id':'i1','original_url':live['items'][1]['url'],
                     'human_reviewed':True,'reviewed_by':'human_auditor','reviewed_at':TIME,'title':'GDP'}]}
    matched=build(live,en,ch,refs,now=TIME)
    assert matched['benchmark_candidates'][0]['url_overlap'] is True
    assert matched['meta']['benchmark_event_recall'] is None
    refs['events'][0]['human_reviewed']=False
    try:build(live,en,ch,refs,now=TIME);raise AssertionError('unreviewed gold benchmark accepted')
    except ValueError:pass
    wrong=json.loads(json.dumps(live));wrong['items'][0]['publisher_id']='arxiv'
    try:build(wrong,en,ch,{'events':[]},now=TIME);raise AssertionError('unapproved source passed')
    except ValueError:pass
    for k in ['verified_claims','independently_confirmed_claims','importance_assessments']:
        bad=json.loads(json.dumps(en));bad['meta'][k]=1
        try:build(live,bad,ch,{'events':[]},now=TIME);raise AssertionError(f'{k} passed')
        except ValueError:pass
    # Existing legacy site tests remain valid: V0.4.3 is optional in nonstrict temp tests.
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'src';root.mkdir();(root/'data').mkdir()
        for fn in ('index.html','source-console.html'):
            shutil.copyfile(BASE/fn,root/fn)
        for fn in ('feed.json','v032_candidates.json','v032_live_probe.json'):
            shutil.copyfile(BASE/'data'/fn,root/'data'/fn)
        live0={'meta':dict(live['meta']),'items':[],'sources':[]}
        write(root/'data/live_items.json',live0)
        write(root/'data/intelligence.json',{'meta':{'rights_scope':'descriptive_public_metadata_only'},'items':[]})
        write(root/'data/evidence_audit.json',{'meta':{'rights_scope':'descriptive_public_metadata_only',
                    'verified_claims':0,'independently_confirmed_claims':0,'importance_assessments':0},'items':[]})
        write(root/'data/evidence_enriched.json',{'meta':{'rights_scope':'descriptive_public_metadata_only',
            'status':'primary_metadata_enrichment_only','verified_claims':0,'independently_confirmed_claims':0,
            'read_bodies':0,'importance_assessments':0},'items':[]})
        empty=build(live0,{'meta':dict(en['meta']),'items':[]},ch,{'events':[]},now=TIME)
        write(root/'data/source_quality_v043.json',empty)
        site_build(Path(td)/'_site',source_root=root)
        assert (Path(td)/'_site/data/source_quality_v043.json').exists()
        forged=json.loads(json.dumps(empty));forged['meta']['global_news_recall']=98
        write(root/'data/source_quality_v043.json',forged)
        try:site_build(Path(td)/'_site',source_root=root);raise AssertionError('fake coverage score published')
        except RuntimeError:pass
        altered=json.loads(json.dumps(empty))
        altered['dimensions'][0]['observed_publisher_count']=2
        altered['dimensions'][0]['observed_publishers']=['fake','fake2']
        write(root/'data/source_quality_v043.json',altered)
        try:site_build(Path(td)/'_site',source_root=root);raise AssertionError('fake independent publishers passed')
        except RuntimeError:pass
    print('PASS V0.4.3: independent publisher dedup, absent political/industry feeds, no global recall, manual benchmark audit, publication fail closed')
if __name__=='__main__':test()
