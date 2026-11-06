#!/usr/bin/env python3
"""V0.5.4b offline regression: prevent title-date leakage and numeric substring matches.

No network calls, no OpenAI API use.
"""
import json
from evidence_analysis_v054 import NUM, validate_answer, analyze, validate as validate_analysis
from pilot_report_v054 import render

ROW={'id':'test-1','title':'A report about September 2026',
     'publisher_id':'bea','status':'excerpts_available','evidence_spans':[
       {'id':'E1','text':'The deficit rose $3.6 billion to $21.9 billion.','sha256':'a'*64}],
     'url':'https://www.bea.gov','published_at':'2026-11-04T13:30:00+00:00','kind':'html',
     'retrieved_at':'2026-11-06T06:00:00+00:00','error_type':None}

def answer(fact):
    return {'zh_title':'九月貿易報告','what_source_says':'統計顯示貿易赤字增加。',
      'key_facts':[{'statement':fact,'evidence_ids':['E1']}],
      'impact_hypotheses':[{'hypothesis':'若趨勢延續，可能影響未來評估。','assumptions':'需比對後續數據。','horizon':'尚無法判斷'}],
      'reading_priority':'值得追蹤','why_priority':'需要核對官方數據。',
      'unknowns':'未知修訂情況。','next_check':'核對修訂與統計方法。'}

def reject(x):
    try: validate_answer(x,ROW)
    except ValueError: return
    raise AssertionError('must reject unsupported numeric literal')

def run():
    validate_answer(answer('赤字增加 $3.6 billion 至 $21.9 billion。'),ROW)
    # The title contains 2026, but E1 does not: cannot use title as numeric evidence.
    reject(answer('2026 年赤字增加 $3.6 billion。'))
    # A substring is insufficient evidence (9 in 21.9, 21 in 21.9).
    reject(answer('赤字增加 9 billion。'))
    reject(answer('赤字增加 21 billion。'))
    reject(answer('赤字為 219 億美元。'))
    assert set(NUM.findall(ROW['evidence_spans'][0]['text']))=={'3.6','21.9'}
    e={'items':[ROW],'meta':{'selected_count':1,'source_readable_count':1}}
    def failing(row,*,api_key,model):return answer('2026 年赤字增加 $3.6 billion。')
    d=analyze(e,enable_ai=True,api_key='fake-for-offline-tests',max_calls=1,annotator=failing)
    validate_analysis(d,e)
    assert d['meta']['draft_count']==0 and d['meta']['api_failures']==1
    assert d['items'][0]['error_code']=='numeric_not_exactly_in_cited_excerpt'
    assert d['items'][0]['rejected_numeric_token']=='2026'
    assert '2026' in render(e,d) and 'numeric_not_exactly_in_cited_excerpt' in render(e,d)
    def valid(row,*,api_key,model):return answer('赤字增加 $3.6 billion 至 $21.9 billion。')
    d=analyze(e,enable_ai=True,api_key='fake-for-offline-tests',max_calls=1,annotator=valid)
    validate_analysis(d,e)
    assert d['meta']['draft_count']==1 and d['meta']['api_failures']==0
    print('PASS V0.5.4b: exact numeric token citations; title-year leakage refused; rejected tokens audited; zero API calls')

if __name__=='__main__':run()
