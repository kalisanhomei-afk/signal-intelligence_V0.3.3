"""K4.8 prospective USDA FGIS weekly report byte capture, strictly research-only.

A source reported publication time and the runner capture time are distinct facts.
The output is not independent PIT certification.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SOURCES = (
    "https://mymarketnews.ams.usda.gov/filerepo/sites/default/files/3071/2026-11-16/1365706/ams_3071_00353.txt",
    "https://www.ams.usda.gov/mnreports/wa_gr101.txt",
    "https://usda.azureedge.us/mnreports/wa_gr101.txt",
)
ALLOWED_HOSTS={"mymarketnews.ams.usda.gov","www.ams.usda.gov","usda.azureedge.us"}
DATE_EXPECTED="2026-11-16"
WEEK_EXPECTED="2026-11-12"
DECEMBER_RELEASE="2026-12-10T17:00:00Z"
MAX_SOURCE_BYTES=250_000

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")

def extract_header_and_corn(raw:bytes):
    text=raw.decode("utf-8-sig",errors="strict")
    if not text.startswith("WA_GR101"):
        raise ValueError("REPORT_ID_MISMATCH")
    top="\n".join(text.splitlines()[:40])
    # Use only the top summary table; CORN can reoccur in region subsections.
    date_match=re.search(r"(?m)^Washington, DC[ \t]+(?:Mon|Tue|Wed|Thu|Fri)[ \t]+Nov[ \t]+16,[ \t]+2026[ \t]+USDA Market News[ \t]*$",top)
    if not date_match:
        raise ValueError("REPORT_DATE_NOT_EXPECTED")
    if not re.search(r"REPORTED IN WEEK ENDING NOV[ \t]+12,[ \t]+2026",top):
        raise ValueError("WEEK_END_NOT_EXPECTED")
    summary_match=re.search(
        r"(?m)^[ \t]*CORN[ \t]+([\d,]+)[ \t]+([\d,]+)[ \t]+([\d,]+)[ \t]+([\d,]+)[ \t]+([\d,]+)[ \t]*$",
        top)
    if not summary_match:
        raise ValueError("CORN_SUMMARY_NOT_FOUND")
    nums=[int(v.replace(",","")) for v in summary_match.groups()]
    if nums[0]!=865503 or nums[3]!=12463023 or nums[4]!=15851319:
        raise ValueError("REPORT_NUMBERS_UNEXPECTED")
    if any(n<0 for n in nums):
        raise ValueError("INVALID_CORN_SUMMARY")
    return {"report_slug":"WA_GR101",
            "report_date":DATE_EXPECTED,
            "week_end":WEEK_EXPECTED,
            "units":"metric_tons",
            "corn_week_current_mt":nums[0],
            "corn_week_previous_mt":nums[1],
            "corn_week_year_ago_mt":nums[2],
            "corn_marketing_year_to_date_mt":nums[3],
            "corn_prior_marketing_year_to_date_mt":nums[4],
            "raw_report_revision_warning_present":"CORRECTIONS AT BOTTOM OF REPORT" in text}

def fetch(url):
    if url not in SOURCES:
        raise ValueError("UNAPPROVED_SOURCE_URL")
    start=utc_now()
    try:
        with urlopen(Request(url,headers={"User-Agent":"SIGNAL-K4-FGIS-Forward-Evidence/1.0"}),timeout=6) as r:
            final=r.geturl()
            parts=urlsplit(final)
            if parts.scheme!="https" or parts.hostname not in ALLOWED_HOSTS:
                raise ValueError("UNEXPECTED_SOURCE_REDIRECT")
            content=r.read(MAX_SOURCE_BYTES+1)
            if len(content)>MAX_SOURCE_BYTES:
                raise ValueError("OVERSIZED_REPORT")
            return content, {"requested_url":url,"response_url":final,
                             "fetch_started_utc":start,
                             "fetch_finished_utc":utc_now(),
                             "source_etag":r.headers.get("ETag"),
                             "source_last_modified_claim":r.headers.get("Last-Modified"),
                             "source_content_type":r.headers.get("Content-Type")}
    except HTTPError as exc:
        raise ValueError(f"HTTP_{exc.code}") from exc

def capture(output_dir, fetcher=fetch):
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    tries=[]
    for source in SOURCES:
        try:
            raw,metadata=fetcher(source)
            data=extract_header_and_corn(raw)
            parsed_finish=datetime.fromisoformat(metadata["fetch_finished_utc"].replace("Z","+00:00"))
            scheduled=datetime.fromisoformat(DECEMBER_RELEASE.replace("Z","+00:00"))
            if parsed_finish>=scheduled:
                raise ValueError("CAPTURE_NOT_PRE_DECEMBER_RELEASE")
            saved_name="WA_GR101_20261116_official_captured.txt"
            (output_dir/saved_name).write_bytes(raw)
            result={
                "schema":"signal-k48-fgis-prospective-raw-capture-v1",
                "status":"CAPTURED_PRE_DECEMBER_RELEASE_NOT_INDEPENDENT_PIT_CERTIFIED",
                "hypothesis_id":"H-CORN-001",
                "source":metadata,
                "source_report":data,
                "selected_official_historical_version_path":"/3071/2026-11-16/1365706/" in metadata["response_url"],
                "source_historical_url_is_cryptographically_immutable":False,
                "source_raw_file":saved_name,
                "source_raw_sha256":hashlib.sha256(raw).hexdigest(),
                "source_raw_bytes":len(raw),
                "future_wasde_scheduled_utc":DECEMBER_RELEASE,
                "capture_before_event_verified_by_local_clock":True,
                "source_report_first_publication_utc_independently_verified":False,
                "source_history_corrections_eliminated":False,
                "repo_commit_provides_independent_timestamp_certificate":False,
                "predictive_edge_verified":False,
                "trade_eligible":False,
                "attempts":tries,
            }
            break
        except (ValueError, UnicodeError, URLError, TimeoutError, OSError) as exc:
            tries.append({"url":source,"status":"UNAVAILABLE_OR_REJECTED","error_type":type(exc).__name__,
                          "error_code":str(exc)[:60] if isinstance(exc,ValueError) else None})
    else:
        result={"schema":"signal-k48-fgis-prospective-raw-capture-v1",
                "status":"BLOCKED_NO_VALID_OFFICIAL_RAW_BYTES",
                "attempts":tries, "source_raw_sha256":None,"source_raw_file":None,
                "trade_eligible":False,"predictive_edge_verified":False,
                "source_report_first_publication_utc_independently_verified":False}
    (output_dir/"capture_receipt.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",
                                                  encoding="utf-8")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--emit-public-source-for-commit",action="store_true",default=False)
    args=p.parse_args()
    result=capture(args.output)
    print(json.dumps({"status":result["status"],"sha256":result["source_raw_sha256"],
                      "attempts":result["attempts"],"trade_eligible":False}))
    if args.emit_public_source_for_commit and result["source_raw_file"]:
        raw=(args.output/result["source_raw_file"]).read_bytes()
        print("K48_ARCHIVE_REPORT_JSON="+json.dumps(raw.decode("utf-8"),ensure_ascii=True))
        print("K48_ARCHIVE_RECEIPT_JSON="+json.dumps(result,ensure_ascii=True))

if __name__=="__main__":
    main()
