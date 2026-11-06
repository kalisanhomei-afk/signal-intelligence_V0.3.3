#!/usr/bin/env python3
"""Offline regression for V0.5.4a diagnostics and preservation of safety gates."""
from evidence_analysis_v054 import analyze, failure_code, validate
from evidence_pilot_v054 import extract_html_spans

def sample():
    return {'meta':{'source_readable_count':1},'items':[{
        'id':'sample-1','source_id':'bea-news','publisher_id':'bea',
        'title':'Sample','status':'excerpts_available',
        'evidence_spans':[{'id':'E1','text':'2026 results were 45%.', 'sha256':'-'}]}]}

def run():
    src=sample()
    def rejected(row,*,api_key,model):raise ValueError('Uncited numeric assertion: 99')
    o=analyze(src,enable_ai=True,api_key='dummy-not-real',max_calls=1,annotator=rejected)
    validate(o,src)
    assert o['meta']['api_calls_attempted']==1 and o['meta']['api_failures']==1
    assert o['meta']['draft_count']==0
    assert o['items'][0]['error_code']=='numeric_not_exactly_in_cited_excerpt'
    assert failure_code(ValueError('Incomplete model response: max_output_tokens'))=='model_output_token_limit'
    assert failure_code(ValueError('Impact hypothesis not conditional'))=='impact_condition_missing'
    assert failure_code(ValueError('other unexpected message'))=='other_value_error'
    # No spurious site-wide EIA tag/navigation blocks in source excerpts.
    html='<html><body><article><h1>Refineries shifted</h1><p>Browse by tag liquid fuels natural gas electricity oil/petroleum production/supply crude oil consumption/demand generation prices map states exports/imports international coal renewables weather forecasts/projections gasoline capacity steo (short-term energy outlook)</p><p>Gasoline share in output declined to 45% during 2026, according to the refinery report and actual published data.</p><p>Middle distillate and jet fuel margins were above prior levels and production changed accordingly, according to the refinery data.</p><p>Jet fuel shares exceeded 12% in the recent period through August, the report states.</p></article></body></html>'
    xs=extract_html_spans(html,'Refineries shifted')
    assert xs and all('Browse by tag' not in x for x in xs)
    print('PASS V0.5.4a: safe failure diagnostics, paid-call cap, numeric safeguards, article-only extraction')

if __name__=='__main__':run()
