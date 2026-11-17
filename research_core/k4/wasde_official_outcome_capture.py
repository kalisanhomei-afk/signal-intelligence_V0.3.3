"""K4.11: independent official-only Dec WASDE original-byte capture and V0 score.

A successful official source is enough to score V0 even if an analyst consensus
was never independently observed. Does not modify frozen V0 or manufacture
consensus, backtest or trading edge. USDA December report only after release.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from research_core.k4.fgis_weekly_vintage import timestamp

SCHEMA="signal-k411-corn-official-december-outcome-v1"
URL="https://esmis.nal.usda.gov/sites/default/release-files/796142/wasde1226.txt"
EVENT="USDA-WASDE-2026-12-10"
BARRIER="2026-12-10T17:00:00Z"
FORECAST=1758
MAX_BYTES=1_000_000
EVIDENCE_ROOT=Path(__file__).resolve().parent
FROZEN=EVIDENCE_ROOT/"cases"/"2026-12-10-forward-baseline-forecast.json"
CONTRACT=EVIDENCE_ROOT/"cases"/"2026-12-10-v0-scoring-contract.json"

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")

def source_allowed(value):
    if not isinstance(value,str):
        raise ValueError("WASDE_SOURCE_URL_REQUIRED")
    p=urlsplit(value)
    if (p.scheme!="https" or p.hostname!="esmis.nal.usda.gov"
        or p.path!="/sites/default/release-files/796142/wasde1226.txt"
        or p.query or p.fragment or p.username or p.password or p.port is not None):
        raise ValueError("NOT_EXACT_OFFICIAL_WASDE_DECEMBER_SOURCE")
    return True

def parse_wasde_corn(raw, report_month="December", previous_month="Nov",
                     current_month="Dec"):
    """Pull only U.S. CORN (2026/27) last of four million-bushel columns.

    Reusable on the actual published November report with
    report_month='November', previous_month='Oct', current_month='Nov'.
    """
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_BYTES:
        raise ValueError("INVALID_WASDE_RAW_BYTES")
    txt=raw.decode("utf-8-sig",errors="strict")
    phrase="U.S. Feed Grain and Corn Supply and Use"
    if txt.count(phrase)!=1:
        raise ValueError("WASDE_US_CORN_TABLE_NOT_UNIQUE")
    i=txt.index(phrase)
    pre=txt[max(0,i-110):i]
    if not re.search(r"\bWASDE\s*-\s*\d+\s*-\s*\d+\s+"+re.escape(report_month)+r"\s+2026\b",pre):
        raise ValueError("WRONG_WASDE_REPORT_MONTH")
    table=txt[i: i+6000]
    # No other major table may be used to provide the U.S. corn result.
    boundary=table.find("U.S. Sorghum, Barley, and Oats Supply and Use")
    if boundary>=0:
        table=table[:boundary]
    if not re.search(r"2026/27\s+Proj\..*2026/27\s+Proj\.",table[:650]):
        raise ValueError("WRONG_MARKETING_YEAR")
    col=re.search(r"(?m)^\s*Item\s+"+re.escape(previous_month)+r"\s+"+re.escape(current_month)+r"\s*$",table[:650])
    if not col:
        raise ValueError("WRONG_WASDE_MONTHLY_COLUMNS")
    anchors=list(re.finditer(r"(?m)^\s*CORN\s*$",table))
    if len(anchors)!=1:
        raise ValueError("CORN_SUBSECTION_NOT_UNIQUE")
    corn=table[anchors[0].end():]
    if "Million Bushels" not in corn[:550]:
        raise ValueError("CORN_VOLUME_UNITS_NOT_MILLION_BUSHELS")
    rows=re.findall(r"(?m)^\s*Ending Stocks\s+(\d[\d,]*)\s+(\d[\d,]*)\s+(\d[\d,]*)\s+(\d[\d,]*)\s*$",corn)
    if len(rows)!=1:
        raise ValueError("CORN_ENDING_STOCK_ROW_NOT_UNIQUE")
    values=[int(n.replace(",","")) for n in rows[0]]
    if any(v<0 or v>100000 for v in values):
        raise ValueError("CORN_ENDING_STOCK_OUT_OF_RANGE")
    return {"crop":"US_CORN","marketing_year":"2026/27",
            "unit":"million_bushels","report_month":report_month,
            "previous_report_month":previous_month,
            "current_report_month":current_month,
            "previous_month_ending_stock_mbu":values[2],
            "current_month_ending_stock_mbu":values[3],
            "four_column_values_mbu":values}

def validate_locked():
    from research_core.k4.prospective_scorecard import score, EMPTY_EVIDENCE
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    e=json.loads(EMPTY_EVIDENCE.read_text(encoding="utf-8"))
    # Reuse strict K4.10 byte hash and V0 contract, but do NOT require future consensus.
    result=score(c,e,FROZEN.read_bytes())
    if (result["forecast_v0_mbu"]!="1758" or
        result["trade_eligible"] is not False or
        result["evidence_complete"] is not False):
        raise ValueError("FROZEN_K410_BASELINE_NOT_VERIFIED")
    return c["forecast_raw_sha256"]

def assess(raw, source, forecast_sha=None):
    if not isinstance(source,dict) or set(source)!={
        "requested_url","response_url","fetch_started_utc","fetch_finished_utc"
    }:
        raise ValueError("MISSING_OFFICIAL_SOURCE_CAPTURE")
    source_allowed(source["requested_url"])
    source_allowed(source["response_url"])
    start=timestamp(source["fetch_started_utc"])
    finish=timestamp(source["fetch_finished_utc"])
    if not timestamp(BARRIER)<=start<=finish:
        raise ValueError("DECEMBER_SOURCE_CAPTURE_BEFORE_RELEASE")
    if forecast_sha is None:
        forecast_sha=validate_locked()
    result=parse_wasde_corn(raw)
    if result["previous_month_ending_stock_mbu"]!=FORECAST:
        raise ValueError("NOVEMBER_ORIGINAL_REFERENCE_CHANGED_REQUIRES_REVIEW")
    ending=result["current_month_ending_stock_mbu"]
    return {
      "schema":SCHEMA,
      "status":"OFFICIAL_RAW_V0_SCORED_CONSENSUS_INDEPENDENT",
      "event_id":EVENT,
      "target":"US_CORN_2026_27_ENDING_STOCKS_MBU",
      "unit":"million_bushels",
      "forecast_v0_mbu":FORECAST,
      "forecast_raw_sha256":forecast_sha,
      "official_value_mbu":ending,
      "v0_absolute_error_mbu":abs(ending-FORECAST),
      "market_consensus_mbu":None,
      "consensus_abs_error_mbu":None,
      "official_raw_sha256":hashlib.sha256(raw).hexdigest(),
      "official_raw_bytes":len(raw),
      "source":source,
      "parsed_official_table":result,
      "official_first_publication_utc_independently_attested":False,
      "independent_pit_certified":False,
      "alpha_verified":False,
      "trade_eligible":False
    }

def fetch(url=URL):
    source_allowed(url)
    started=utcnow()
    with urlopen(Request(url,headers={"User-Agent":"SIGNAL-K411-WASDE-Official-Event/1.0"}),
                 timeout=18) as r:
        target=r.geturl()
        source_allowed(target)
        raw=r.read(MAX_BYTES+1)
        return raw,{
            "requested_url":url,"response_url":target,
            "fetch_started_utc":started,"fetch_finished_utc":utcnow()
        }

def capture(output_dir, fetcher=fetch, clock=utcnow):
    if timestamp(clock())<timestamp(BARRIER):
        return {"status":"BLOCKED_DECEMBER_WASDE_NOT_YET_RELEASED",
                "official_raw_sha256":None,"trade_eligible":False}
    try:
        raw, source=fetcher()
        result=assess(raw,source)
        name=f"USDA_WASDE_20261210_{result['official_raw_sha256'][:16]}"
        root=Path(output_dir)
        root.mkdir(parents=True,exist_ok=True)
        files={
            "raw":root/(name+"_official_raw.txt"),
            "receipt":root/(name+"_capture_receipt.json"),
            "score":root/(name+"_v0_score.json")
        }
        if any(p.exists() for p in files.values()):
            raise ValueError("OFFICIAL_WASDE_EVIDENCE_ALREADY_ARCHIVED")
        owned=[]
        try:
            with files["raw"].open("xb") as f:
                owned.append(files["raw"])
                f.write(raw)
            for key,obj in (("receipt",{
                "schema":"signal-k411-wasde-source-receipt-v1",
                "source":source,"source_raw_sha256":result["official_raw_sha256"],
                "source_raw_bytes":len(raw),"raw_file":files["raw"].name,
                "event_id":EVENT,"trade_eligible":False}),("score",result)):
                with files[key].open("x",encoding="utf-8") as f:
                    owned.append(files[key])
                    json.dump(obj,f,ensure_ascii=False,indent=2)
                    f.write("\n")
        except BaseException:
            for p in reversed(owned):
                p.unlink(missing_ok=True)
            raise
        return {"status":result["status"],"raw_file":files["raw"].name,
                "receipt_file":files["receipt"].name,
                "score_file":files["score"].name,
                "official_value_mbu":result["official_value_mbu"],
                "v0_absolute_error_mbu":result["v0_absolute_error_mbu"],
                "official_raw_sha256":result["official_raw_sha256"],
                "trade_eligible":False}
    except (ValueError,HTTPError,URLError,OSError,TimeoutError,UnicodeError) as exc:
        return {"status":"BLOCKED_OFFICIAL_WASDE_NOT_VALIDATED",
                "error_type":type(exc).__name__,
                "reason":str(exc)[:130] if isinstance(exc,ValueError) else None,
                "official_raw_sha256":None,"trade_eligible":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    r=capture(args.output_dir)
    print(json.dumps(r,ensure_ascii=False))
    if not r["status"].startswith("OFFICIAL_"):
        raise SystemExit(2)
if __name__=="__main__":
    main()
