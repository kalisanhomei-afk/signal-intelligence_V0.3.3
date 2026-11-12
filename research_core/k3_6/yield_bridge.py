#!/usr/bin/env python3
"""SIGNAL K3.6 yield-revision mechanism probe.

Frozen historical cohorts only; descriptive accounting + year-blocked
research backtest. Never a PIT-certified model, trading signal, or causal
identification. Python standard library only. Run via repository root.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import json
import math
import statistics
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATUS = 'EXPLORATORY_YIELD_BRIDGE_PIT_UNVERIFIED'
ALPHA = 10.0  # fixed beforehand; not tuned on held-out results
COHORT_YEARS = ['2023/24', '2024/25', '2025/26', '2026/27']
EXPECTED_SHA = {
    'exploratory_fixed_cohort.csv': '3b1cf70492a0462973e24254593ccc56058549661305e023719f350af6618660',
    'asof_cohort.csv': '762551a5fc251aa35e64564157c2a874d71daf78b6f82e378e5df9c5d71437ca',
    'wasde_corn_balance.csv': '230714b80f9c08c3f47bae15423311752afce8af2f68ffe1ffb1ac76674a3cb8',
}
OUTPUTS = ('yield_transitions.csv','all_41_yield_transitions.csv','predictions.csv',
           'training_trace.csv','year_metrics.csv','review.json','review.html')


def utc(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if d.tzinfo is None: raise ValueError('Naive datetime: '+s)
    return d.astimezone(timezone.utc)


def read_frozen(path: Path, expected_sha: str, expected_n: int) -> tuple[list[dict],str]:
    raw = path.read_bytes().decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    if expected_sha != digest: raise ValueError(f'FROZEN_HASH_MISMATCH {path.name}: {digest}')
    rows = list(csv.DictReader(raw.splitlines()))
    if len(rows) != expected_n: raise ValueError(f'ROW_COUNT_CHANGED {path.name}: {len(rows)} != {expected_n}')
    return rows, digest


def f(row:dict, name:str) -> float:
    result = float(row[name])
    if not math.isfinite(result): raise ValueError(f'NONFINITE {name}')
    return result


def transition(co: dict, by_release:dict) -> dict:
    origin=utc(co['forecast_origin_utc'])
    base_time=utc(co['base_release_schedule_utc'])
    target_time=utc(co['target_release_schedule_utc'])
    if not (base_time < origin < target_time): raise ValueError('FORECAST_TIME_ORDER_VIOLATION')
    gap_days=(target_time-base_time).total_seconds()/86400
    year=co['marketing_year']
    key0=(base_time.date().isoformat(),year)
    key1=(target_time.date().isoformat(),year)
    if key0 not in by_release or key1 not in by_release: raise ValueError(f'WASDE_JOIN_MISSING {key0} {key1}')
    b,t=by_release[key0],by_release[key1]
    # Make explicit that the 2026/27 next-vintage fields are LABELS,
    # forbidden from being used as predictors at the origin.
    if abs(f(b,'ending_stocks_million_bushels')-f(co,'base_ending_stocks'))>0.001: raise ValueError('BASE_STOCKS_DISAGREE')
    if abs(f(t,'ending_stocks_million_bushels')-f(co,'target_ending_stocks'))>0.001: raise ValueError('TARGET_STOCKS_DISAGREE')
    if abs(f(t,'ending_stocks_million_bushels')-f(b,'ending_stocks_million_bushels')-f(co,'target_delta_million_bushels'))>0.001:
        raise ValueError('STOCK_DELTA_DISAGREE')
    def diff(name): return f(t,name)-f(b,name)
    change_y=diff('yield_bushels_per_acre')
    change_area=diff('harvested_area_million_acres')
    y_contrib=f(b,'harvested_area_million_acres')*change_y
    area_contrib=f(b,'yield_bushels_per_acre')*change_area
    cross=change_area*change_y
    prod=diff('production_million_bushels')
    rounding=prod-y_contrib-area_contrib-cross
    begin=diff('beginning_stocks_million_bushels')
    imports=diff('imports_million_bushels')
    domestic=diff('total_domestic_million_bushels')
    exports=diff('exports_million_bushels')
    stocks=diff('ending_stocks_million_bushels')
    accounting_residual=stocks-(begin+prod+imports-domestic-exports)
    if abs(accounting_residual)>2.001: raise ValueError('STOCK_FLOW_BRIDGE_FAILURE')
    if abs(prod-(y_contrib+area_contrib+cross+rounding))>1e-7: raise ValueError('PRODUCTION_BRIDGE_FAILURE')
    nasstime=co.get('selected_nass_usable_after_utc','')
    if nasstime and utc(nasstime)>origin: raise ValueError('FUTURE_NASS_FEATURE')
    if co['pit_certified'].lower() != 'false': raise ValueError('PIT_STATUS_CHANGED_REASSESS')
    if co['feature_status']=='ELIGIBLE_EXPLORATORY_SCHEDULE_ONLY' and not nasstime:
        raise ValueError('ELIGIBLE_MISSING_NASS')
    return dict(
        marketing_year=year,
        observed_release_gap_days=round(gap_days,3),
        irregular_release_gap_over_45_days=gap_days>45,
        forecast_origin_utc=co['forecast_origin_utc'],
        base_release_utc=co['base_release_schedule_utc'],
        target_release_utc=co['target_release_schedule_utc'],
        feature_status=co['feature_status'],
        nass_date=co.get('selected_nass_date',''),
        nass_good_excellent_pct=co.get('selected_nass_good_excellent_pct',''),
        nass_change_pp=co.get('delta_good_excellent_pp',''),
        base_yield_bu_acre=f(b,'yield_bushels_per_acre'),
        target_yield_bu_acre=f(t,'yield_bushels_per_acre'),
        delta_yield_bu_acre=round(change_y,5),
        base_area_million_acres=f(b,'harvested_area_million_acres'),
        delta_area_million_acres=round(change_area,5),
        delta_production_million_bushels=round(prod,4),
        ex_post_yield_effect_million_bushels=round(y_contrib,4),
        ex_post_area_effect_million_bushels=round(area_contrib,4),
        ex_post_interaction_effect_million_bushels=round(cross,4),
        ex_post_production_rounding_residual=round(rounding,4),
        delta_beginning_stocks_million_bushels=round(begin,4),
        delta_imports_million_bushels=round(imports,4),
        delta_domestic_use_million_bushels=round(domestic,4),
        delta_exports_million_bushels=round(exports,4),
        delta_ending_stocks_million_bushels=round(stocks,4),
        ex_post_stocks_accounting_residual=round(accounting_residual,4),
        pit_certified=False,
        review_status=STATUS)


def build_data(folder:Path) -> tuple[list[dict],list[dict],dict]:
    w,h0=read_frozen(folder/'wasde_corn_balance.csv',EXPECTED_SHA['wasde_corn_balance.csv'],46)
    fixed,h1=read_frozen(folder/'exploratory_fixed_cohort.csv',EXPECTED_SHA['exploratory_fixed_cohort.csv'],21)
    allrows,h2=read_frozen(folder/'asof_cohort.csv',EXPECTED_SHA['asof_cohort.csv'],41)
    by_release={}
    for v in w:
        key=(v['release_date'],v['marketing_year'])
        if key in by_release: raise ValueError('DUPLICATE_VINTAGE')
        if v['quality_status'] != 'PASS_ROUNDING_TOLERANCE': raise ValueError('WASDE_BALANCE_QUALITY_FAIL')
        e=(f(v,'beginning_stocks_million_bushels')+f(v,'production_million_bushels')+
           f(v,'imports_million_bushels')-f(v,'total_domestic_million_bushels')-
           f(v,'exports_million_bushels'))
        if abs(f(v,'ending_stocks_million_bushels')-e)>1.001: raise ValueError('WASDE_BALANCE_DRIFT')
        by_release[key]=v
    alltrans=[transition(r,by_release) for r in allrows]
    by_identity={(r['marketing_year'],r['forecast_origin_utc']):r for r in alltrans}
    if len(by_identity)!=41: raise ValueError('DUPLICATE_ORIGIN')
    eligible=[]
    for row in fixed:
        key=(row['marketing_year'],row['forecast_origin_utc'])
        if key not in by_identity: raise ValueError('FIXED_NOT_IN_ASOF')
        trans=transition(row,by_release)
        if trans['feature_status']!='ELIGIBLE_EXPLORATORY_SCHEDULE_ONLY': raise ValueError('FIXED_FEATURE_CHANGED')
        if trans!=by_identity[key]: raise ValueError('FROZEN_SUBSET_DIFFERENCE')
        eligible.append(trans)
    if len(eligible)!=21 or set(r['marketing_year'] for r in eligible)!=set(COHORT_YEARS): raise ValueError('COHORT_DRIFT')
    eligible.sort(key=lambda d:d['forecast_origin_utc'])
    alltrans.sort(key=lambda d:d['forecast_origin_utc'])
    return eligible,alltrans,{'wasde_46':h0,'k341_fixed_21':h1,'k341_asof_41':h2}


def x(r:dict) -> tuple[float,float]:
    return float(r['nass_good_excellent_pct']), float(r['nass_change_pp'])


def train_ridge(train:list[dict],alpha:float=ALPHA) -> dict:
    if len(train)<6: raise ValueError('TRAIN_TOO_SMALL')
    if alpha<=0: raise ValueError('ALPHA_MUST_BE_POSITIVE')
    vals=[x(r) for r in train]
    y=[float(r['delta_yield_bu_acre']) for r in train]
    mu=[statistics.mean(v[j] for v in vals) for j in range(2)]
    std=[math.sqrt(statistics.mean((v[j]-mu[j])**2 for v in vals)) for j in range(2)]
    std=[z if z>1e-10 else 1.0 for z in std]
    xx=[((v[0]-mu[0])/std[0], (v[1]-mu[1])/std[1]) for v in vals]
    y0=statistics.mean(y)
    a=sum(v[0]**2 for v in xx)+alpha
    b=sum(v[0]*v[1] for v in xx)
    c=sum(v[1]**2 for v in xx)+alpha
    d=sum(v[0]*(yy-y0) for v,yy in zip(xx,y))
    e=sum(v[1]*(yy-y0) for v,yy in zip(xx,y))
    det=a*c-b*b
    if det<1e-10: raise ValueError('RIDGE_SINGULAR')
    beta=[(d*c-e*b)/det,(a*e-b*d)/det]
    return {'intercept':y0,'means':mu,'stds':std,'beta':beta,'alpha':alpha,'train_n':len(train)}


def predict_ridge(model:dict,r:dict) -> float:
    v=x(r)
    return model['intercept']+sum(model['beta'][j]*(v[j]-model['means'][j])/model['stds'][j] for j in range(2))


def score(rows:list[dict],key:str) -> dict:
    pred=[r['predict_delta_'+key] for r in rows]
    actual=[r['actual_delta_yield'] for r in rows]
    errors=[p-a for p,a in zip(pred,actual)]
    wins=sum(abs(e) < abs(a) for e,a in zip(errors,actual)) if key!='A' else None
    # A predicts zero and makes no directional call. Direction scores include
    # zero changes so readers must ALSO see class frequencies.
    def sign(v):return 0 if abs(v)<1e-9 else (1 if v>0 else -1)
    direction=None if key=='A' else sum(sign(p)==sign(a) for p,a in zip(pred,actual))/len(rows)
    return {'n':len(rows),'mae':round(statistics.mean(abs(e) for e in errors),6),
            'rmse':round(math.sqrt(statistics.mean(e*e for e in errors)),6),
            'bias':round(statistics.mean(errors),6),
            'direction_match':None if direction is None else round(direction,6),
            'beats_persistence_rows':wins}


def walk_forward(eligible:list[dict]) -> tuple[list[dict],list[dict],list[dict],dict]:
    pred=[];trace=[]; yearmetrics=[]
    for idx in range(1,len(COHORT_YEARS)):
        yr=COHORT_YEARS[idx]
        prior=set(COHORT_YEARS[:idx]); train=[r for r in eligible if r['marketing_year'] in prior]
        test=[r for r in eligible if r['marketing_year']==yr]
        if not train or not test: raise ValueError('EMPTY_FOLD')
        if len(train)<6: raise ValueError('INSUFFICIENT_TRAIN')
        latest_label=max(utc(r['target_release_utc']) for r in train)+timedelta(hours=24)
        earliest_origin=min(utc(r['forecast_origin_utc']) for r in test)
        if latest_label>earliest_origin: raise ValueError('FUTURE_LABEL_LEAKAGE')
        histmean=statistics.mean(float(r['delta_yield_bu_acre']) for r in train)
        model=train_ridge(train)
        trace.append({'test_year':yr,'train_years':';'.join(COHORT_YEARS[:idx]),
                      'train_n':len(train),'test_n':len(test),
                      'latest_train_label_plus_24h':latest_label.isoformat(),
                      'first_test_origin':earliest_origin.isoformat(),
                      'mean_train_yield_delta':round(histmean,6),
                      'ridge_intercept':round(model['intercept'],6),
                      'ridge_beta_ge':round(model['beta'][0],6),
                      'ridge_beta_ge_change':round(model['beta'][1],6),
                      'ridge_alpha':ALPHA})
        sub=[]
        for r in test:
            row={'test_year':yr,'forecast_origin_utc':r['forecast_origin_utc'],
                 'target_release_utc':r['target_release_utc'],
                 'nass_good_excellent_pct':r['nass_good_excellent_pct'],
                 'nass_change_pp':r['nass_change_pp'],
                 'base_yield':r['base_yield_bu_acre'],
                 'actual_target_yield':r['target_yield_bu_acre'],
                 'actual_delta_yield':r['delta_yield_bu_acre'],
                 'predict_delta_A':0.0,
                 'predict_delta_B':round(histmean,8),
                 'predict_delta_C':round(predict_ridge(model,r),8),
                 'train_n':len(train),'pit_certified':False,
                 'model_status':STATUS}
            pred.append(row);sub.append(row)
        for m in 'ABC': yearmetrics.append({'test_year':yr,'model':m,**score(sub,m)})
    if len(pred)!=15: raise ValueError(f'HELDOUT_COUNT_CHANGED {len(pred)}')
    return pred,trace,yearmetrics,{m:score(pred,m) for m in 'ABC'}


def csv_out(path:Path,rows:list[dict]):
    if not rows: raise ValueError('EMPTY_OUTPUT '+str(path))
    with path.open('w',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def make_html(review:dict):
    metrics=review['metrics']['heldout']
    stat=''.join(f'<tr><td>{m}</td><td>{metrics[m]["mae"]:.3f}</td><td>{metrics[m]["rmse"]:.3f}</td><td>{metrics[m]["direction_match"] if metrics[m]["direction_match"] is not None else "不適用"}</td></tr>' for m in 'ABC')
    notes=''.join('<li>'+html.escape(t)+'</li>' for t in review['limitations'])
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>SIGNAL K3.6 單產傳導研究</title><style>body{{font:16px/1.65 system-ui,-apple-system,'Microsoft JhengHei',sans-serif;max-width:1040px;margin:40px auto;padding:0 24px;color:#172333;background:#f5f7fa}}h1,h2{{color:#193b58}}main{{background:white;padding:32px 40px;border-radius:15px;box-shadow:0 5px 30px #1232}}table{{border-collapse:collapse;width:100%;margin:16px 0 25px}}th,td{{border-bottom:1px solid #dce4ec;padding:10px;text-align:left}}th{{background:#edf4f8}}.tag{{display:inline-block;background:#fff0d6;padding:5px 12px;border-radius:14px;color:#7c4400}}.big{{font-weight:bold;font-size:18px}}.muted{{color:#526373}}</style></head><body><main><div class="tag">研究用途｜PIT 未經獨立認證｜不得作為交易訊號</div><h1>SIGNAL K3.6｜玉米單產修正與供需傳導</h1><p class="big">資料檢查：46 期 WASDE → 41 次同年度修正 → 21 筆具有 NASS 的探索樣本 → 15 筆年度封鎖測試。</p><h2>模型比較（單位：bushels/acre）</h2><table><tr><th>模型</th><th>MAE</th><th>RMSE</th><th>方向吻合</th></tr>{stat}</table><p>模型 A：單產不修正；B：先前年份平均修正；C：Good+Excellent 與週變化的固定 Ridge（α=10）。三者在完全相同的 15 筆測試資料比較。</p><h2>機制核算</h2><p>期末庫存變化＝期初庫存變化＋產量變化＋進口變化－國內使用變化－出口變化＋帳面四捨五入殘差。</p><p>產量變化≈前期收穫面積×單產變化＋前期單產×面積變化＋交互項＋公告數值四捨五入差。</p><p class="muted">這是事後會計歸因，不是已證實的因果估計。目標月份的供需修正只用於解釋與評分，絕不進入當期預測特徵。</p><h2>資料品質與判定</h2><table><tr><th>項目</th><th>結果</th></tr><tr><td>探索樣本的單產有修正</td><td>{review['nonzero_yield_in_21']} / 21</td></tr><tr><td>全部41次中單產有修正</td><td>{review['nonzero_yield_in_41']} / 41</td></tr><tr><td>已獨立核實的 PIT</td><td>0</td></tr><tr><td>狀態</td><td>{html.escape(STATUS)}</td></tr></table><h2>限制與下一步</h2><ul>{notes}</ul><p class="muted">審閱檔案：review.json、yield_transitions.csv、all_41_yield_transitions.csv、predictions.csv、training_trace.csv、year_metrics.csv</p></main></body></html>'''


def run(inputs:Path,out:Path) -> dict:
    eligible,alltrans,hashes=build_data(inputs)
    pred,trace,yearmetrics,metrics=walk_forward(eligible)
    nonzero21=sum(abs(float(r['delta_yield_bu_acre']))>1e-8 for r in eligible)
    nonzero41=sum(abs(float(r['delta_yield_bu_acre']))>1e-8 for r in alltrans)
    irregular=[r for r in alltrans if r['irregular_release_gap_over_45_days']]
    r26=[r for r in eligible if r['base_release_utc'].startswith('2026-10-09') and r['target_release_utc'].startswith('2026-11-10')]
    if len(r26)!=1: raise ValueError('OCT_NOV_2026_BRIDGE_NOT_FOUND')
    r26=r26[0]
    if abs(float(r26['delta_yield_bu_acre'])+1.6)>1e-7 or abs(float(r26['delta_ending_stocks_million_bushels'])+91)>1e-8:
        raise ValueError('OCT_NOV_2026_REFERENCE_DRIFT')
    review={
      'module':'K3.6 yield-revision causal-chain preflight / exploratory backtest',
      'status':STATUS,'research_only':True,'pit_certified':False,
      'input_origin': 'User-provided GitHub Actions artifacts K3.4 and K3.4.1, frozen copies',
      'input_sha256_normalized_lf':hashes,
      'counts':{'wasde_vintages':46,'all_transitions':41,'exploratory_cohort':21,'heldout_predictions':15},
      'nonzero_yield_in_21':nonzero21,'nonzero_yield_in_41':nonzero41,
      'irregular_release_intervals_over_45_days':[{
          'marketing_year':r['marketing_year'], 'base_release_utc':r['base_release_utc'],
          'target_release_utc':r['target_release_utc'],'gap_days':r['observed_release_gap_days']} for r in irregular],
      'heldout_actual_direction':dict(Counter('up' if p['actual_delta_yield']>0 else ('down' if p['actual_delta_yield']<0 else 'unchanged') for p in pred)),
      'model_definitions':{'A':'persistence delta yield=0','B':'mean of yield revisions in earlier marketing years only','C':'ridge on NASS Good+Excellent and one-week change, alpha=10 fixed, train-only standardization'},
      'training_rule':'expanding whole marketing years, no current-year labels; training targets released >=24h before first test origin',
      'metrics':{'heldout':metrics,'by_year':yearmetrics},
      'ex_post_bridge_2026_10_to_11':{k:v for k,v in r26.items() if k.startswith('delta_') or k.startswith('ex_post_')},
      'limitations':[
        'PIT timestamps are official scheduled times plus safety buffers, not independently observed per-report publication timestamps.',
        'This reuses years already examined in K3.5; the apparent holdout is chronological but not a new untouched confirmation set.',
        'Only four marketing years, with merely three held-out years. The same-year NASS observations are correlated and are not independent trials.',
        'The Sep-to-Nov 2025 transition spans 63 days because an October release is missing; it remains one next-published-vintage event, not a standard one-month observation.',
        'Good+Excellent describes reported crop condition; it is not a direct measurement of national yield or a surprise relative to consensus.',
        'End-of-period supply-and-use terms are only used for ex-post decomposition; incorporating them as contemporaneous features would leak targets.',
        'Acreage × yield and USDA printed production differ due to independently rounded published numbers. Do not force rounding residual to zero.',
        'Current vintage CSV captures original report-month vintages but cannot establish whether historical corrected data were ever revised; archival integrity audit remains open.',
        'No prices, consensus expectations, transaction costs, or risk-adjusted trading tests are included.'
      ]}
    out.mkdir(parents=True,exist_ok=True)
    csv_out(out/'yield_transitions.csv',eligible)
    csv_out(out/'all_41_yield_transitions.csv',alltrans)
    csv_out(out/'predictions.csv',pred)
    csv_out(out/'training_trace.csv',trace)
    csv_out(out/'year_metrics.csv',yearmetrics)
    (out/'review.json').write_text(json.dumps(review,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (out/'review.html').write_text(make_html(review),encoding='utf-8')
    return review


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parent/'inputs')
    p.add_argument('--out',type=Path,default=Path('k36-review'))
    args=p.parse_args()
    report=run(args.inputs,args.out)
    print(json.dumps({'status':report['status'], 'counts':report['counts'],'metrics':report['metrics']['heldout']},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
