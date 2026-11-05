#!/usr/bin/env python3
"""V0.4 quality gates. Uses only synthetic data; does not call paid APIs."""
import json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from intelligence_v040 import prepare, select_diverse, openai_annotate, verified_input, atomic_write

def item(i,source,pub,title=None):
    return {'id':f'id-{i}','source_id':source,'publisher_id':pub,'source':pub,
            'source_kind':'official' if source in ('bea-news','fed-monetary') else 'research',
            'category':'財經' if source in ('bea-news','fed-monetary') else '知識',
            'title':title or f'New observations in energy systems {i}',
            'url':f'https://example.org/record/{i}','published_at':'2026-11-05T00:00:00+00:00','summary':None}

def fixture():
    xs=[item(n,'arxiv-ai','arxiv') for n in range(14)]
    xs +=[item(30,'arxiv-robotics','arxiv','  New observations in energy systems 0  ')]
    xs +=[item(31,'bea-news','bea','GDP release this quarter')]
    xs +=[item(32,'fed-monetary','fed','FOMC interest rate announcement')]
    xs +=[item(33,'bbc-world','bbc','election')]
    return {'meta':{'rights_scope':'descriptive_public_metadata_only','mode':'official_metadata','last_success_at':'2026-11-05T02:00:00+00:00','status':'healthy'},'items':xs}

def fake(item,*,api_key):
    assert api_key=='fake-secret'
    assert item['source_id'] in ('arxiv-ai','arxiv-robotics','bea-news','fed-monetary')
    return {'zh_title':'標題翻譯','category':'知識','monitor_reason':'若有實驗驗證，可能值得追蹤',
            'verification_question':'需要查核實驗方法與外部驗證。','ambiguity_note':'僅從標題無法得知研究方法。'}

def assert_test():
    f=fixture()
    ok=verified_input(f)
    assert len(ok)==17, len(ok)  # 14 AI+1 robotics+BEA+Fed; BBC blocked
    chosen=select_diverse(ok)
    assert len(chosen)==6,len(chosen) # capped at four per publisher + 1 each other
    assert sum(x['publisher_id']=='arxiv' for x in chosen)==4
    a=prepare(f,{},enabled=False,api_key=None)
    assert a['meta']['mode']=='rules_only'
    assert a['meta']['ai_calls_this_run']==0
    assert all(x['review_required'] is True and x['independent_confirmation'] is False for x in a['items'])
    assert all(x['monitor_reason'] is None for x in a['items'])
    b=prepare(f,{},enabled=True,api_key='fake-secret',max_ai=3,annotator=fake)
    assert b['meta']['ai_calls_this_run']==3
    assert sum(x['analysis_mode']=='ai_title_only' for x in b['items'])==3
    assert all(x['verification_status']=='待人工核對' for x in b['items'])
    c=prepare(f,b,enabled=True,api_key='fake-secret',max_ai=3,annotator=fake)
    assert c['meta']['cached_ai_annotations']==3
    assert c['meta']['ai_calls_this_run']==3 # next 3 candidates, incremental spending bounded
    d=prepare(f,c,enabled=False,api_key=None)
    assert sum(x['analysis_mode']=='ai_title_only' for x in d['items'])==6 # cache persists even if disabled
    try:
        verified_input({'meta':{'mode':'demo','rights_scope':'descriptive_public_metadata_only'},'items':[]})
        raise AssertionError('Demo should fail closed')
    except ValueError:pass
    bad=f.copy();bad['items']=[dict(f['items'][0],summary='do not copy full text')]
    assert len(verified_input(bad))==0
    # Test the structured API request in memory; no external calls.
    def mock_transport(payload):
        assert payload['text']['format']['type']=='json_schema'
        assert payload['store'] is False
        assert 'summary' not in json.dumps(payload['input'],ensure_ascii=False)
        return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(fake(f['items'][0],api_key='fake-secret'),ensure_ascii=False)}]}]}
    z=openai_annotate(f['items'][0],api_key='fake-secret',transport=mock_transport)
    assert z['category']=='知識'
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'test.json';atomic_write(p,b)
        assert json.loads(p.read_text())['meta']['candidate_count']==6
    print('V0.4 offline tests: PASS (source gates, diversity, AI cap, cache, structured output, no fabricated analysis)')

if __name__=='__main__': assert_test()
