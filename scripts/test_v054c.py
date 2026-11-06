#!/usr/bin/env python3
"""V0.5.4c offline safety test: source metadata cannot pollute numeric evidence.
No external API/network calls.
"""
import json
from evidence_analysis_v054 import call_model,validate_answer,analyze,validate

ROW={
 'id':'test-bea','title':'U.S. International Trade in Goods and Services, September 2026',
 'publisher_id':'bea','url':'https://www.bea.gov/news/2026/sample-2026',
 'published_at':'2026-11-04T13:30:00+00:00','kind':'html',
 'status':'excerpts_available',
 'evidence_spans':[{'id':'E1','text':'The deficit with Taiwan increased $3.6 billion to $21.9 billion in September.'}],
}

ANSWER={
 'zh_title':'美國貿易收支資料',
 'what_source_says':'來源摘錄指出對台灣的貿易逆差擴大。',
 'key_facts':[{'statement':'對台灣的貿易逆差增加 $3.6 billion 至 $21.9 billion。',
               'evidence_ids':['E1']}],
 'impact_hypotheses':[{'hypothesis':'若此變化持續，可能需要重新評估貿易結構。',
                       'assumptions':'須核對後續月份及數據修訂。','horizon':'尚無法判斷'}],
 'reading_priority':'值得追蹤',
 'why_priority':'該摘錄提供可查證的數值與變化。',
 'unknowns':'尚缺不同來源證實及後續月份資料。',
 'next_check':'核對官方報告表格中的數字與修訂。',
}

def main():
    def transport(payload):
        user = json.loads(payload['input'][1]['content'])
        assert set(user)=={'UNTRUSTED_SOURCE_MATERIAL','publisher','kind','input_scope','snippets'}
        assert user['publisher']=='bea' and user['kind']=='html'
        assert user['input_scope']=='cited_excerpts_only'
        assert user['snippets']==[{'id':'E1','text':ROW['evidence_spans'][0]['text']}]
        assert '2026' not in json.dumps(user)
        assert 'source_url' not in user and 'title' not in user and 'published_at' not in user
        return {'status':'completed','output':[{'type':'message','content':[
          {'type':'output_text','text':json.dumps(ANSWER,ensure_ascii=False)}]}]}
    good=call_model(ROW,api_key='offline-fake-key',transport=transport)
    assert good==ANSWER
    validate_answer(good,ROW)
    bad=json.loads(json.dumps(ANSWER))
    bad['key_facts'][0]['statement']='2026 年對台灣的貿易逆差增加 $3.6 billion。'
    try: validate_answer(bad,ROW)
    except ValueError as e: assert 'Uncited numeric assertion: 2026' in str(e)
    else: raise AssertionError('Metadata year must not be accepted as evidence')
    evidence={'meta':{'selected_count':1,'source_readable_count':1},'items':[ROW]}
    def adapter(row,*,api_key,model):return call_model(row,api_key=api_key,model=model,transport=transport)
    result=analyze(evidence,enable_ai=True,api_key='offline-fake-key',max_calls=1,annotator=adapter)
    validate(result,evidence)
    assert result['meta']['draft_count']==1 and result['meta']['api_failures']==0
    assert result['meta']['model_input_scope']=='cited_excerpts_only_no_title_url_or_published_date'
    print('PASS V0.5.4c: metadata withheld from model, source traceability retained, exact numeric guard unchanged; no API cost')

if __name__=='__main__':main()
