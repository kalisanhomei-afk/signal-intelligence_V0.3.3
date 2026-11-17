"""K4.9 generic weekly USDA FGIS WA_GR101 provenance capture (standard library).

Prospective observation, NOT independent publisher PIT certification or trading.
Each report revision is stored under a content-addressed, never-overwrite name.
"""
from __future__ import annotations

import argparse
import calendar
from datetime import date, datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROLLING="https://www.ams.usda.gov/mnreports/wa_gr101.txt"
FIXED_RE=re.compile(r"^/filerepo/sites/default/files/3071/(\d{4}-\d{2}-\d{2})/\d+/ams_3071_\d+\.txt$")
HOSTS={"www.ams.usda.gov","mymarketnews.ams.usda.gov"}
MAX_BYTES=250_000
REPORT_RE=re.compile(
    r"(?m)^Washington,\s*DC[ \t]+(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[ \t]+"
    r"([A-Za-z]{3})[ \t]+(\d{1,2}),[ \t]+(\d{4})[ \t]+USDA Market News[ \t]*$"
)
WEEK_RE=re.compile(r"(?m)\bREPORTED IN WEEK ENDING\s+([A-Z]{3})\s+(\d{1,2}),\s+(\d{4})\b")
CORN_RE=re.compile(r"(?m)^CORN[ \t]+([0-9][0-9,]*)[ \t]+([0-9][0-9,]*)[ \t]+"
                   r"([0-9][0-9,]*)[ \t]+([0-9][0-9,]*)[ \t]+([0-9][0-9,]*)[ \t]*$")

def timestamp(value):
    if not isinstance(value,str) or not value.endswith("Z"):
        raise ValueError("UTC_Z_REQUIRED")
    d=datetime.fromisoformat(value[:-1]+"+00:00")
    if d.utcoffset()!=timedelta(0):
        raise ValueError("UTC_OFFSET_INVALID")
    return d

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")

def allowed(url, expected_report_date):
    p=urlsplit(url)
    if p.scheme!="https" or p.query or p.fragment or p.username or p.password:
        raise ValueError("SOURCE_URL_NOT_ALLOWED")
    if url==ROLLING:
        return True
    if p.hostname!="mymarketnews.ams.usda.gov" or p.port is not None:
        raise ValueError("SOURCE_URL_NOT_ALLOWED")
    m=FIXED_RE.fullmatch(p.path)
    if not m or m.group(1)!=expected_report_date:
        raise ValueError("WRONG_OFFICIAL_HISTORICAL_DATE")
    return True

def parse_report(raw, expected_report_date, expected_week_end):
    report_expected=date.fromisoformat(expected_report_date)
    week_expected=date.fromisoformat(expected_week_end)
    if not 1 <= (report_expected-week_expected).days <= 9:
        raise ValueError("REPORT_WEEK_DATE_ORDER")
    text=raw.decode("utf-8-sig",errors="strict")
    if not text.startswith("WA_GR101"):
        raise ValueError("REPORT_SLUG_MISMATCH")
    lines=text.splitlines()
    header="\n".join(lines[:45])
    h=REPORT_RE.search(header)
    if not h:
        raise ValueError("REPORT_HEADER_UNRECOGNIZED")
    try:
        actual_report=datetime.strptime(
            f"{h.group(2)} {h.group(3)} {h.group(4)}","%b %d %Y").date()
    except ValueError as exc:
        raise ValueError("REPORT_HEADER_DATE_INVALID") from exc
    if actual_report != report_expected:
        raise ValueError("WRONG_REPORT_DATE")
    if calendar.day_abbr[actual_report.weekday()] != h.group(1):
        raise ValueError("REPORT_WEEKDAY_INCONSISTENT")
    g=WEEK_RE.search(header)
    if not g:
        raise ValueError("WEEK_HEADER_NOT_FOUND")
    actual_week=datetime.strptime(
        f"{g.group(1)} {g.group(2)} {g.group(3)}","%b %d %Y").date()
    if actual_week != week_expected:
        raise ValueError("WRONG_WEEK_END")
    # Restrict to the top first summary, not later country/port sections.
    if "GRAINS INSPECTED AND/OR WEIGHED FOR EXPORT" not in header:
        raise ValueError("TOP_SUMMARY_NOT_FOUND")
    rows=list(CORN_RE.finditer(header))
    if len(rows)!=1:
        raise ValueError("AMBIGUOUS_TOP_CORN_ROW")
    values=[int(x.replace(",","")) for x in rows[0].groups()]
    if values[3]<values[0] or any(v<0 for v in values):
        raise ValueError("IMPOSSIBLE_CORN_VOLUMES")
    tab=re.search(r"(?m)^\s*GRAIN[ \t]+"
                  r"(\d{2}/\d{2}/\d{4})[ \t]+(\d{2}/\d{2}/\d{4})[ \t]+"
                  r"(\d{2}/\d{2}/\d{4})",header)
    if not tab:
        raise ValueError("TOP_SUMMARY_COLUMN_DATES_NOT_FOUND")
    cur=date.fromisoformat(datetime.strptime(tab.group(1),"%m/%d/%Y").date().isoformat())
    prev=datetime.strptime(tab.group(2),"%m/%d/%Y").date()
    if cur!=actual_week or prev!=actual_week-timedelta(days=7):
        raise ValueError("COLUMN_DATE_MISMATCH")
    return {
        "report_slug":"WA_GR101",
        "report_date":actual_report.isoformat(),
        "week_end":actual_week.isoformat(),
        "previous_week_end":prev.isoformat(),
        "units":"metric_tons",
        "corn_week_current_mt":values[0],
        "corn_week_previous_mt":values[1],
        "corn_week_year_ago_mt":values[2],
        "corn_marketing_year_to_date_mt":values[3],
        "corn_prior_marketing_year_to_date_mt":values[4],
        "raw_report_revision_warning_present":
            "CORRECTIONS AT BOTTOM OF REPORT" in text,
        "revision_rows_independently_reconciled":False,
    }

