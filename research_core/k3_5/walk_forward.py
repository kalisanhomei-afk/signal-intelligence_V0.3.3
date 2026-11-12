#!/usr/bin/env python3
"""SIGNAL K3.5 / frozen K3.4.1 cohort: marketing-year blocked expanding evaluation.

Research only. No causal/trading inference. Python 3.11+ standard library only.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

RESEARCH_STATUS = 'EXPLORATORY_MODEL_COMPARISON_PIT_UNVERIFIED'
FROZEN_SHA256_CANONICAL = '3b1cf70492a0462973e24254593ccc56058549661305e023719f350af6618660'
ALPHA = 10.0  # Pre-committed, not tuned on validation years.
MIN_TRAIN = 6
TRAINING_MARKETING_YEAR = '2023/24'
PIT_STATUS_REQUIRED = 'ELIGIBLE_EXPLORATORY_SCHEDULE_ONLY'
FEATURE_NAMES = ['selected_nass_good_excellent_pct', 'delta_good_excellent_pp']


def normalized_bytes(raw: bytes) -> bytes:
    return raw.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')


def parse_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if dt.tzinfo is None: raise ValueError('Naive datetime is prohibited: ' + s)
    return dt.astimezone(timezone.utc)


def year_start(my: str) -> int:
    a,b = my.split('/')
    if len(a) != 4 or len(b) != 2 or (int(a)+1)%100 != int(b):
        raise ValueError('Invalid marketing year: ' + my)
    return int(a)


@dataclass(frozen=True)
class Obs:
    marketing_year: str
    origin: str
    target_release: str
    prev_release: str
    base: float
    actual: float
    delta: float
    ge: float
    ge_change: float
    nass_date: str
    nass_usable: str
    pit_certified: bool


def load_cohort(path: Path, frozen_sha: str = FROZEN_SHA256_CANONICAL) -> tuple[list[Obs],str]:
    raw = path.read_bytes()
    canon = normalized_bytes(raw)
    checksum = hashlib.sha256(canon).hexdigest()
    if frozen_sha and checksum != frozen_sha:
        raise ValueError(f'FROZEN_INPUT_HASH_MISMATCH expected={frozen_sha} actual={checksum}')
    text = canon.decode('utf-8')
    records = list(csv.DictReader(text.splitlines()))
    if len(records) != 21: raise ValueError(f'FROZEN_COHORT_SIZE_CHANGED: {len(records)} (expected 21)')
    result=[]
    origins=set()
    for r in records:
        required=['marketing_year','forecast_origin_utc','target_release_schedule_utc',
                  'base_release_schedule_utc','base_ending_stocks','target_ending_stocks',
                  'target_delta_million_bushels','selected_nass_date','selected_nass_usable_after_utc',
                  'selected_nass_good_excellent_pct','delta_good_excellent_pp',
                  'feature_status','pit_certified']
        if any(x not in r or r[x]=='' for x in required):
            raise ValueError('Required field missing at '+repr(r.get('forecast_origin_utc')))
        if r['feature_status'] != PIT_STATUS_REQUIRED: raise ValueError('Ineligible feature selected')
        if r['pit_certified'].strip().lower() != 'false':
            raise ValueError('Source claims PIT certification unexpectedly; must reassess protocol')
        origin = parse_utc(r['forecast_origin_utc'])
        target = parse_utc(r['target_release_schedule_utc'])
        prev = parse_utc(r['base_release_schedule_utc'])
        nass = parse_utc(r['selected_nass_usable_after_utc'])
        if not (prev < origin < target and nass <= origin):
            raise ValueError('RELEASE_ORDER_OR_ASOF_VIOLATION: '+str(origin))
        if r['forecast_origin_utc'] in origins: raise ValueError('Duplicate forecast origin')
        origins.add(r['forecast_origin_utc'])
        base, actual, delta = map(float, (r['base_ending_stocks'],r['target_ending_stocks'],r['target_delta_million_bushels']))
        if not all(math.isfinite(v) for v in [base,actual,delta]): raise ValueError('Nonfinite target')
        if abs((actual-base) - delta)>1e-6: raise ValueError('Delta inconsistency')
        ge,change = float(r['selected_nass_good_excellent_pct']),float(r['delta_good_excellent_pp'])
        if not 0 <= ge <= 100 or not -100 <= change <= 100: raise ValueError('Invalid NASS metric')
        year_start(r['marketing_year'])
        result.append(Obs(r['marketing_year'],r['forecast_origin_utc'],r['target_release_schedule_utc'],
                          r['base_release_schedule_utc'],base,actual,delta,ge,change,
                          r['selected_nass_date'],r['selected_nass_usable_after_utc'],False))
    result.sort(key=lambda v:v.origin)
    if len(set(o.marketing_year for o in result))!=4: raise ValueError('Expected four marketing-year cohorts')
    if [len([o for o in result if o.marketing_year==yr]) for yr in ['2023/24','2024/25','2025/26','2026/27']] != [6,6,4,5]:
        raise ValueError('Marketing-year cohort distribution changed')
    return result, checksum


def feature(o: Obs) -> tuple[float,float]: return (o.ge,o.ge_change)


def train_ridge(train: list[Obs], alpha: float=ALPHA) -> dict:
    """Two-feature ridge with standardized training features and unpenalized intercept.
    2x2 solve avoids package downloads and uses *training rows only*.
    """
    if len(train)<MIN_TRAIN: raise ValueError('Insufficient training rows')
    if alpha <= 0: raise ValueError('Alpha must be pre-defined and >0')
    X=[feature(o) for o in train]
    y=[o.delta for o in train]
    mu=[statistics.mean(x[j] for x in X) for j in range(2)]
    std=[math.sqrt(statistics.mean((x[j]-mu[j])**2 for x in X)) for j in range(2)]
    std=[v if v>1e-12 else 1.0 for v in std]
    XX=[((a-mu[0])/std[0],(b-mu[1])/std[1]) for a,b in X]
    y0=statistics.mean(y)
    a00=sum(v[0]*v[0] for v in XX)+alpha
    a01=sum(v[0]*v[1] for v in XX)
    a11=sum(v[1]*v[1] for v in XX)+alpha
    c0=sum(v[0]*(actual-y0) for v,actual in zip(XX,y))
    c1=sum(v[1]*(actual-y0) for v,actual in zip(XX,y))
    det=a00*a11-a01*a01
    if det<=0: raise ValueError('Ill-conditioned ridge matrix')
    beta=[(c0*a11-c1*a01)/det, (a00*c1-a01*c0)/det]
    return {'intercept':y0,'feature_means':mu,'feature_stds':std,'beta_standardized':beta,
            'alpha':alpha, 'train_n':len(train)}


def predict_ridge(model: dict, o: Obs) -> float:
    x=feature(o)
    return model['intercept']+sum(model['beta_standardized'][j]*(x[j]-model['feature_means'][j])/model['feature_stds'][j] for j in range(2))


def metric(rows: list[dict], model: str) -> dict:
    errors=[float(r['predict_delta_'+model])-float(r['actual_delta']) for r in rows]
    if not errors: return {'n':0,'mae':None,'rmse':None,'bias':None,'direction_accuracy':None,'beats_A_count':None}
    wins = sum(abs(e)<abs(float(r['predict_delta_A'])-float(r['actual_delta'])) for e,r in zip(errors,rows)) if model!='A' else None
    def sign(v): return 1 if v>0 else (-1 if v<0 else 0)
    return {'n':len(errors), 'mae':round(statistics.mean(abs(e) for e in errors),6),
            'rmse':round(math.sqrt(statistics.mean(e*e for e in errors)),6),
            'bias':round(statistics.mean(errors),6),
            'direction_accuracy':(None if model=='A' else round(statistics.mean(sign(float(r['predict_delta_'+model]))==sign(float(r['actual_delta'])) for r in rows),6)),
            'beats_A_count':wins}


def run_backtest(obs: list[Obs]) -> tuple[list[dict],list[dict],dict]:
    years=sorted({o.marketing_year for o in obs},key=year_start)
    if years != ['2023/24','2024/25','2025/26','2026/27']:
        raise ValueError('Unexpected vintages')
    rows=[]; trace=[]
    for year in years[1:]:
        train=[o for o in obs if year_start(o.marketing_year)<year_start(year)]
        test=[o for o in obs if o.marketing_year==year]
        if len(train)<MIN_TRAIN: raise ValueError('Insufficient first training year')
        if not test: raise ValueError('Empty held-out year')
        # Prior-year targets must already have been published by the earliest held-out origin.
        first_test=min(parse_utc(t.origin) for t in test)
        if any(parse_utc(t.target_release)+timedelta(hours=24)>first_test for t in train):
            raise ValueError('TRAIN_LABEL_ASOF_VIOLATION')
        mean_delta=statistics.mean(o.delta for o in train)
        reg=train_ridge(train)
        trace.append({'held_out_marketing_year':year, 'n_train':len(train),'n_test':len(test),
                      'train_years':';'.join(sorted({o.marketing_year for o in train},key=year_start)),
                      'max_train_label_release':max(o.target_release for o in train),
                      'min_test_origin':min(o.origin for o in test),
                      'B_mean_historical_delta':round(mean_delta,6),
                      'C_intercept':round(reg['intercept'],6),
                      'C_G_E_mean':round(reg['feature_means'][0],6),
                      'C_G_E_std':round(reg['feature_stds'][0],6),
                      'C_delta_GE_mean':round(reg['feature_means'][1],6),
                      'C_delta_GE_std':round(reg['feature_stds'][1],6),
                      'C_beta_GE':round(reg['beta_standardized'][0],6),
                      'C_beta_change_GE':round(reg['beta_standardized'][1],6),
                      'C_ridge_alpha':ALPHA})
        for o in test:
            preds={'A':0.0, 'B':mean_delta,'C':predict_ridge(reg,o)}
            rows.append({'marketing_year':year,'forecast_origin_utc':o.origin,
                         'target_release_schedule_utc':o.target_release,
                         'selected_nass_date':o.nass_date,'selected_nass_usable_after_utc':o.nass_usable,
                         'nass_good_excellent_pct':o.ge,'delta_good_excellent_pp':o.ge_change,
                         'train_n':len(train),'base_ending_stocks':o.base,
                         'actual_target_ending_stocks':o.actual,'actual_delta':o.delta,
                         **{'predict_delta_'+m:round(v,6) for m,v in preds.items()},
                         **{'predicted_ending_stocks_'+m:round(o.base+v,6) for m,v in preds.items()},
                         'pit_certified':str(o.pit_certified).lower(),
                         'prediction_status':'EXPLORATORY_SCHEDULE_PROXY_ONLY'})
    if len(rows)!=15: raise ValueError(f'Expected 15 held-out rows, got {len(rows)}')
    metrics={m:metric(rows,m) for m in ['A','B','C']}
    if metrics['A']['mae']!=115.2: raise ValueError('Unexpected locked 15-row baseline MAE')
    year_metrics={yr:{m:metric([r for r in rows if r['marketing_year']==yr],m) for m in ['A','B','C']} for yr in years[1:]}
    return rows,trace,{'overall':metrics,'by_marketing_year':year_metrics}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows: raise ValueError('Cannot write empty CSV')
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def render_html(review:dict,rows:list[dict]) -> str:
    mets=review['metrics']['overall']
    summary_rows=''.join('<tr><td>'+html.escape(n)+'</td><td>'+str(mets[n]['mae'])+'</td><td>'+str(mets[n]['rmse'])+'</td><td>'+str(mets[n]['direction_accuracy'])+'</td></tr>' for n in ['A','B','C'])
    yearly=''.join('<tr><td>'+html.escape(yr)+'</td><td>'+str(review['metrics']['by_marketing_year'][yr]['A']['n'])+'</td>'+''.join('<td>'+str(review['metrics']['by_marketing_year'][yr][n]['mae'])+'</td>' for n in ['A','B','C'])+'</tr>' for yr in review['test_marketing_years'])
    lines=''.join('<tr><td>'+html.escape(r['forecast_origin_utc'][:10])+'</td><td>'+html.escape(r['marketing_year'])+'</td><td>'+str(r['actual_delta'])+'</td>'+''.join('<td>'+str(r['predict_delta_'+name])+'</td>' for name in ['A','B','C'])+'</tr>' for r in rows)
    return '''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGNAL K3.5 探索性 Walk-forward 回測</title><style>body{font:16px/1.65 system-ui,'Microsoft JhengHei',sans-serif;color:#18263d;background:#f5f7fb;margin:0;padding:32px}.page{max-width:1100px;margin:auto;background:white;padding:28px 36px;border-radius:16px;box-shadow:0 3px 20px #1427440d}h1,h2{color:#173c70}table{width:100%;border-collapse:collapse;margin:14px 0 24px}th,td{padding:9px 10px;border-bottom:1px solid #e2e7ee;text-align:right}th:first-child,td:first-child{text-align:left}th{background:#eaf2fc;color:#29476a}.warning{padding:16px;border-left:5px solid #c27a22;background:#fff8e8}.muted{color:#536579}.scroll{overflow-x:auto}code{background:#eff3f8;padding:2px 6px;border-radius:3px}</style></head><body><main class="page"><h1>SIGNAL K3.5｜探索性 Walk-forward 比較</h1><div class="warning"><b>研究用途，非投資訊號。</b> K3.4.1 原始資料的歷史發布時間尚未逐期獨立驗證，PIT certified = 0；15 個樣本與 3 個測試年度不足以證明預測優勢。所有數值皆為靜態、固定資料快照的回顧性測試。</div><h2>方法</h2><p>依收成年度留出整年；2023/24 僅作訓練，依序測試 2024/25、2025/26、2026/27。每個測試年度僅使用較早收成年度的標籤與統計量；當年度不更新參數。</p><p>A = 假設下期庫存修正 0；B = 前期收成年度庫存修正平均；C = NASS Good+Excellent 與其變化的固定正則化線性回歸（alpha=10、僅以訓練資料標準化）。目標為下期 WASDE 期末庫存修正，單位：百萬蒲式耳。</p><h2>相同 15 筆樣本績效</h2><div class="scroll"><table><tr><th>模型</th><th>MAE ↓</th><th>RMSE ↓</th><th>方向命中率（探索性）</th></tr>'''+summary_rows+'''</table></div><p class="muted">方向命中率：A（零修正）不做方向預測，標示 None；本次 15 筆真實修正中 12 筆為下修（80%），B 的方向命中率亦為 80%，不能視為已證明方向優勢。</p><h2>分年度 MAE</h2><div class="scroll"><table><tr><th>留出年度</th><th>樣本 n</th><th>A 基準</th><th>B 歷史均值</th><th>C NASS ridge</th></tr>'''+yearly+'''</table></div><h2>15 筆固定樣本預測表</h2><div class="scroll"><table><tr><th>預測日期 UTC</th><th>收成年度</th><th>真實修正</th><th>A</th><th>B</th><th>C</th></tr>'''+lines+'''</table></div><h2>結果解讀限制</h2><p>本實驗不是 USDA 發布前的交易回測；官方發布時刻僅用預定時程加安全緩衝表示，未擁有逐筆可取得時間證據。模型也未涵蓋期貨價格、市場共識、交易成本或任何下單條件；無法將較小 MAE 直接轉換成投資獲利。</p><p class="muted">輸入檔（去 BOM、標準化換行）SHA-256: <code>'''+html.escape(review['frozen_input_sha256_canonical'])+'''</code>。完整稽核與逐期參數見 review.json、training_trace.csv。</p></main></body></html>'''


def run(input_path:Path,source_review:Path,out:Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    obs,sha=load_cohort(input_path)
    prior=json.loads(source_review.read_text(encoding='utf-8-sig'))
    if prior.get('status')!='COHORT_FROZEN_EXPLORATORY_PIT_NOT_CERTIFIED':
        raise ValueError('Unexpected K3.4.1 source status')
    if prior.get('exploratory_eligible')!=21 or prior.get('pit_independently_certified')!=0:
        raise ValueError('Unexpected source data quality status')
    rows,trace,met=run_backtest(obs)
    years=['2024/25','2025/26','2026/27']
    def d(m): return round(met['overall']['A']['mae']-met['overall'][m]['mae'],6)
    review={'version':'K3.5-year-blocked-v1','status':RESEARCH_STATUS,
            'research_only':True,'pit_certified':False, 'certified_pit_records':0,
            'input_origin':'user-provided K3.4.1 GitHub Actions Artifact signal-k341-pit-cohort-audit.zip',
            'frozen_input_sha256_canonical':sha,
            'k341_source_status':prior['status'],
            'k341_reported_frozen_content_sha':prior.get('frozen_cohort_content_sha256'),
            'k341_provenance_note':'K3.4.1 SHA value is a separately generated audit value, not the raw CSV SHA; this module asserts normalized CSV bytes instead.',
            'starting_training_year':TRAINING_MARKETING_YEAR,'test_marketing_years':years,
            'frozen_cohort_size':len(obs),'heldout_rows':len(rows),
            'heldout_actual_direction_counts':{'down':sum(o['actual_delta']<0 for o in rows),
                                              'up':sum(o['actual_delta']>0 for o in rows),
                                              'no_change':sum(o['actual_delta']==0 for o in rows)},
            'direction_accuracy_caution':'B 80% direction matches the post-hoc down-share (12/15); the zero-revision A model makes no directional call; this does not establish a direction edge.',
            'train_rows_by_year':{r['held_out_marketing_year']:r['n_train'] for r in trace},
            'model_definitions':{'A':'persistence: predict next WASDE ending-stock revision = 0',
                  'B':'historical mean of prior marketing years eligible revision values',
                  'C':'two feature ridge regression (GE percentage and change in GE percentage points); alpha=10; train-only standardization'},
            'fold_protocol':'expanding, blocked by marketing year; held-out current-year targets are never added to training',
            'label_asof_rule':'training label scheduled release plus 24h <= earliest held-out forecast origin',
            'input_pit_rule':'K3.4.1 scheduled release plus 24h buffer: not independently certified actual release',
            'no_hyperparam_search':True,'ridge_alpha':ALPHA,'metrics':met,
            'mae_gain_over_A':{'B':d('B'),'C':d('C')},
            'limitations':['small n=15 with only three held-out years','historical actual source timestamp evidence not independently verified',
                           'possible data pipeline/source selection bias in frozen cohort','target is USDA inventory revision not commodity price return',
                           'no market consensus, slippage or transaction costs','model-selection should not be performed from these same test folds'],
            'promotion_gate':'BLOCKED: no PIT certification, insufficient independent years, no price-linked net-return validation',
            'errors':[]}
    write_csv(out/'predictions.csv',rows)
    write_csv(out/'training_trace.csv',trace)
    year_rows=[]
    for yr in years:
        for m in ['A','B','C']:
            year_rows.append({'marketing_year':yr,'model':m,**met['by_marketing_year'][yr][m]})
    write_csv(out/'year_metrics.csv',year_rows)
    (out/'review.json').write_text(json.dumps(review,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (out/'review.html').write_text(render_html(review,rows),encoding='utf-8')
    return review


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    here=Path(__file__).resolve().parent
    p.add_argument('--input',type=Path,default=here/'inputs/exploratory_fixed_cohort.csv')
    p.add_argument('--source-review',type=Path,default=here/'inputs/k341_source_review.json')
    p.add_argument('--output',type=Path,default=Path('k35-review'))
    args=p.parse_args()
    report=run(args.input,args.source_review,args.output)
    print(json.dumps({'status':report['status'], 'n':report['heldout_rows'],
                      'A_MAE':report['metrics']['overall']['A']['mae'],
                      'B_MAE':report['metrics']['overall']['B']['mae'],
                      'C_MAE':report['metrics']['overall']['C']['mae']},ensure_ascii=False))


if __name__=='__main__': main()
