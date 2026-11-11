#!/usr/bin/env python3
"""Manual, allowlisted USDA consolidated WASDE intake. Fail closed on schema drift."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import tempfile
from collections import Counter
from datetime import datetime, time, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ALLOWED = re.compile(r"^/sites/default/files/documents/oce-wasde-report-data-20\d{2}-\d{2}\.csv$")
REQUIRED = {"ReleaseDate","ReportTitle","Commodity","Region","MarketYear","Attribute","Value","Unit","ProjEstFlag"}
TITLE = "u.s. feed grain and corn supply and use"


def allowlist_url(url: str) -> None:
    u=urlsplit(url)
    if (u.scheme != "https" or u.netloc not in ("www.usda.gov","usda.azureedge.us")
        or not ALLOWED.fullmatch(u.path) or u.query or u.fragment or u.username or u.password):
        raise ValueError("Refusing URL not matching the USDA consolidated WASDE CSV allowlist")


def fetch_official(url: str, target: Path) -> None:
    allowlist_url(url)
    req=Request(url,headers={"User-Agent":"SIGNAL-K3.2-research-intake/1.0"})
    with urlopen(req,timeout=45) as r, target.open("wb") as f:
        final_url=r.geturl()
        allowlist_url(final_url)
        total=0
        while True:
            block=r.read(1024*256)
            if not block: break
            total+=len(block)
            if total>35*1024*1024:raise ValueError("Official CSV unexpectedly large >35 MB")
            f.write(block)
    if not target.read_bytes().startswith((b'ReportDate',b'WasdeNumber',b'\xef\xbb\xbf')):
        # Some valid archives may use a different first column; strict column header validation below is authoritative.
        pass


def normalize_title(s: str) -> str:
    return ' '.join(s.lower().replace('’',"'").split())


def ingest(input_csv: Path, source_url: str, out_csv: Path, out_audit: Path, start_year: int=2023) -> dict:
    allowlist_url(source_url)
    data=input_csv.read_bytes()
    if not data or len(data)>35*1024*1024:raise ValueError("Unexpected input size")
    fingerprint=hashlib.sha256(data).hexdigest()
    selected={}
    reasons=Counter()
    with input_csv.open('r',newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        missing=REQUIRED-set(reader.fieldnames or [])
        if missing:raise ValueError(f"USDA schema differs. Missing fields: {sorted(missing)}; received {reader.fieldnames}")
        for i,row in enumerate(reader,2):
            if not re.match(r"^20\d\d-\d\d-\d\d$",(row.get('ReleaseDate') or '')):
                reasons['bad_date']+=1;continue
            release_date=datetime.strptime(row['ReleaseDate'],'%Y-%m-%d').date()
            if release_date.year<start_year:reasons['outside_scope']+=1;continue
            if TITLE not in normalize_title(row['ReportTitle'] or ''):
                reasons['wrong_table']+=1;continue
            if (row['Commodity'] or '').strip().lower()!='corn' or normalize_title(row['Region'] or '') not in ('united states','us','u.s.'):
                reasons['wrong_product_or_region']+=1;continue
            if (row['Attribute'] or '').strip().lower() not in ('ending stocks',):
                reasons['wrong_attribute']+=1;continue
            if 'proj' not in (row['ProjEstFlag'] or '').lower():
                reasons['not_projection']+=1;continue
            if normalize_title(row['Unit']) not in ('million bushels','mil. bushels'):
                raise ValueError(f"Unexpected corn unit at input line {i}: {row['Unit']}")
            market_year=(row['MarketYear'] or '').strip()
            if not re.fullmatch(r"20\d{2}/\d{2}",market_year):
                raise ValueError(f"Unexpected market year line {i}: {market_year}")
            try:value=float(row['Value'].replace(',',''))
            except Exception as exc:raise ValueError(f"Bad numeric at line {i}") from exc
            if value<0:raise ValueError(f"Negative ending stocks line {i}")
            # USDA WASDE official release convention = 12:00 ET. A separately recorded
            # actual publication timestamp has precedence if provided in later revisions.
            release_at=datetime.combine(release_date,time(12),ZoneInfo('America/New_York'))
            key=(release_at.isoformat(),market_year)
            if key in selected:
                if selected[key]['value'] != value:
                    raise ValueError(f"Conflicting candidate rows for {key}; review manually")
                reasons['exact_duplicate']+=1;continue
            selected[key]={"release_at":release_at.isoformat(),"marketing_year":market_year,
                           "metric":"ending_stocks","value":value,"unit":"million_bushels",
                           "source_url":source_url,"verification":"official_consolidated_vintage"}
    if not selected:
        raise ValueError(f"No matching U.S. corn projected ending-stocks rows; review title/schema/filters. Exclusions={dict(reasons)}")
    out_csv.parent.mkdir(parents=True,exist_ok=True)
    out_audit.parent.mkdir(parents=True,exist_ok=True)
    fields=['release_at','marketing_year','metric','value','unit','source_url','verification']
    with out_csv.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        for key in sorted(selected):writer.writerow(selected[key])
    years=sorted({x['marketing_year'] for x in selected.values()})
    audit={"status":"IMPORTED_UNDER_SCHEMA_CHECK_NEEDS_ARCHIVE_SPOTCHECK", "source_url":source_url,
           "input_sha256":fingerprint,"input_bytes":len(data),"rows_exported":len(selected),
           "marketing_years":years,"excluded_counts":dict(reasons),
           "availability_note":"12 ET is official WASDE release convention; independent archive timestamp verification not yet performed; do not claim lookahead-free model readiness.",
           "warning":"Consolidated USDA historical CSV captures vintages; official individual reports remain the record of authority."}
    out_audit.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    return audit


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--input',type=Path,help="Local unchanged consolidated USDA CSV")
    g.add_argument('--download-url',help="Only strict official USDA historical CSV download URL")
    p.add_argument('--source-url',help="Exact official download URL when importing a local CSV")
    p.add_argument('--start-year',type=int,default=2023)
    p.add_argument('--output',type=Path,default=Path(__file__).parent/'inputs'/'historical_vintages.csv')
    p.add_argument('--audit',type=Path,default=Path(__file__).parent/'out'/'historical_intake_audit.json')
    p.add_argument('--raw-output',type=Path,help='Retain downloaded unmodified raw USDA CSV for replay')
    args=p.parse_args()
    if args.input and not args.source_url:p.error('--source-url required with --input')
    if args.download_url:
        if args.raw_output:
            args.raw_output.parent.mkdir(parents=True,exist_ok=True)
            fetch_official(args.download_url,args.raw_output)
            result=ingest(args.raw_output,args.download_url,args.output,args.audit,args.start_year)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'official.csv'
                fetch_official(args.download_url,path)
                result=ingest(path,args.download_url,args.output,args.audit,args.start_year)
    else:
        result=ingest(args.input,args.source_url,args.output,args.audit,args.start_year)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
