#!/usr/bin/env python3
"""SIGNAL K3.4.1: frozen, research-only time-evidence and as-of cohort audit.

This module is intentionally OFFLINE and standard-library only.
Input snapshots are derived from the user's K3.4 GitHub Actions artifact, NOT
independently reproduced from archived USDA source bytes. Scheduled release
hours are not evidence of exact historical publication, ingestion, or trades.
The pipeline NEVER declares historical PIT evidence independently verified.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import io
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
UTC = timezone.utc
HERE = Path(__file__).resolve().parent
NASS_POLICY_URL = 'https://www.nass.usda.gov/Surveys/Guide_to_NASS_Surveys/Crop_Progress_and_Condition/'
WASDE_POLICY_URL = 'https://www.usda.gov/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report'
WASDE_POLICY_ALTERNATE_URL = 'https://usda.azureedge.us/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report'
IN_FILES = ('pit_join.csv', 'nass_corn_condition.csv', 'wasde_corn_balance.csv', 'audit.json')
ASOF_COLS = [
    'marketing_year','forecast_origin_utc','target_release_schedule_utc',
    'base_release_schedule_utc','base_ending_stocks','target_ending_stocks',
    'target_delta_million_bushels','selected_nass_date',
    'selected_nass_release_schedule_utc','selected_nass_usable_after_utc',
    'selected_nass_good_excellent_pct','previous_nass_date',
    'delta_good_excellent_pp','nass_age_days','feature_status',
    'pit_evidence_grade','pit_certified','baseline_abs_error_million_bushels',
    'k34_original_selected_nass_date','selection_changed_vs_K34',
]
LEDGER_COLS = ['dataset','release_date','market_year','source_url','source_sha256',
               'official_schedule_utc','usable_after_buffer_utc','time_source',
               'time_evidence_grade','exact_per_release_verified','content_hash_rechecked']

class InvalidInput(ValueError):
    pass


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def iso_z(ts: datetime) -> str:
    if ts.tzinfo is None:
        raise InvalidInput('Naive datetime cannot be used for PIT')
    return ts.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def parse_utc(ts: str) -> datetime:
    try:
        dt=datetime.fromisoformat(ts.strip().replace('Z','+00:00'))
        if dt.tzinfo is None:
            raise ValueError('timezone missing')
        return dt.astimezone(UTC)
    except Exception as exc:
        raise InvalidInput(f'Invalid time {ts!r}: {exc}') from exc


def schedule_utc(day: str, kind: str) -> datetime:
    if kind not in ('NASS', 'WASDE'):
        raise ValueError('Unknown report type')
    d=date.fromisoformat(day)
    local=datetime.combine(d, time(16,0) if kind=='NASS' else time(12,0), tzinfo=ET)
    return local.astimezone(UTC)


def read_csv(path: Path, required: set[str]) -> list[dict]:
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not required.issubset(reader.fieldnames or []):
            raise InvalidInput(f'{path.name} missing required columns: {sorted(required-set(reader.fieldnames or []))}')
        rows=list(reader)
        if not rows:
            raise InvalidInput(f'{path.name} is empty')
        return rows


def fnum(value: str, key: str) -> float:
    try:
        x=float(value)
        if not math.isfinite(x): raise ValueError('non-finite')
        return x
    except Exception as exc:
        raise InvalidInput(f'Invalid number {key}={value!r}') from exc


def read_bundle(root: Path):
    missing=[name for name in IN_FILES if not (root/name).is_file()]
    if missing: raise InvalidInput(f'Missing K3.4 snapshot files: {missing}')
    pairs=read_csv(root/'pit_join.csv',
       {'marketing_year','forecast_origin_proxy_utc','target_release_proxy_utc',
        'base_ending_stocks','target_ending_stocks','target_delta_million_bushels','nass_source_date'})
    nass=read_csv(root/'nass_corn_condition.csv',
       {'marketing_year','source_date','good_excellent_pct','source_url','source_sha256',
        'available_at_proxy_utc','provenance'})
    wasde=read_csv(root/'wasde_corn_balance.csv',
       {'release_date','release_at_proxy_utc','marketing_year','ending_stocks_million_bushels',
        'source_url','source_sha256'})
    audit=json.loads((root/'audit.json').read_text(encoding='utf-8-sig'))
    if not isinstance(audit,dict): raise InvalidInput('K3.4 audit is not a dictionary')
    return pairs,nass,wasde,audit


def evidence_ledger(nass: list[dict], wasde: list[dict], safety_hours: int) -> list[dict]:
    evidence=[]
    for kind,rows in [('NASS',nass),('WASDE',wasde)]:
        for row in rows:
            day=row['source_date'] if kind=='NASS' else row['release_date']
            s=schedule_utc(day,kind)
            evidence.append({
               'dataset':kind,'release_date':day,'market_year':row['marketing_year'],
               'source_url':row['source_url'],'source_sha256':row.get('source_sha256',''),
               'official_schedule_utc':iso_z(s),
               'usable_after_buffer_utc':iso_z(s+timedelta(hours=safety_hours)),
               'time_source':NASS_POLICY_URL if kind=='NASS' else WASDE_POLICY_URL,
               'time_evidence_grade':'SCHEDULE_POLICY_ONLY_NOT_PER_RELEASE_PROOF',
               'exact_per_release_verified':'false',
               'content_hash_rechecked':'false',
            })
    return evidence


def validate_k34_timeline(pairs: list[dict], wasde: list[dict]):
    """Cross-check frozen transition rows against vintage balances and scheduled ET clock.

    K3.4's forecast_origin_proxy_utc was generated as base release time + 24h.
    This is a research origin, NOT a claim that an order could trade at that time.
    """
    lookup={}
    for r in wasde:
        t=parse_utc(r['release_at_proxy_utc'])
        expected=schedule_utc(r['release_date'],'WASDE')
        if t!=expected:
            raise InvalidInput(f'WASDE proxy off schedule: {r["release_date"]} {iso_z(t)} != {iso_z(expected)}')
        key=(r['marketing_year'],iso_z(t))
        if key in lookup:raise InvalidInput('Duplicate WASDE date/year')
        lookup[key]=fnum(r['ending_stocks_million_bushels'],'ending_stocks')
    seen=set()
    for p in pairs:
        my=p['marketing_year']
        origin=parse_utc(p['forecast_origin_proxy_utc'])
        t=parse_utc(p['target_release_proxy_utc'])
        base=origin-timedelta(days=1)
        if not base<origin<t: raise InvalidInput(f'Invalid origin/target order for {my} {p["target_release_proxy_utc"]}')
        kb=(my,iso_z(base));kt=(my,iso_z(t))
        if kb not in lookup or kt not in lookup:
            raise InvalidInput(f'Unmatched WASDE baseline or target for {my} {iso_z(t)}')
        if (my,iso_z(t)) in seen: raise InvalidInput(f'Duplicate target {my} {iso_z(t)}')
        seen.add((my,iso_z(t)))
        before=fnum(p['base_ending_stocks'],'base');after=fnum(p['target_ending_stocks'],'target')
        delta=fnum(p['target_delta_million_bushels'],'target_delta')
        if abs(before-lookup[kb])>1e-6 or abs(after-lookup[kt])>1e-6 or abs((after-before)-delta)>1e-6:
            raise InvalidInput(f'Stock/delta mismatch for {my} {iso_z(t)}')
    return lookup


def compute_cohort(pairs: list[dict],nass: list[dict],wasde: list[dict],safety_hours=24,max_age_days=35):
    if not 1<=safety_hours<=168:raise InvalidInput('safety_hours must be between 1 and 168')
    if not 1<=max_age_days<=120:raise InvalidInput('max_age_days must be 1..120')
    validate_k34_timeline(pairs,wasde)
    prepared=defaultdict(list);unique=set()
    for r in nass:
        day=r['source_date'];yr=r['marketing_year'];key=(yr,day)
        if key in unique:raise InvalidInput(f'Duplicate NASS {yr} {day}')
        unique.add(key)
        if not re.fullmatch(r'\d{4}/\d{2}',yr) or int(day[:4])!=int(yr[:4]):
            raise InvalidInput(f'NASS crop year/date mismatch {yr} {day}')
        pct=fnum(r['good_excellent_pct'],'good_excellent_pct')
        if not 0<=pct<=100: raise InvalidInput('NASS percentage out of range')
        schedule=schedule_utc(day,'NASS')
        prepared[yr].append((schedule+timedelta(hours=safety_hours),schedule,r,pct))
    for arr in prepared.values():arr.sort(key=lambda x:x[0])
    out=[]
    for p in pairs:
        origin=parse_utc(p['forecast_origin_proxy_utc']);target=parse_utc(p['target_release_proxy_utc']);yr=p['marketing_year']
        known=[obs for obs in prepared[yr] if obs[0]<=origin]
        cur=known[-1] if known else None
        prev=known[-2] if len(known)>1 else None
        age=(origin.date()-date.fromisoformat(cur[2]['source_date'])).days if cur else None
        if cur is None: status='NO_IN_SEASON_NASS'
        elif age<0: raise InvalidInput('Observation dated after origin')
        elif age>max_age_days:status='STALE_NASS'
        elif prev is None:status='ONLY_ONE_NASS_OBSERVATION'
        else:status='ELIGIBLE_EXPLORATORY_SCHEDULE_ONLY'
        base=fnum(p['base_ending_stocks'],'base')
        targetstock=fnum(p['target_ending_stocks'],'target')
        old=p['nass_source_date'] or ''
        new=cur[2]['source_date'] if cur else ''
        out.append({
          'marketing_year':yr,'forecast_origin_utc':iso_z(origin),
          'target_release_schedule_utc':iso_z(target),
          'base_release_schedule_utc':iso_z(origin-timedelta(days=1)),
          'base_ending_stocks':base,'target_ending_stocks':targetstock,
          'target_delta_million_bushels':round(targetstock-base,6),
          'selected_nass_date':new,
          'selected_nass_release_schedule_utc':iso_z(cur[1]) if cur else '',
          'selected_nass_usable_after_utc':iso_z(cur[0]) if cur else '',
          'selected_nass_good_excellent_pct':cur[3] if cur else '',
          'previous_nass_date':prev[2]['source_date'] if prev else '',
          'delta_good_excellent_pp':(cur[3]-prev[3]) if prev else '',
          'nass_age_days':age if age is not None else '',
          'feature_status':status,
          'pit_evidence_grade':'OFFICIAL_SCHEDULE_AND_SAFETY_BUFFER_NOT_ACTUAL_RELEASE_PROOF',
          'pit_certified':'false',
          'baseline_abs_error_million_bushels':abs(targetstock-base),
          'k34_original_selected_nass_date':old,
          'selection_changed_vs_K34':str(old!=new).lower(),
        })
    return out


def write_csv(path:Path,cols:list[str],rows:list[dict]):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)


def metrics(rows:list[dict]):
    if not rows: return {'n':0,'persistence_mae_million_bushels':None}
    return {'n':len(rows), 'persistence_mae_million_bushels':round(sum(float(r['baseline_abs_error_million_bushels']) for r in rows)/len(rows),6)}


def render_html(report:dict,sample:list[dict]) -> str:
    counts=report.get('cohort_status_counts',{})
    base=report.get('metrics',{})
    lines=''.join(f'<tr><td>{html.escape(k)}</td><td>{v}</td></tr>' for k,v in sorted(counts.items()))
    def metric(k):return html.escape(str(base.get(k,{}).get('persistence_mae_million_bushels','—')))
    samples=''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in
           ['marketing_year','forecast_origin_utc','selected_nass_date','feature_status','target_delta_million_bushels'])+'</tr>' for r in sample)
    status=html.escape(str(report['status']))
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGNAL K3.4.1 PIT 稽核</title><style>body{{font-family:system-ui,-apple-system,"Microsoft JhengHei",sans-serif;max-width:1100px;margin:auto;padding:28px;color:#122033;background:#f7fafc;line-height:1.6}}h1{{font-size:1.8rem}}.warning{{border-left:5px solid #be6b13;background:#fff9e9;padding:16px;border-radius:8px}}.card{{background:#fff;padding:18px 24px;border-radius:12px;margin:16px 0;box-shadow:0 1px 4px #cbd5e1}}table{{border-collapse:collapse;width:100%;font-size:.88rem}}th,td{{border-bottom:1px solid #e4eaf0;padding:8px;text-align:left}}th{{background:#f0f5fa}}.scroll{{overflow-x:auto}}code{{white-space:normal}}</style></head><body>
<h1>SIGNAL K3.4.1｜時間證據與樣本定版</h1><p>狀態：<strong>{status}</strong></p>
<div class="warning"><strong>研究限制：</strong>USDA 官方公布時刻是「一般發布排程」，不是每一期歷史報告已於該分鐘上線的獨立證明。使用額外安全緩衝亦不能取代歷史存取紀錄。本報告的 <strong>PIT 已認證筆數為 0</strong>，不允許用於正式交易能力宣稱。</div>
<div class="card"><h2>資料快照與審核結果</h2><p>歷史基準轉換數：{report.get('total_transitions',0)}；NASS 觀測數：{report.get('nass_observations',0)}；可供探索性實驗：{report.get('exploratory_eligible',0)}；相對 K3.4 選取變更：{report.get('selected_observation_changes',0)}。</p><p>所有樣本前值不變 MAE：{metric('all')} 百萬蒲式耳；探索性同樣本 MAE：{metric('eligible_exploratory')} 百萬蒲式耳。</p><p>時間安全緩衝：{report.get('safety_hours')} 小時；資料新鮮度上限：{report.get('max_age_days')} 天。</p></div>
<div class="card"><h2>樣本分級</h2><table><tr><th>分級</th><th>筆數</th></tr>{lines}</table></div>
<div class="card"><h2>最近 8 筆預測起點（僅供研究）</h2><div class="scroll"><table><tr><th>收成年度</th><th>預測起點 UTC</th><th>選用 NASS</th><th>分級</th><th>庫存變化</th></tr>{samples}</table></div></div>
<div class="card"><h2>不可跨越的驗收界線</h2><p>一、輸入快照已固定，但原始 USDA TXT/CSV 位元組不在本包內，無法以此獨立驗證原檔 SHA。二、下階段若要宣稱正式 PIT，必須有每期報告歷史發布／公開可取得證據或可核驗的資料快照紀錄。三、預測驗證需用相同起點、同一子樣本，並設置樣本外測試。</p><p>官方時間規則：<a href="{NASS_POLICY_URL}">USDA NASS Crop Progress</a>（一般為 16:00 ET）；<a href="{WASDE_POLICY_URL}">USDA WASDE</a>（一般為 12:00 ET）。</p></div>
</body></html>'''


def execute(input_root:Path,output_root:Path,safety_hours=24,max_age_days=35):
    output_root.mkdir(parents=True,exist_ok=True)
    try:
        pairs,nass,wasde,audit=read_bundle(input_root)
        rows=compute_cohort(pairs,nass,wasde,safety_hours,max_age_days)
        ledger=evidence_ledger(nass,wasde,safety_hours)
        eligible=[r for r in rows if r['feature_status']=='ELIGIBLE_EXPLORATORY_SCHEDULE_ONLY']
        contents={name:sha((input_root/name).read_bytes()) for name in IN_FILES}
        selected_changed=sum(r['selection_changed_vs_K34']=='true' for r in rows)
        status_counts=dict(sorted(Counter(r['feature_status'] for r in rows).items()))
        def guard(r):return {k:r[k] for k in ASOF_COLS if k in r}
        freeze=json.dumps([guard(r) for r in rows],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
        config={'safety_hours':safety_hours,'max_age_days':max_age_days,
                'forecast_origin_rule':'prior_WASDE_scheduled_noon_ET_plus_24h',
                'nass_policy_availability_rule':'NASS_scheduled_4pm_ET_plus_safety_hours',
                'nass_season_rule':'source calendar year matches marketing year start',
                'feature_eligibility':'two prior condition reports, latest not older than max_age_days',
                'evidence_certification':'NO historical per-release evidence - research only'}
        report={
           'version':'K3.4.1-pit-cohort-v1','status':'COHORT_FROZEN_EXPLORATORY_PIT_NOT_CERTIFIED',
           'input_snapshot':'User-supplied SIGNAL K3.4 Actions artifact, frozen locally in installer',
           'source_archive_raw_reproduced':False,
           'usda_actual_release_times_independently_verified':False,
           'usda_actual_ingestion_times_independently_verified':False,
           'official_schedule_policy_source':{'NASS':NASS_POLICY_URL,'WASDE':WASDE_POLICY_URL},
           'original_K34_status':audit.get('status','UNKNOWN'),
           'total_transitions':len(rows),'nass_observations':len(nass),'wasde_vintages':len(wasde),
           'exploratory_eligible':len(eligible),'pit_independently_certified':0,
           'selected_observation_changes':selected_changed,
           'cohort_status_counts':status_counts,'metrics':{'all':metrics(rows),'eligible_exploratory':metrics(eligible)},
           'safety_hours':safety_hours,'max_age_days':max_age_days,
           'config':config,'input_sha256':contents,
           'frozen_cohort_content_sha256':sha(freeze),
           'comparison_requirement':'same_prediction_origins_and_target_cohort_for_any_future_model_comparison',
           'errors':[]}
        write_csv(output_root/'pit_evidence_ledger.csv',LEDGER_COLS,ledger)
        write_csv(output_root/'asof_cohort.csv',ASOF_COLS,rows)
        write_csv(output_root/'exploratory_fixed_cohort.csv',ASOF_COLS,eligible)
        (output_root/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (output_root/'review.html').write_text(render_html(report,rows[-8:]),encoding='utf-8')
        return report
    except Exception as exc:
        report={'version':'K3.4.1-pit-cohort-v1','status':'INPUT_VALIDATION_FAILED',
                'pit_independently_certified':0,'errors':[f'{type(exc).__name__}: {exc}']}
        (output_root/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (output_root/'review.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><h1>INPUT_VALIDATION_FAILED</h1><pre>'+html.escape(report['errors'][0])+'</pre></html>',encoding='utf-8')
        raise


def main():
    p=argparse.ArgumentParser(description='SIGNAL K3.4.1 offline PIT-cohort evidence audit')
    p.add_argument('--input-root',default=str(HERE/'inputs'))
    p.add_argument('--output',default='k341-review')
    p.add_argument('--safety-hours',type=int,default=24)
    p.add_argument('--max-age-days',type=int,default=35)
    args=p.parse_args()
    try:
        report=execute(Path(args.input_root),Path(args.output),args.safety_hours,args.max_age_days)
    except Exception as exc:
        print(f'K3.4.1 failed closed: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2
    print(json.dumps({k:report[k] for k in ['status','total_transitions','exploratory_eligible','pit_independently_certified','selected_observation_changes']},ensure_ascii=False))
    return 0

if __name__=='__main__':sys.exit(main())