def fetch(url):
    started=utcnow()
    try:
        with urlopen(Request(url,headers={"User-Agent":"SIGNAL-K49-FGIS-Prospective/1.0"}),timeout=10) as r:
            actual=r.geturl()
            raw=r.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:
                raise ValueError("OVERSIZED_REPORT")
            return raw,{
                "requested_url":url,"response_url":actual,
                "fetch_started_utc":started,"fetch_finished_utc":utcnow(),
                "source_last_modified_claim":r.headers.get("Last-Modified"),
                "source_etag":r.headers.get("ETag"),
            }
    except HTTPError as e:
        raise ValueError(f"HTTP_{e.code}") from e

def compare_previous(current,prior_raw=None,prior_receipt=None):
    if (prior_raw is None) != (prior_receipt is None):
        raise ValueError("INCOMPLETE_PREVIOUS_SOURCE_PAIR")
    if prior_raw is None:
        return {"status":"NO_VERIFIED_PREVIOUS_WEEK_CAPTURE",
                "previous_week_revision_delta_mt":None,
                "cumulative_implied_other_revisions_mt":None}
    prior=json.loads(Path(prior_receipt).read_text(encoding="utf-8"))
    raw=Path(prior_raw).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=prior.get("source_raw_sha256"):
        raise ValueError("PREVIOUS_RAW_SHA_MISMATCH")
    p=prior.get("source_report",{})
    if p.get("week_end")!=current["previous_week_end"]:
        raise ValueError("PREVIOUS_WEEK_NOT_CONTIGUOUS")
    # Prior report may have a different schema, but must be the same commodity and units.
    if p.get("report_slug")!="WA_GR101" or p.get("units")!="metric_tons":
        raise ValueError("PREVIOUS_REPORT_NOT_COMPARABLE")
    return {
        "status":"PREVIOUS_WEEK_REVISED" if
            current["corn_week_previous_mt"]!=p["corn_week_current_mt"] else "PREVIOUS_WEEK_UNCHANGED",
        "previous_week_original_mt":p["corn_week_current_mt"],
        "previous_week_now_reported_mt":current["corn_week_previous_mt"],
        "previous_week_revision_delta_mt":current["corn_week_previous_mt"]-p["corn_week_current_mt"],
        "cumulative_implied_other_revisions_mt":
            current["corn_marketing_year_to_date_mt"]-
            p["corn_marketing_year_to_date_mt"]-current["corn_week_current_mt"],
        "cumulative_difference_could_reflect_other_corrections":True,
        "prior_raw_sha256":prior["source_raw_sha256"],
    }

