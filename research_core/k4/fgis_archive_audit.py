"""K4.9 offline audit of archived FGIS originals and attached capture receipts.

Works for legacy K4.8 evidence and hash-addressed K4.9 versions without
edits for each new week. Never upgrades PIT or trading permissions.
"""
from __future__ import annotations
import argparse
from datetime import timedelta
import hashlib
import json
from pathlib import Path

from research_core.k4.fgis_weekly_vintage import parse_report,timestamp

def audit(folder):
    directory=Path(folder)
    receipts=sorted(directory.glob("WA_GR101_*_capture_receipt.json"))
    if not receipts:
        raise ValueError("NO_CAPTURE_RECEIPTS")
    rows=[]
    seen=set()
    for receipt_path in receipts:
        r=json.loads(receipt_path.read_text(encoding="utf-8"))
        if r.get("status") not in (
            "CAPTURED_PRE_DECEMBER_RELEASE_NOT_INDEPENDENT_PIT_CERTIFIED",
            "CAPTURED_PRE_WASDE_NOT_INDEPENDENT_PIT_CERTIFIED"):
            raise ValueError("UNSUPPORTED_RECEIPT_STATUS")
        digest=r.get("source_raw_sha256")
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("MISSING_VALID_RAW_SHA")
        name=r.get("raw_filename",r.get("source_raw_file"))
        if not isinstance(name,str) or Path(name).name!=name or not name.endswith(".txt"):
            raise ValueError("UNSAFE_RAW_FILENAME")
        raw_path=directory/name
        raw=raw_path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=digest or len(raw)!=r["source_raw_bytes"]:
            raise ValueError("ORIGINAL_RAW_BYTES_MISMATCH")
        info=r["source_report"]
        parsed=parse_report(raw,info["report_date"],info["week_end"])
        # The historical K4.8 receipt predates new 'previous_week_end' field.
        for key in ("report_slug","report_date","week_end","units","corn_week_current_mt",
                    "corn_week_previous_mt","corn_week_year_ago_mt",
                    "corn_marketing_year_to_date_mt","corn_prior_marketing_year_to_date_mt"):
            if parsed[key]!=info.get(key):
                raise ValueError("RAW_VERSUS_RECEIPT_CONTENT_MISMATCH")
        captured=timestamp(r["source"]["fetch_finished_utc"])
        started=timestamp(r["source"]["fetch_started_utc"])
        cutoff=timestamp(r["future_wasde_scheduled_utc"])
        if not started <= captured < cutoff:
            raise ValueError("CAPTURE_AFTER_EVENT_OR_CLOCK_REVERSED")
        if r.get("trade_eligible") is not False:
            raise ValueError("UNAUTHORIZED_TRADE_PROMOTION")
        marker=(info["report_date"],digest)
        if marker in seen:
            raise ValueError("DUPLICATED_ARCHIVED_SOURCE_VERSION")
        seen.add(marker)
        rows.append({"report_date":info["report_date"],"week_end":info["week_end"],
                     "sha256":digest,"bytes":len(raw),
                     "capture_finished_utc":r["source"]["fetch_finished_utc"],
                     "corn_week_mt":info["corn_week_current_mt"],
                     "corn_mtd_mt":info["corn_marketing_year_to_date_mt"],
                     "prior_comparison":r.get("prior_report_comparison",{}),
                     "raw_file":name,"receipt_file":receipt_path.name})
    hashes={r["sha256"] for r in rows}
    for row in rows:
        prior=row["prior_comparison"]
        if prior.get("status") in ("PREVIOUS_WEEK_REVISED","PREVIOUS_WEEK_UNCHANGED"):
            if prior.get("prior_raw_sha256") not in hashes:
                raise ValueError("REFERENCED_PREVIOUS_SOURCE_NOT_ARCHIVED")
            matches=[x for x in rows if x["sha256"]==prior["prior_raw_sha256"]]
            if len(matches)!=1:
                raise ValueError("AMBIGUOUS_PREVIOUS_SOURCE")
            if matches[0]["week_end"]!=str(
                __import__("datetime").date.fromisoformat(row["week_end"])-timedelta(days=7)):
                raise ValueError("REFERENCED_PREVIOUS_WEEK_MISMATCH")
            if matches[0]["capture_finished_utc"] >= row["capture_finished_utc"]:
                raise ValueError("PREVIOUS_CAPTURE_CHRONOLOGY_INVALID")
            delta=row["prior_comparison"]["previous_week_revision_delta_mt"]
            if delta != row["prior_comparison"]["previous_week_now_reported_mt"]-matches[0]["corn_week_mt"]:
                raise ValueError("PREVIOUS_WEEK_DELTA_RECONCILIATION_FAILURE")
    rows.sort(key=lambda x:(x["week_end"],x["capture_finished_utc"]))
    weeks=sorted({x["week_end"] for x in rows})
    return {"schema":"signal-k49-fgis-archived-series-audit-v1",
            "status":"FORWARD_SOURCE_BYTES_AND_RECEIPTS_VERIFIED_NOT_INDEPENDENT_PIT",
            "version_count":len(rows),
            "distinct_weeks":len(weeks),
            "week_ends":weeks,
            "report_date_versions":{date:sum(r["report_date"]==date for r in rows)
                                     for date in sorted({r["report_date"] for r in rows})},
            "observations":rows,
            "first_published_content_independently_attested":False,
            "historic_nine_year_fgis_features_pit_certified":False,
            "model_calibrated":False,
            "predictive_edge_verified":False,
            "trade_eligible":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--evidence-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=audit(args.evidence_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"weeks":result["distinct_weeks"],
                      "versions":result["version_count"],"trade_eligible":False}))

if __name__=="__main__":main()
