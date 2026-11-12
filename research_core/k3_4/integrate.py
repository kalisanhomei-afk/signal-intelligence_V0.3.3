#!/usr/bin/env python3
"""SIGNAL K3.4: official-source backfill + conservative point-in-time research join.

Standalone Python 3.10+ stdlib. Does not train a model or emit trading signals.
The release-date timestamps in archived WASDE records and K31 manually extracted
observations are convention/proxy timestamps, not verified ingestion timestamps.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import math
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ARCHIVE = 'https://esmis.nal.usda.gov/publication/crop-progress'
ALLOWED = {'esmis.nal.usda.gov', 'www.usda.gov', 'usda.gov', 'usda.azureedge.us'}
MONTH_PATTERN = r'(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
DATE_RE = re.compile(rf'{MONTH_PATTERN}\s+(?P<day>\d{{1,2}}),?\s+(?P<year>20\d{{2}})', re.I)
STOCK_COLS = {'release_at', 'marketing_year', 'metric', 'value', 'unit', 'source_url'}
WASDE_FIELDS = {
    'Area Planted': ('planted_area_million_acres', 'Million Acres'),
    'Area Harvested': ('harvested_area_million_acres', 'Million Acres'),
    'Yield per Harvested Acre': ('yield_bushels_per_acre', 'Bushels'),
    'Beginning Stocks': ('beginning_stocks_million_bushels', 'Million Bushels'),
    'Production': ('production_million_bushels', 'Million Bushels'),
    'Imports': ('imports_million_bushels', 'Million Bushels'),
    'Supply, Total': ('total_supply_million_bushels', 'Million Bushels'),
    'Feed and Residual': ('feed_residual_million_bushels', 'Million Bushels'),
    'Food, Seed & Industrial': ('food_seed_industrial_million_bushels', 'Million Bushels'),
    'Ethanol & by-products': ('ethanol_million_bushels', 'Million Bushels'),
    'Domestic, Total': ('total_domestic_million_bushels', 'Million Bushels'),
    'Exports': ('exports_million_bushels', 'Million Bushels'),
    'Use, Total': ('total_use_million_bushels', 'Million Bushels'),
    'Ending Stocks': ('ending_stocks_million_bushels', 'Million Bushels'),
}
WASDE_COLS = {'ReportTitle', 'Attribute', 'Commodity', 'Region', 'MarketYear', 'Value', 'Unit', 'ReleaseDate'}
NASS_COLS = ['source_date','week_ending','marketing_year','state_count','very_poor','poor','fair','good','excellent',
             'good_excellent_pct','available_at_proxy_utc','source_url','source_sha256','provenance','timestamp_quality']
BALANCE_COLS = ['release_at_proxy_utc','release_date','marketing_year',*list(x[0] for x in WASDE_FIELDS.values()),
                'balance_residual_million_bushels','source_url','source_sha256','quality_status']
JOIN_COLS = ['marketing_year','forecast_origin_proxy_utc','target_release_proxy_utc','base_ending_stocks',
             'target_ending_stocks','target_delta_million_bushels','nass_source_date','nass_available_proxy_utc',
             'nass_good_excellent_pct','previous_nass_source_date','selected_observation_change_pp',
             'nass_age_days','feature_status','pit_status','target_is_future_of_origin']


def allowed(url: str, hosts=ALLOWED) -> bool:
    p = urlsplit(url)
    return p.scheme == 'https' and (p.hostname or '').lower() in hosts and not p.username and not p.password


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def download(url: str, max_bytes: int=4_000_000, tries: int=2, timeout: int=25) -> bytes:
    if not allowed(url):
        raise ValueError(f'Non-allowlisted URL: {url}')
    for attempt in range(tries):
        try:
            req = Request(url, headers={'User-Agent':'SIGNAL-K34-research/1.0 (public USDA data)', 'Accept':'text/html,text/plain,text/csv,*/*'})
            with urlopen(req, timeout=timeout) as resp:
                if not allowed(resp.geturl()):
                    raise ValueError(f'Download redirected to unapproved host: {resp.geturl()}')
                data = resp.read(max_bytes+1)
                if len(data)>max_bytes:
                    raise ValueError(f'Oversized response > {max_bytes} bytes')
                return data
        except Exception:
            if attempt+1 == tries:
                raise
            time.sleep(1.0 * (attempt+1))
    raise RuntimeError('unreachable')


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active_href=None
        self.active_text=[]
        self.items=[]
    def handle_starttag(self, tag, attrs):
        if tag=='a':
            self.active_href=dict(attrs).get('href','')
            self.active_text=[]
    def handle_data(self, data):
        if self.active_href is not None:
            self.active_text.append(data)
    def handle_endtag(self, tag):
        if tag=='a' and self.active_href is not None:
            self.items.append((self.active_href,' '.join(self.active_text)))
            self.active_href=None
            self.active_text=[]


def archive_links(page_html: str):
    """Extract published TXT URLs and release dates from the USDA ESMIS page.

    Fail closed: no plausible date and explicit .txt link -> no release record.
    """
    parser=Anchors(); parser.feed(page_html)
    result=[]
    for href,label in parser.items:
        full=urljoin(ARCHIVE,html.unescape(href))
        if not allowed(full) or not re.search(r'\.txt(?:[?#]|$)',full,re.I):
            continue
        m=DATE_RE.search(label)
        if not m:
            continue
        # Full/abbreviated month names both supported.
        token=m.group('month')[:3].title()
        when=date(int(m.group('year')),datetime.strptime(token,'%b').month,int(m.group('day')))
        if not re.search(r'prog\d{4}\.txt',urlsplit(full).path,re.I):
            continue
        result.append((when,full))
    return result


def discover_nass(start_year:int,end_year:int,max_pages:int,fetch=download):
    results={}; page_log=[]
    for page in range(max_pages):
        url=ARCHIVE if page==0 else f'{ARCHIVE}?page={page}'
        try:
            body=fetch(url,max_bytes=1_000_000)
            links=archive_links(body.decode('utf-8','replace'))
            page_log.append({'page':page,'url':url,'links':len(links),'status':'OK'})
            if not links:
                page_log[-1]['status']='NO_LINKS'; break
            for when,link in links:
                if start_year<=when.year<=end_year:
                    if when in results and results[when]!=link:
                        page_log.append({'page':page,'status':'DUPLICATE_RELEASE_URL','release_date':str(when)})
                    results.setdefault(when,link)
            # Reached older than requested range: archive sorted newest-first.
            if min(d for d,_ in links).year < start_year:
                break
        except Exception as exc:
            page_log.append({'page':page,'url':url,'status':'FAILED','error':f'{type(exc).__name__}: {exc}'})
            break
    return [(d,results[d]) for d in sorted(results)],page_log


def parse_nass_txt(raw:bytes, url:str, expected_release:date|None=None):
    """Parse a single contemporary corn-condition block, never 'previous week/year'."""
    s=raw.decode('utf-8-sig','replace')
    m= re.search(r'\bReleased\s+('+MONTH_PATTERN+r'\s+\d{1,2},?\s+20\d{2})',s,re.I)
    # Nested named month group conflicts? Parse with generic date regex below.
    released=DATE_RE.search(m.group(1)) if m else None
    if not released:
        raise ValueError('Missing NASS "Released Month Day, Year" header')
    released_date=date(int(released.group('year')),datetime.strptime(released.group('month')[:3].title(),'%b').month,int(released.group('day')))
    if expected_release and released_date!=expected_release:
        raise ValueError(f'Release date mismatch {released_date} vs {expected_release}')
    # Restrict to Corn Condition block. No soybean or previous-week fallbacks.
    head=re.search(r'(?im)^\s*Corn Condition\s*-\s*Selected States\s*:\s*Week Ending\s*([^\r\n]+)',s)
    if not head:
        raise ValueError('NO_CORN_CONDITION_BLOCK')
    block=s[head.end():]
    next_heading=re.search(r'(?m)^\s*(?:Soybean|Soybeans|Cotton|Sorghum|Winter Wheat|Wheat|Peanut|Peanuts|Rice|Oats|Barley)\b',block)
    if next_heading:
        block=block[:next_heading.start()]
    week_end_m=DATE_RE.search(head.group(1))
    if not week_end_m:
        raise ValueError('Missing week-ending date')
    week_ending=date(int(week_end_m.group('year')),datetime.strptime(week_end_m.group('month')[:3].title(),'%b').month,int(week_end_m.group('day')))
    if abs((released_date-week_ending).days)>12 or week_ending>released_date:
        raise ValueError('Inconsistent release/week-ending dates')
    matching=[]
    for line in block.splitlines():
        x=re.match(r'^\s*(\d{1,2})\s+States\s*\.{2,}\s*:\s*((?:\s*\d{1,3}\s*){5})\s*$',line)
        if x:
            values=[int(k) for k in re.findall(r'\d+',x.group(2))]
            if len(values)==5 and sum(values)==100:
                matching.append((int(x.group(1)),values))
    if len(matching)!=1:
        raise ValueError(f'Expected one five-part national selected-states row, got {len(matching)}')
    state_count,values=matching[0]
    if not 10<=state_count<=25:
        raise ValueError('Unexpected state count')
    # K31 source timing convention: next calendar day 12:00 UTC; NOT official exact time.
    available=datetime.combine(released_date+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc)+timedelta(hours=12)
    return {'source_date':str(released_date),'week_ending':str(week_ending),'marketing_year':f'{released_date.year}/{str(released_date.year+1)[-2:]}',
            'state_count':state_count, **dict(zip(['very_poor','poor','fair','good','excellent'],values)),
            'good_excellent_pct':values[3]+values[4],'available_at_proxy_utc':available.isoformat().replace('+00:00','Z'),
            'source_url':url,'source_sha256':digest(raw),'provenance':'official_raw_txt',
            'timestamp_quality':'next_day_noon_utc_proxy_NOT_VERIFIED'}


def parse_manual_k31(path:Path):
    obj=json.loads(path.read_text(encoding='utf-8-sig'))
    out=[]
    for r in obj['records']:
        numbers=[int(r[x]) for x in ['very_poor','poor','fair','good','excellent']]
        if sum(numbers)!=100:
            raise ValueError('K31 manually transcribed selected-state percentages do not sum to 100')
        m=re.match(r'\s*(\d+)\s+States',r['source_row'])
        if not m or not allowed(r['source_uri']):
            raise ValueError('Manual K31 lacks approved source')
        d=dict(source_date=r['source_date'],week_ending=r['week_ending'],
               marketing_year=f"{r['source_date'][:4]}/{str(int(r['source_date'][:4])+1)[-2:]}",
               state_count=int(m.group(1)),**dict(zip(['very_poor','poor','fair','good','excellent'],numbers)),
               good_excellent_pct=numbers[3]+numbers[4],
               available_at_proxy_utc=r['available_at_proxy_utc'].replace('+00:00','Z'),
               source_url=r['source_uri'],source_sha256='',provenance='K31_manual_official_excerpt',
               timestamp_quality='next_day_noon_utc_proxy_NOT_VERIFIED')
        out.append(d)
    return out


def combine_nass(official:list[dict],manual:list[dict]):
    out={};issues=[]
    for r in manual:
        key=r['source_date'];
        if key in out: raise ValueError('Duplicate K31 date')
        out[key]=r
    for r in official:
        key=r['source_date']
        if key in out:
            old=out[key]
            if (old['good_excellent_pct']!=r['good_excellent_pct'] or old['state_count']!=r['state_count']
                    or any(old[k]!=r[k] for k in ['very_poor','poor','fair','good','excellent'])):
                issues.append({'status':'K31_VS_OFFICIAL_CONFLICT','date':key,'manual':old['good_excellent_pct'],'official':r['good_excellent_pct']})
                # Never silently overwrite mismatched historical data.
                continue
        out[key]=r  # promote verified exact-source bytes over manual excerpt
    return sorted(out.values(),key=lambda v:v['source_date']),issues


def stock_rows(path:Path):
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f)
        if not STOCK_COLS<=set(rd.fieldnames or []):
            raise ValueError('K3.3 historical vintage CSV schema changed')
        rows=list(rd)
    out=[];seen=set()
    for row in rows:
        if row['metric']!='ending_stocks' or row['unit']!='million_bushels' or not allowed(row['source_url']):
            raise ValueError('Unexpected K3.3 stock series fields')
        t=datetime.fromisoformat(row['release_at'].replace('Z','+00:00'))
        if t.tzinfo is None: raise ValueError('K3.3 vintage must have timezone')
        value=float(row['value'])
        if not math.isfinite(value) or value<0: raise ValueError('Bad stock value')
        key=(t.date(),row['marketing_year'])
        if key in seen: raise ValueError('Duplicated K3.3 release/market year')
        seen.add(key)
        out.append({'release_at_proxy_utc':t.astimezone(timezone.utc).isoformat().replace('+00:00','Z'),
                    'release_date':str(t.date()),'marketing_year':row['marketing_year'],
                    'ending_stocks':value,'source_url':row['source_url']})
    return sorted(out,key=lambda r:r['release_at_proxy_utc'])


def parse_wasde_csv(raw:bytes, source_url:str, market_year:str, release_date:str):
    with io.StringIO(raw.decode('utf-8-sig','replace')) as stream:
        rd=csv.DictReader(stream)
        if not WASDE_COLS<=set(rd.fieldnames or []):
            raise ValueError('Unexpected WASDE consolidated CSV schema')
        items={}
        for r in rd:
            if not (r['ReportTitle'].strip()=='U.S. Feed Grain and Corn Supply and Use'
                    and r['Commodity'].strip()=='Corn' and r['Region'].strip()=='United States'
                    and r['MarketYear'].strip()==market_year
                    and r['ReleaseDate']==release_date
                    and r['Attribute'].strip() in WASDE_FIELDS):
                continue
            attr=r['Attribute'].strip()
            key,unit=WASDE_FIELDS[attr]
            if r['Unit']!=unit or r.get('AnnualQuarterFlag','Annual')!='Annual':
                raise ValueError(f'Unexpected unit/period for {attr}: {r["Unit"]}')
            if key in items: raise ValueError(f'Duplicate supply attribute {attr}')
            val=float(r['Value'])
            if not math.isfinite(val):raise ValueError(f'Non-finite {attr}')
            items[key]=val
    result={key:'' for key,_ in WASDE_FIELDS.values()}
    result.update(items)
    result.update(source_url=source_url,source_sha256=digest(raw),quality_status='')
    expected=['beginning_stocks_million_bushels','production_million_bushels','imports_million_bushels',
              'total_supply_million_bushels','total_use_million_bushels','ending_stocks_million_bushels']
    if not all(k in items for k in expected):
        raise ValueError(f'Missing balance values: {sorted(set(expected)-set(items))}')
    a=items['beginning_stocks_million_bushels']+items['production_million_bushels']+items['imports_million_bushels']
    b=items['total_use_million_bushels']+items['ending_stocks_million_bushels']
    residual=round(a-b,4)
    result['balance_residual_million_bushels']=residual
    result['quality_status']='PASS_ROUNDING_TOLERANCE' if abs(residual)<=3 else 'BALANCE_MISMATCH'
    return result


def get_wasde_balance(stocks:list[dict],audit_path:Path,fetch=download):
    audit=json.loads(audit_path.read_text(encoding='utf-8-sig'))
    entries={r['release_month']:r for r in audit['sources']}
    balances=[];fail=[]
    for stock in stocks:
        month=stock['release_date'][:7]
        info=entries.get(month)
        if not info:
            fail.append({'release_date':stock['release_date'],'error':'NO_K33_SOURCE_MANIFEST'});continue
        url=info['url']
        try:
            data=fetch(url,max_bytes=3_000_000)
            if digest(data)!=info['sha256']:
                raise ValueError('Source file SHA256 changed since K3.3: do not substitute revised data')
            parsed=parse_wasde_csv(data,url,stock['marketing_year'],stock['release_date'])
            if abs(parsed['ending_stocks_million_bushels']-stock['ending_stocks'])>0.01:
                raise ValueError('K3.3 ending-stocks mismatch')
            parsed.update(release_at_proxy_utc=stock['release_at_proxy_utc'],
                          release_date=stock['release_date'],marketing_year=stock['marketing_year'])
            balances.append(parsed)
        except Exception as exc:
            fail.append({'release_date':stock['release_date'],'source_url':url,'error':f'{type(exc).__name__}: {exc}'})
    return balances,fail


def transitions(stocks):
    by_year=defaultdict(list)
    for r in stocks:by_year[r['marketing_year']].append(r)
    out=[]
    for year,rr in sorted(by_year.items()):
        for base,target in zip(rr,rr[1:]):
            out.append((base,target))
    return sorted(out,key=lambda pair:pair[1]['release_at_proxy_utc'])


def make_join(stocks:list[dict],nass:list[dict]):
    all_pairs=transitions(stocks)
    output=[]
    for base,target in all_pairs:
        origin=datetime.fromisoformat(base['release_at_proxy_utc'].replace('Z','+00:00'))+timedelta(days=1)
        known=[r for r in nass if datetime.fromisoformat(r['available_at_proxy_utc'].replace('Z','+00:00'))<origin
               and int(r['source_date'][:4])==int(base['marketing_year'][:4])]
        known.sort(key=lambda r:r['available_at_proxy_utc'])
        current=known[-1] if known else None
        prev=known[-2] if len(known)>1 else None
        lag=(origin.date()-date.fromisoformat(current['source_date'])).days if current else None
        stale=lag is not None and lag>35
        status=('NO_IN_SEASON_NASS' if not current else 'STALE_NASS' if stale else
                'ONLY_ONE_K31_OBSERVATION' if not prev else 'AVAILABLE_PROXY_ONLY')
        target_dt=datetime.fromisoformat(target['release_at_proxy_utc'].replace('Z','+00:00'))
        output.append({'marketing_year':base['marketing_year'],'forecast_origin_proxy_utc':origin.isoformat().replace('+00:00','Z'),
                       'target_release_proxy_utc':target['release_at_proxy_utc'],
                       'base_ending_stocks':base['ending_stocks'],'target_ending_stocks':target['ending_stocks'],
                       'target_delta_million_bushels':round(target['ending_stocks']-base['ending_stocks'],6),
                       'nass_source_date':current['source_date'] if current else '',
                       'nass_available_proxy_utc':current['available_at_proxy_utc'] if current else '',
                       'nass_good_excellent_pct':current['good_excellent_pct'] if current else '',
                       'previous_nass_source_date':prev['source_date'] if prev else '',
                       'selected_observation_change_pp':(current['good_excellent_pct']-prev['good_excellent_pct']) if current and prev else '',
                       'nass_age_days':lag if lag is not None else '',
                       'feature_status':status,
                       'pit_status':'PROXY_ONLY_NOT_INDEPENDENTLY_VERIFIED',
                       'target_is_future_of_origin':str(target_dt>origin).lower()})
    return output


def write_csv(path:Path,cols:list[str],rows:list[dict]):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)


def run(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    stocks=stock_rows(Path(args.stocks_csv))
    manual=parse_manual_k31(Path(args.k31_json))
    errors=[];off=[];page_log=[];discovered=[];not_reported=[]
    if args.fetch_nass:
        discovered,page_log=discover_nass(args.start_year,args.end_year,args.max_pages)
        if len(discovered)>args.max_reports:
            errors.append({'type':'NASS_DISCOVERY_LIMIT','discovered':len(discovered),'cap':args.max_reports})
            discovered=discovered[:args.max_reports]
        for d,url in discovered:
            try:
                raw=download(url,max_bytes=1_000_000)
                off.append(parse_nass_txt(raw,url,d))
            except ValueError as exc:
                if str(exc)=='NO_CORN_CONDITION_BLOCK':
                    not_reported.append({'release_date':str(d),'url':url,'reason':'CORN_CONDITION_NOT_REPORTED'})
                else:
                    errors.append({'type':'NASS_PARSE_OR_FETCH_FAILED','release_date':str(d),'url':url,'detail':f'{type(exc).__name__}: {exc}'})
            except Exception as exc:
                errors.append({'type':'NASS_PARSE_OR_FETCH_FAILED','release_date':str(d),'url':url,'detail':f'{type(exc).__name__}: {exc}'})
    nass,conflicts=combine_nass(off,manual)
    errors.extend(conflicts)
    balances=[];wasde_errors=[]
    if args.fetch_wasde:
        balances,wasde_errors=get_wasde_balance(stocks,Path(args.audit_json))
        errors.extend({'type':'WASDE_FETCH_FAILED',**r} for r in wasde_errors)
    joined=make_join(stocks,nass)
    write_csv(out/'nass_corn_condition.csv',NASS_COLS,nass)
    write_csv(out/'wasde_corn_balance.csv',BALANCE_COLS,balances)
    write_csv(out/'pit_join.csv',JOIN_COLS,joined)
    mae=sum(abs(float(r['target_delta_million_bushels'])) for r in joined)/len(joined) if joined else None
    coverage={year:sum(1 for r in nass if r['source_date'].startswith(str(year))) for year in range(args.start_year,args.end_year+1)}
    official_coverage={year:sum(1 for r in off if r['source_date'].startswith(str(year))) for year in range(args.start_year,args.end_year+1)}
    stats={'version':'K3.4-history-integration-v1','classification':'DATA_ENGINEERING_ONLY_NOT_TRAINED_MODEL',
           'base_K33_stocks':len(stocks),'base_K33_transitions':len(joined),
           'persistence_baseline_MAE_million_bushels':round(mae,4) if mae is not None else None,
           'k31_manual_observations':len(manual),'nass_official_discovered':len(discovered),
           'nass_official_parsed':len(off),'nass_total_usable':len(nass), 'nass_year_counts':coverage, 'nass_official_year_counts':official_coverage,
           'nass_releases_without_corn_condition':len(not_reported), 'nonreported_releases':not_reported,
           'nass_conflicts':len(conflicts), 'wasde_balance_verified':len(balances),
           'wasde_balance_error_count':len(wasde_errors),
           'join_has_nass':sum(bool(r['nass_source_date']) for r in joined),
           'join_has_two_nass':sum(r['feature_status']=='AVAILABLE_PROXY_ONLY' for r in joined),
           'join_pit_verified':0,'join_target_in_future':sum(r['target_is_future_of_origin']=='true' for r in joined),
           'source_discovery_status':'NOT_REQUESTED' if not args.fetch_nass else
                                     'OK' if page_log and page_log[-1]['status']=='OK' else 'INCOMPLETE_OR_FAILED',
           'time_evidence':'K31_NEXT_DAY_NOON_UTC_PROXY; WASDE_REPORT_TIME_CONVENTION; NO_VERIFIED_INGESTION',
           'pit_evidence_certified':False,'source_archive_pages':page_log,'errors':errors}
    # Important: reaching sample thresholds does NOT imply official timestamp certification.
    stats['status']=('DATA_CONFLICT_REVIEW_REQUIRED' if conflicts else
                     'PARTIAL_SOURCE_RECOVERY' if errors or (args.fetch_nass and stats['source_discovery_status']!='OK') else
                     'RESEARCH_ONLY_PIT_UNVERIFIED')
    (out/'audit.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    items=[('K3.3 庫存歷史期數',stats['base_K33_stocks']),('K3.3 同年度修正次數',stats['base_K33_transitions']),
           ('NASS 已取得觀測',stats['nass_total_usable']),('其中官方全文解析',stats['nass_official_parsed']),
           ('WASDE 供需整表',stats['wasde_balance_verified']),('PIT 已完整驗證',stats['join_pit_verified']),
           ('尚需人工／技術查核錯誤',len(errors))]
    table=''.join(f'<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>' for k,v in items)
    out_html='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>SIGNAL K3.4 歷史資料整合稽核</title>
<style>body{font-family:system-ui,"Microsoft JhengHei",sans-serif;max-width:900px;margin:45px auto;padding:0 20px;color:#172536;line-height:1.6}h1{color:#15395a}table{width:100%;border-collapse:collapse}th,td{border:1px solid #dee5eb;padding:11px;text-align:left}th{background:#eff6fb}aside{padding:18px;background:#fff4df;border-left:4px solid #dc9525}code{background:#eef2f6;padding:3px}</style>
<h1>SIGNAL K3.4 · 歷史資料整合稽核</h1><aside><strong>研究限制：</strong>此工具只整理原始來源與時間代理，沒有建立模型、回測優勢或交易建議。歷史資料的「報告發布日期」不等於當時完整可用的證據。</aside>
<h2>數據摘要</h2><table>'''+table+'</table><p>本報告來源：audit.json；請依照失敗清單和來源 SHA-256 進行稽核。</p><p>狀態：<code>'+html.escape(stats['status'])+'</code></p></html>'
    (out/'review.html').write_text(out_html,encoding='utf-8')
    return stats


def main():
    parser=argparse.ArgumentParser(description='SIGNAL K3.4 official research source linkage; no model training')
    parser.add_argument('--stocks-csv',default=str(HERE/'inputs/historical_vintages.csv'))
    parser.add_argument('--audit-json',default=str(HERE/'inputs/vintage_archive_audit.json'))
    parser.add_argument('--k31-json',default=str(HERE/'inputs/k31_selected_observations.json'))
    parser.add_argument('--output',default='k34-review')
    parser.add_argument('--start-year',type=int,default=2023)
    parser.add_argument('--end-year',type=int,default=2026)
    parser.add_argument('--max-pages',type=int,default=23)
    parser.add_argument('--max-reports',type=int,default=180)
    parser.add_argument('--fetch-nass',action='store_true')
    parser.add_argument('--fetch-wasde',action='store_true')
    args=parser.parse_args()
    if not 2010<=args.start_year<=args.end_year<=2026:parser.error('Invalid range')
    if not 1<=args.max_pages<=40 or not 1<=args.max_reports<=300:parser.error('Unreasonable discovery bounds')
    result=run(args)
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_archive_pages','errors')},ensure_ascii=False,indent=2))
    # Tests/integrity should fail when official and manual NASS disagree.
    if result['nass_conflicts']:
        print('DATA CONFLICT: inspect audit.json',file=sys.stderr)
        sys.exit(2)


if __name__=='__main__':main()
