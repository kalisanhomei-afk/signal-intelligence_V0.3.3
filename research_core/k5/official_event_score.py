"""K5.2 fixed pre-registered evaluation from actual future EIA original bytes.

No target value is known before Nov 19. Do not accept a manually typed outcome
with a decorative SHA: reparse exact EIA JSON, hash bytes and compare to a frozen
original forecast Git blob before scoring. Never grants trading eligibility.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from research_core.k5.ng_baseline import parse_utc

ROOT=Path(__file__).resolve().parent
FROZEN=ROOT/"cases"/"2026-11-19-eia-frozen-v0-forecast.json"
FIRST=ROOT/"evidence"/"eia"/"EIA_WNGSR_20261113_6eb6c699b789d713_original.json"
PRIOR_RECEIPT=ROOT/"evidence"/"eia"/"EIA_WNGSR_20261113_6eb6c699b789d713_receipt.json"
FROZEN_BLOB_SHA="bacc82f549fb3bba74142139d89bec94e386d88e"
TARGET_ID="png.nw2_epg0_swo_r48_bcf.w"
WEEK="2026-11-13"
PRIOR_WEEK="2026-11-06"
EVENT="EIA-WNGSR-2026-11-19"
RELEASE="2026-11-19T15:30:00Z"
MAX_BYTES=150_000

def git_blob_sha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\x00"+data).hexdigest()

def frozen_checked(blob):
    if git_blob_sha(blob)!=FROZEN_BLOB_SHA:
        raise ValueError("PRE_RELEASE_FORECAST_BYTES_CHANGED")
    f=json.loads(blob.decode("utf-8"))
    if (f.get("event_id")!=EVENT or f.get("target_week_end")!=WEEK or
        f.get("release_scheduled_utc")!=RELEASE or
        f.get("forecast_net_change_bcf")!=61 or
        f.get("method_id")!="PREVIOUS_RELEASE_WEEKLY_NET_CHANGE_UNCHANGED" or
        f.get("market_consensus_bcf") is not None or
        f.get("actual_next_release_net_change_bcf") is not None or
        f.get("trade_eligible") is not False):
        raise ValueError("PRE_RELEASE_FORECAST_CONTRACT_CHANGED")
    return f

def prior_checked(raw, receipt):
    p=json.loads(receipt.decode("utf-8"))
    if (p.get("source_raw_sha256")!=hashlib.sha256(raw).hexdigest() or
        p.get("source_raw_bytes")!=len(raw) or
        p.get("source_report",{}).get("week_end")!=PRIOR_WEEK or
        p.get("source_report",{}).get("storage_bcf")!=3862 or
        p.get("source_report",{}).get("net_change_bcf")!=61 or
        p.get("trade_eligible") is not False):
        raise ValueError("PRIOR_OFFICIAL_SOURCE_TAMPERED")
    return p

def official_parsed(raw):
    if not isinstance(raw,bytes) or not (0<len(raw)<=MAX_BYTES):
        raise ValueError("INVALID_EIA_RAW_BYTES")
    o=json.loads(raw.decode("utf-8-sig",errors="strict"))
    if not isinstance(o,dict) or o.get("release_name")!="Weekly Natural Gas Storage Report":
        raise ValueError("WRONG_EIA_REPORT_ID")
    if (not str(o.get("release_date","")).startswith("2026-Nov-19 ")
        or o.get("current_week")!=WEEK or o.get("week_ago")!=PRIOR_WEEK
        or o.get("fuel_type")!="natural gas"
        or o.get("process")!="storage" or o.get("periodicity")!="weekly"):
        raise ValueError("WRONG_EIA_EVENT_WEEK")
    s=o.get("series",[])
    rows=[x for x in s if isinstance(x,dict) and x.get("series_id")==TARGET_ID]
    if len(rows)!=1:
        raise ValueError("MISSING_OR_AMBIGUOUS_LOWER48")
    r=rows[0]
    if (r.get("name")!="total lower 48 states" or r.get("unitsshort")!="bcf"
        or r.get("source")!="U.S. Energy Information Administration"):
        raise ValueError("WRONG_SERIES_UNITS_OR_SOURCE")
    v=r.get("data")
    if (not isinstance(v,list) or len(v)<2 or
        not isinstance(v[0],list) or not isinstance(v[1],list) or
        len(v[0])!=2 or len(v[1])!=2 or
        v[0][0]!=WEEK or v[1][0]!=PRIOR_WEEK or
        type(v[0][1]) is not int or type(v[1][1]) is not int or
        not 0<v[0][1]<10000 or not 0<v[1][1]<10000):
        raise ValueError("WRONG_STORAGE_LEVEL_OR_WEEK")
    current,previous=v[0][1],v[1][1]
    c=r.get("calculated")
    if not isinstance(c,dict) or type(c.get("net_change")) is not int:
        raise ValueError("MISSING_OFFICIAL_WEEKLY_NET_CHANGE")
    change=c["net_change"]
    if not -1000<=change<=1000 or abs(change-(current-previous))>1:
        raise ValueError("OFFICIAL_CHANGE_LEVEL_RECONCILIATION")
    return {"release_date_claim":"2026-11-19",
            "target_week_end":WEEK,
            "region":"Lower 48 states","unit":"Bcf",
            "official_stock_current_bcf":current,
            "official_previous_week_stock_bcf":previous,
            "official_net_change_bcf":change,
            "storage_level_delta_bcf":current-previous,
            "prior_official_week_stock_revision_bcf":previous-3862,
            "prior_source_vintage_revised":previous!=3862}

def evaluate(frozen_bytes,prior_raw,prior_receipt,raw=None,capture=None):
    f=frozen_checked(frozen_bytes)
    p=prior_checked(prior_raw,prior_receipt)
    base={"schema":"signal-k52-natural-gas-event-raw-evaluation-v1",
          "event_id":EVENT,"target_week_end":WEEK,
          "frozen_v0_net_change_bcf":f["forecast_net_change_bcf"],
          "frozen_v0_git_blob_sha":FROZEN_BLOB_SHA,
          "prior_original_sha256":p["source_raw_sha256"],
          "raw_official_release_sha256":None,
          "actual_net_change_bcf":None,
          "v0_absolute_error_bcf":None,
          "revised_prior_week_bcf":None,
          "independent_pit_first_publication_verified":False,
          "consensus_vintage_verified":False,
          "alpha_or_trade_verified":False,
          "trade_eligible":False}
    if raw is None and capture is None:
        return {**base,"status":"WAITING_FOR_NOV19_OFFICIAL_EIA_ORIGINAL"}
    if not isinstance(raw,bytes) or not isinstance(capture,dict) or set(capture)!={"requested_url","response_host","response_path","capture_started_utc","capture_finished_utc"}:
        raise ValueError("EIA_SOURCE_AND_CAPTURE_REQUIRED")
    if (capture["requested_url"]!="https://ir.eia.gov/ngs/wngsr.json" or
        capture["response_host"]!="ir.eia.gov" or
        capture["response_path"] not in ("/ngs/wngsr.json","/secure/ngs/wngsr.json")):
        raise ValueError("NOT_OFFICIAL_EIA_DATA_URL")
    start=parse_utc(capture["capture_started_utc"])
    finished=parse_utc(capture["capture_finished_utc"])
    if not parse_utc(RELEASE)<=start<=finished:
        raise ValueError("RESULT_CAPTURE_BEFORE_EIA_SCHEDULE")
    outcome=official_parsed(raw)
    return {**base,"status":"ONE_EVENT_OFFICIAL_RAW_DESCRIPTIVE_SCORE_ONLY",
            "source_capture_utc":capture["capture_finished_utc"],
            "raw_official_release_sha256":hashlib.sha256(raw).hexdigest(),
            "actual_net_change_bcf":outcome["official_net_change_bcf"],
            "v0_absolute_error_bcf":abs(outcome["official_net_change_bcf"]-61),
            "revised_prior_week_bcf":outcome["prior_official_week_stock_revision_bcf"],
            "official_data_checks":outcome}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    # No post-event outcome args by default; code cannot hallucinate it.
    args=p.parse_args()
    result=evaluate(FROZEN.read_bytes(), FIRST.read_bytes(), PRIOR_RECEIPT.read_bytes())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"actual":result["actual_net_change_bcf"],
                      "trade_eligible":False}))
if __name__=="__main__":main()
