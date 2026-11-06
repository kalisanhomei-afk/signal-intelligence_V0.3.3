#!/usr/bin/env python3
"""Self-contained offline V0.5.4 acceptance tests; all HTTP and OpenAI calls mocked."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
from pathlib import Path
from evidence_pilot_v054 import allowed_link,extract_html_spans,evidence_spans,make,validate
from evidence_analysis_v054 import validate_answer,analyze,validate as validate_analysis
from pilot_report_v054 import render


def sample(sid,pub,title,url):
    return {'id':'test-'+sid,'source_id':sid,'publisher_id':pub,'title':title,'url':url,
            'source':pub,'published_at':'2026-11-06T00:00:00+00:00','category':'財經',
            'evidence_level':'M0'}

BEA=sample('bea-news','bea','U.S. International Trade in Goods and Services, September 2026',
           'https://www.bea.gov/news/2026/us-international-trade-goods-and-services-september-2026')
EIA=sample('eia-energy','eia','Refineries have shifted production away from gasoline to middle distillates',
           'https://www.eia.gov/todayinenergy/detail.php?id=68424')
ARX=sample('arxiv-robotics','arxiv','MESA: An Evaluation Framework for Robotics',
           'https://arxiv.org/abs/2611.05567')
HTML_BE=('<html><head><title>'+BEA['title']+'</title></head><body><nav>Menu navigation</nav>'
         '<main><h1>'+BEA['title']+'</h1><p>The United States recorded a trade deficit of '
         '$105.0 billion in September 2026, while goods exports increased.</p>'
         '<p>Services imports were $100.0 billion during September 2026 and these figures may be revised.</p>'
         '</main></body></html>')
HTML_EIA=('<html><body><article><h1>'+EIA['title']+'</h1><p>Refineries shifted their '
          'production toward middle distillates, with gasoline yield under 45% in 2026.</p>'
          '<p>Jet fuel yields stayed at or above 12% in recent months according to the EIA.</p>'
          '</article></body></html>')


def stub_html(row):return HTML_BE if row['source_id']=='bea-news' else HTML_EIA

def stub_arxiv(ids):return {ids[0]:{
    'record_id':ids[0],'record_url':'https://arxiv.org/abs/'+ids[0],
    'title':ARX['title'],
    'abstract':'The proposed MESA framework evaluates robotic learning on 7 benchmark methods and 5 test suites.'}}


def throws(fn):
    try:fn()
    except ValueError:return True
    raise AssertionError('Expected unsafe/invalid result to raise ValueError')


def run():
    assert allowed_link(BEA)=='html' and allowed_link(EIA)=='html' and allowed_link(ARX)=='arxiv_api'
    assert allowed_link({**BEA,'url':'https://attacker.test/news/2026/fake'}) is None
    assert allowed_link({**EIA,'url':'http://www.eia.gov/todayinenergy/detail.php?id=68424'}) is None
    assert allowed_link({**EIA,'url':'https://www.eia.gov/todayinenergy/detail.php?id=2&url=attacker'}) is None
    assert allowed_link({**BEA,'url':'https://www.bea.gov@evil.test/news/2026/foo'}) is None
    assert len(extract_html_spans(HTML_BE,BEA['title']))>=2
    assert all('navigation' not in s for s in extract_html_spans(HTML_BE,BEA['title']))
    assert throws(lambda:extract_html_spans('<html><main><p>access denied</p></main></html>',BEA['title']))
    base={'items':[BEA,EIA,ARX],'meta':{'status':'provisional_editorial_review_only'}}
    fixed_now=dt.datetime(2026,11,6,tzinfo=dt.timezone.utc)
    doc=make(base,now=fixed_now,html_fetcher=stub_html,arxiv_fetcher=stub_arxiv)
    validate(doc,base)
    assert doc['meta']['selected_count']==3 and doc['meta']['source_readable_count']==3
    assert doc['meta']['verified_claims']==0 and doc['meta']['publication_allowed'] is False
    assert doc['items'][2]['body_read'] is False  # arxiv author abstract is not paper body
    assert doc['items'][0]['body_read'] is True
    tampered=json.loads(json.dumps(doc));tampered['items'][0]['evidence_spans'][0]['text']='modified'
    assert throws(lambda:validate(tampered,base))
    failed=make(base,now=fixed_now,html_fetcher=lambda _: (_ for _ in ()).throw(TimeoutError()),
                arxiv_fetcher=lambda _: {})
    validate(failed,base)
    assert failed['meta']['source_readable_count']==0
    assert all(x['status']=='unavailable' and x['error_type'] for x in failed['items'])
    answer={'zh_title':'美國貿易報告','what_source_says':'原文指出在九月的商品貿易資料。',
       'key_facts':[{'statement':'2026年September的貿易逆差為105.0 billion美元',
          'evidence_ids':['E1']}],
       'impact_hypotheses':[{'hypothesis':'若這一變化持續，可能改變貿易預期。',
           'assumptions':'需先檢查是否為已修訂數據。','horizon':'一季內'}],
       'reading_priority':'值得追蹤','why_priority':'有具體數據可再查證。',
       'unknowns':'無第三方驗證','next_check':'確認最新修訂值。'}
    assert validate_answer(answer,doc['items'][0])
    bad=json.loads(json.dumps(answer));bad['key_facts'][0]['statement']='貿易逆差為9999 billion美元'
    assert throws(lambda:validate_answer(bad,doc['items'][0]))
    bad=json.loads(json.dumps(answer));bad['key_facts'][0]['evidence_ids']=['E999']
    assert throws(lambda:validate_answer(bad,doc['items'][0]))
    assert throws(lambda:analyze(doc,enable_ai=True,api_key='',max_calls=3))
    out=analyze(doc,enable_ai=False,api_key='',max_calls=0)
    validate_analysis(out,doc)
    assert out['meta']['api_calls_attempted']==0 and out['meta']['draft_count']==0
    def mocked(row,*,api_key,model):return answer if row['source_id']=='bea-news' else {
        **answer,'key_facts':[],'what_source_says':'只見部分官方摘錄，仍需查核。'}
    out=analyze(doc,enable_ai=True,api_key='test-never-a-real-secret',max_calls=3,annotator=mocked)
    validate_analysis(out,doc)
    assert out['meta']['api_calls_attempted']==3 and out['meta']['draft_count']==3
    assert out['meta']['verified_claims']==0
    page=render(doc,out)
    assert 'SIGNAL' in page and 'V0.5.4' in page and '原始出處' in page
    assert '&lt;script' not in page and '模型草稿' in page
    print('PASS V0.5.4: 21 source, rights, failure, provenance, AI, and report acceptance assertions')

if __name__=='__main__':run()
