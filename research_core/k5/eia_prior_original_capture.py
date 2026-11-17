"""K5.1 capture previously published EIA WNGSR original source bytes before next release.

One-time evidence acquisition: no API key, no trading and no implied PIT certificate.
Never rewrites a frozen forecast or silently substitutes a later WNGSR.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

URL="https://ir.eia.gov/ngs/wngsr.json"
SCHEDULE="2026-11-19T15:30:00Z"
MAX_BYTES=150_000
TARGET_SERIES="png.nw2_epg0_swo_r48_bcf.w"
REPORT_DATE="2026-Nov-13"
WEEK="2026-11-06"
PRIOR_WEEK="2026-10-30"
YEAR_AGO="2025-11-06"
STOCKS=3862
PREVIOUS_STOCKS=3801
PRIOR_YEAR_STOCKS=3954
FIVE_YEAR_AVG=3787
NET_CHANGE=61

def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")

def parse_utc(x):
    if not isinstance(x,str) or not x.endswith("Z"):
        raise ValueError("INVALID_UTC_TIMESTAMP")
    dt=datetime.fromisoformat(x[:-1]+"+00:00")
    if dt.utcoffset()!=timedelta(0):
        raise ValueError("INVALID_UTC_TIMESTAMP")
    return dt

def validate_data(raw):
    if not isinstance(raw,bytes) or len(raw)==0 or len(raw)>MAX_BYTES:
        raise ValueError("INVALID_EIA_SOURCE_BYTES")
    data=json.loads(raw.decode("utf-8-sig",errors="strict"))
    if not isinstance(data,dict):
        raise ValueError("EIA_JSON_OBJECT_EXPECTED")
    if (data.get("release_name")!="Weekly Natural Gas Storage Report"
        or not str(data.get("release_date","")).startswith(REPORT_DATE+" ")
        or data.get("current_week")!=WEEK
        or data.get("week_ago")!=PRIOR_WEEK
        or data.get("year_ago")!=YEAR_AGO
        or data.get("fuel_type")!="natural gas"
        or data.get("process")!="storage"
        or data.get("periodicity")!="weekly"):
        raise ValueError("WRONG_EIA_RELEASE_OR_WEEK")
    entries=data.get("series")
    if not isinstance(entries,list):
        raise ValueError("MISSING_EIA_SERIES")
    hits=[x for x in entries if isinstance(x,dict) and x.get("series_id")==TARGET_SERIES]
    if len(hits)!=1:
        raise ValueError("AMBIGUOUS_LOWER48_SERIES")
    row=hits[0]
    if (row.get("unitsshort")!="bcf" or row.get("name")!="total lower 48 states"
        or row.get("source")!="U.S. Energy Information Administration"):
        raise ValueError("WRONG_LOWER48_UNITS_OR_PROVENANCE")
    if row.get("data")!=[[WEEK,STOCKS],[PRIOR_WEEK,PREVIOUS_STOCKS],[YEAR_AGO,PRIOR_YEAR_STOCKS]]:
        raise ValueError("WRONG_EIA_STOCKS_OR_DATES")
    c=row.get("calculated",{})
    if not isinstance(c,dict) or any(
        type(c.get(k)) is not int or c[k]!=v for k,v in
        {"net_change":NET_CHANGE,"implied_flow":NET_CHANGE,"5yr-avg":FIVE_YEAR_AVG}.items()
    ):
        raise ValueError("WRONG_EIA_NET_CHANGE_OR_5YR")
    if STOCKS-PREVIOUS_STOCKS!=NET_CHANGE:
        raise ValueError("SOURCE_ACCOUNTING_INCONSISTENT")
    return {
        "source_report_release_date_claim":REPORT_DATE,
        "source_report_release_clock_timezone_unverified":True,
        "week_end":WEEK,
        "prior_week_end":PRIOR_WEEK,
        "year_ago_week_end":YEAR_AGO,
        "series_id":TARGET_SERIES,
        "region":"Lower 48 states",
        "unit":"Bcf",
        "storage_bcf":STOCKS,
        "prior_week_storage_bcf":PREVIOUS_STOCKS,
        "year_ago_storage_bcf":PRIOR_YEAR_STOCKS,
        "five_year_average_storage_bcf":FIVE_YEAR_AVG,
        "net_change_bcf":NET_CHANGE,
        "all_source_revision_flags_independently_audited":False
    }

def fetch():
    started=now()
    try:
        with urlopen(Request(URL,headers={"User-Agent":"SIGNAL-K51-EIA-Prior-Release-Provenance/1.0"}),
                     timeout=18) as response:
            final=response.geturl()
            p=urlsplit(final)
            if (p.scheme!="https" or p.hostname!="ir.eia.gov"
                or p.path not in ("/ngs/wngsr.json","/secure/ngs/wngsr.json")):
                raise ValueError("UNEXPECTED_EIA_REDIRECT")
            raw=response.read(MAX_BYTES+1)
            info={
                "requested_url":URL,
                "response_host":p.hostname,
                "response_path":p.path,
                "signed_redirect_query_deliberately_omitted":True,
                "capture_started_utc":started,
                "capture_finished_utc":now(),
                "content_type_claim":response.headers.get("Content-Type"),
                "last_modified_claim":response.headers.get("Last-Modified"),
                "etag_claim":response.headers.get("ETag")
            }
            return raw,info
    except HTTPError as exc:
        raise ValueError(f"HTTP_{exc.code}") from exc

def capture(out, fetcher=fetch):
    out=Path(out)
    try:
        raw,meta=fetcher()
        summary=validate_data(raw)
        start=parse_utc(meta["capture_started_utc"])
        finish=parse_utc(meta["capture_finished_utc"])
        scheduled=parse_utc(SCHEDULE)
        if not start<=finish<scheduled:
            raise ValueError("CAPTURE_NOT_BEFORE_TARGET_RELEASE")
        if start.date()<datetime(2026,11,13,tzinfo=timezone.utc).date():
            raise ValueError("CAPTURE_BEFORE_REFERENCE_SOURCE_RELEASE")
        digest=hashlib.sha256(raw).hexdigest()
        name=f"EIA_WNGSR_20261113_{digest[:16]}_original.json"
        receipt_name=f"EIA_WNGSR_20261113_{digest[:16]}_receipt.json"
        receipt={
            "schema":"signal-k51-prior-eia-raw-capture-v1",
            "status":"PRIOR_EIA_ORIGINAL_BYTES_CAPTURED_BEFORE_NEXT_EVENT",
            "source":meta,
            "source_report":summary,
            "source_raw_file":name,
            "source_raw_sha256":digest,
            "source_raw_bytes":len(raw),
            "next_eia_event_scheduled_utc":SCHEDULE,
            "official_first_publication_time_independently_verified":False,
            "source_corrections_and_history_independently_verified":False,
            "noaa_ex_ante_vintages_verified":False,
            "market_consensus_pre_event_verified":False,
            "baseline_forecast_already_frozen_and_unchanged":True,
            "investment_edge_verified":False,
            "trade_eligible":False
        }
        out.mkdir(parents=True,exist_ok=True)
        raw_path=out/name
        receipt_path=out/receipt_name
        if raw_path.exists() or receipt_path.exists():
            raise ValueError("SOURCE_ARCHIVE_ALREADY_EXISTS_NO_OVERWRITE")
        with raw_path.open("xb") as f:
            f.write(raw)
        try:
            with receipt_path.open("x",encoding="utf-8") as f:
                json.dump(receipt,f,ensure_ascii=False,indent=2)
                f.write("\n")
        except BaseException:
            raw_path.unlink(missing_ok=True)
            raise
        return receipt
    except (ValueError,UnicodeError,URLError,TimeoutError,OSError) as exc:
        return {
            "schema":"signal-k51-prior-eia-raw-capture-v1",
            "status":"BLOCKED_NO_VALID_EIA_PRIOR_RELEASE_ORIGINAL",
            "source_raw_sha256":None,"source_raw_file":None,
            "error_type":type(exc).__name__,
            "reason":str(exc)[:150] if isinstance(exc,ValueError) else None,
            "trade_eligible":False
        }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--emit-source-to-ci-log-once",action="store_true")
    args=p.parse_args()
    result=capture(args.output_dir)
    print("K51_CAPTURE_RESULT="+json.dumps(result,ensure_ascii=True,separators=(",",":")))
    if result["status"].startswith("BLOCKED"):
        raise SystemExit(2)
    if args.emit_source_to_ci_log_once:
        raw=(args.output_dir/result["source_raw_file"]).read_bytes()
        print("K51_CAPTURE_RAW_JSON="+json.dumps(raw.decode("utf-8"),ensure_ascii=True))
        print("K51_CAPTURE_RECEIPT_JSON="+json.dumps(result,ensure_ascii=True))
if __name__=="__main__":
    main()
