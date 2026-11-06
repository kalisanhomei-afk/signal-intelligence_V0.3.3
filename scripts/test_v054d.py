#!/usr/bin/env python3
"""Regression tests for the observed numeric token '9' failure.

Uses mocked AI output and local evidence only; incurs no API cost.
"""
import copy
from evidence_analysis_v054 import validate_answer,analyze,validate,normalize_cited_months

ROW={
 'id':'bea-month-case','publisher_id':'bea','kind':'html','status':'excerpts_available',
 'title':'U.S. International Trade in Goods and Services, September 2026',
 'url':'https://www.bea.gov/news/2026/sample',
 'published_at':'2026-11-04T13:30:00+00:00',
 'evidence_spans':[
  {'id':'E1','text':'The deficit with Taiwan increased $3.6 billion to $21.9 billion in September.'},
  {'id':'E2','text':'Exports increased $0.6 billion to $5.3 billion and imports increased $4.2 billion to $27.3 billion.'},
 ]
}
ANSWER={
 'zh_title':'美國國際貿易的官方數據',
 'what_source_says':'資料摘錄提供部分跨境貿易數據。',
 'key_facts':[{'statement':'9月，對台灣逆差增加 $3.6 billion 至 $21.9 billion。','evidence_ids':['E1']}],
 'impact_hypotheses':[{'hypothesis':'若此變化持續，仍需查核其背景與影響。',
                       'assumptions':'需閱讀完整數據表格及修訂。','horizon':'尚無法判斷'}],
 'reading_priority':'值得追蹤',
 'why_priority':'官方資料提供有來源的數字，值得人工核對。',
 'unknowns':'摘錄未包含完整圖表與獨立解釋。',
 'next_check':'對照官方貿易統計完整表格。',
}

def expect_reject(text,row=ROW,code='Uncited numeric assertion'):
    ans=copy.deepcopy(ANSWER);ans['key_facts'][0]['statement']=text
    try:validate_answer(ans,row)
    except ValueError as exc:
        assert code in str(exc), (text,str(exc))
    else:raise AssertionError('Unexpectedly accepted: '+text)

def run():
    assert normalize_cited_months('9月進口','The report says September')=='九月進口'
    assert normalize_cited_months('9月進口','The report says December')=='9月進口'
    assert normalize_cited_months('21.9','September')=='21.9'
    good=copy.deepcopy(ANSWER);validate_answer(good,ROW)
    assert good['key_facts'][0]['statement'].startswith('九月，')
    assert '21.9' in good['key_facts'][0]['statement']
    # An unsupported date, amount, or un-cited month must never slip through.
    expect_reject('2026年9月，對台灣逆差增加 $3.6 billion。')
    expect_reject('9月，對台灣逆差增加 $219 billion。')
    expect_reject('9月，對台灣逆差增加 $9 billion。')
    expect_reject('10月，對台灣逆差增加 $3.6 billion。')
    expect_reject('9月21日，對台灣逆差增加 $3.6 billion。')
    expect_reject('9月，對台灣逆差增加 $3.6 billion。',{
       **ROW,'evidence_spans':[{'id':'E1','text':'The deficit with Taiwan increased $3.6 billion.'}]})
    evidence={'meta':{'selected_count':1,'source_readable_count':1},'items':[ROW]}
    def fake_model(row,*,api_key,model):return copy.deepcopy(ANSWER)
    analysis=analyze(evidence,enable_ai=True,api_key='offline-fake',max_calls=1,annotator=fake_model)
    validate(analysis,evidence)
    assert analysis['meta']['draft_count']==1 and analysis['meta']['api_failures']==0
    assert analysis['items'][0]['analysis']['key_facts'][0]['statement'].startswith('九月')
    print('PASS V0.5.4d: source-grounded September→九月 normalization; exact amounts, years and days remain strict; no API used')

if __name__=='__main__':run()