def capture(report_date,week_end,cutoff_utc,output_dir, historical_url=None,
            prior_raw=None,prior_receipt=None,fetcher=fetch):
    output_dir=Path(output_dir)
    # Validate temporal and source contracts before touching the filesystem.
    scheduled=timestamp(cutoff_utc)
    if not date.fromisoformat(report_date) < scheduled.date():
        raise ValueError("REPORT_DATE_NOT_BEFORE_WASDE")
    sources=([historical_url] if historical_url else [])+[ROLLING]
    for url in sources:allowed(url,report_date)
    attempts=[]
    for url in sources:
        try:
            raw,source=fetcher(url)
            allowed(source["response_url"],report_date)
            start=timestamp(source["fetch_started_utc"])
            finished=timestamp(source["fetch_finished_utc"])
            if not start <= finished < scheduled:
                raise ValueError("NOT_CAPTURED_BEFORE_WASDE")
            if start.date()<date.fromisoformat(report_date):
                raise ValueError("CAPTURE_BEFORE_SOURCE_REPORT_DATE")
            info=parse_report(raw,report_date,week_end)
            revisions=compare_previous(info,prior_raw,prior_receipt)
            digest=hashlib.sha256(raw).hexdigest()
            short=digest[:16]
            stem=f"WA_GR101_{report_date.replace('-','')}_{short}"
            raw_name=stem+"_official_raw.txt"
            receipt_name=stem+"_capture_receipt.json"
            raw_path=output_dir/raw_name
            receipt_path=output_dir/receipt_name
            result={
                "schema":"signal-k49-fgis-weekly-prospective-capture-v1",
                "status":"CAPTURED_PRE_WASDE_NOT_INDEPENDENT_PIT_CERTIFIED",
                "source":source,
                "source_report":info,
                "prior_report_comparison":revisions,
                "raw_filename":raw_name,
                "receipt_filename":receipt_name,
                "source_raw_sha256":digest,
                "source_raw_bytes":len(raw),
                "future_wasde_scheduled_utc":cutoff_utc,
                "source_first_publication_time_independently_verified":False,
                "source_corrections_independently_certified":False,
                "predictive_edge_verified":False,
                "trade_eligible":False,
                "attempts":attempts,
            }
            if raw_path.exists() or receipt_path.exists():
                if raw_path.exists() and receipt_path.exists() and (
                    raw_path.read_bytes()==raw and
                    json.loads(receipt_path.read_text(encoding="utf-8")).get("source_raw_sha256")==digest):
                    return {**result,"status":"ALREADY_ARCHIVED_IDENTICAL_BYTES"}
                raise ValueError("ARCHIVE_COLLISION_OR_INCOMPLETE_PAIR")
            output_dir.mkdir(parents=True,exist_ok=True)
            with raw_path.open("xb") as f:
                f.write(raw)
            try:
                with receipt_path.open("x",encoding="utf-8") as f:
                    json.dump(result,f,indent=2,ensure_ascii=False)
                    f.write("\n")
            except BaseException:
                raw_path.unlink(missing_ok=True)
                raise
            return result
        except (ValueError,UnicodeError,URLError,TimeoutError,OSError) as exc:
            # Never fall through to rolling on a previously captured archive collision.
            if str(exc)=="ARCHIVE_COLLISION_OR_INCOMPLETE_PAIR":
                raise
            attempts.append({"url":url,"error_type":type(exc).__name__,
                             "reason":str(exc)[:80] if isinstance(exc,ValueError) else None})
    return {
        "schema":"signal-k49-fgis-weekly-prospective-capture-v1",
        "status":"BLOCKED_NO_VALID_OFFICIAL_REPORT",
        "expected_report_date":report_date,
        "expected_week_end":week_end,
        "source_raw_sha256":None,
        "attempts":attempts,
        "trade_eligible":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report-date",required=True,help="YYYY-MM-DD")
    p.add_argument("--week-end",required=True,help="YYYY-MM-DD")
    p.add_argument("--wasde-cutoff-utc",default="2026-12-10T17:00:00Z")
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--historical-url",default=None)
    p.add_argument("--prior-raw",type=Path)
    p.add_argument("--prior-receipt",type=Path)
    args=p.parse_args()
    result=capture(args.report_date,args.week_end,args.wasde_cutoff_utc,args.output_dir,
                   args.historical_url,args.prior_raw,args.prior_receipt)
    print(json.dumps({"status":result["status"],"sha256":result.get("source_raw_sha256"),
                      "raw_filename":result.get("raw_filename"),
                      "receipt_filename":result.get("receipt_filename"),
                      "attempts":result.get("attempts"),"trade_eligible":False}))
    if result["status"].startswith("BLOCKED_"):
        raise SystemExit(2)

if __name__=="__main__":main()
