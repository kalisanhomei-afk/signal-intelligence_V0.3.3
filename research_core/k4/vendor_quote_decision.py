"""Classify a K4 Databento metadata-only quote; never acquire market data."""
from __future__ import annotations
import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

EXPECTED_SCHEMAS = ("ohlcv-1m", "trades", "tbbo")
EXPECTED_START = "2026-11-10T16:30:00Z"
EXPECTED_END = "2026-11-10T19:30:00Z"

class QuoteReviewError(ValueError):
    pass

def decision(quote):
    if not isinstance(quote, dict) or quote.get("schema") != "signal-k4-vendor-metadata-quote-only-v1":
        raise QuoteReviewError("INVALID_QUOTE_SCHEMA")
    fixed = {"vendor": "Databento", "dataset": "GLBX.MDP3", "raw_symbol": "ZCZ6",
             "request_scope": "ONE_CONTRACT_ONE_EVENT_THREE_SCHEMAS_NO_PURCHASE",
             "status": "VENDOR_METADATA_QUOTED_NO_HISTORY_PURCHASED"}
    if any(quote.get(k) != v for k,v in fixed.items()):
        raise QuoteReviewError("QUOTE_SCOPE_MISMATCH")
    if not isinstance(quote.get("instrument_id"), str) or not quote["instrument_id"].isdigit():
        raise QuoteReviewError("UNVERIFIED_INSTRUMENT_ID")
    try:
        observed=datetime.fromisoformat(quote["quoted_at_utc"].replace("Z","+00:00"))
        if not quote["quoted_at_utc"].endswith("Z") or observed.utcoffset().total_seconds() != 0:
            raise ValueError()
    except (TypeError, KeyError, ValueError, AttributeError) as exc:
        raise QuoteReviewError("INVALID_QUOTE_UTC") from exc
    if (quote.get("data_download_requests") != 0 or quote.get("trading_orders") != 0 or
        quote.get("actual_history_downloaded") is not False or
        quote.get("license_to_redistribute_verified") is not False or
        quote.get("market_data_asof_authenticated") is not False):
        raise QuoteReviewError("QUOTE_NOT_METADATA_ONLY")
    rows=quote.get("quote_rows")
    if not isinstance(rows,list) or len(rows)!=3 or [r.get("schema") for r in rows if isinstance(r,dict)]!=list(EXPECTED_SCHEMAS):
        raise QuoteReviewError("SCHEMA_LIST_MISMATCH")
    catalog=[]
    for row in rows:
        expected={"dataset":"GLBX.MDP3","raw_symbol":"ZCZ6","start_utc":EXPECTED_START,"end_utc":EXPECTED_END}
        if any(row.get(k)!=v for k,v in expected.items()):
            raise QuoteReviewError("ROW_SCOPE_MISMATCH")
        count=row.get("record_count_metadata_only")
        if isinstance(count,bool) or not isinstance(count,int) or count<0:
            raise QuoteReviewError("INVALID_RECORD_COUNT")
        try:
            cost=Decimal(str(row["vendor_quoted_usd"]))
        except (KeyError,InvalidOperation,ValueError) as exc:
            raise QuoteReviewError("INVALID_COST") from exc
        if isinstance(row["vendor_quoted_usd"],bool) or not cost.is_finite() or cost<0:
            raise QuoteReviewError("INVALID_COST")
        catalog.append({"schema":row["schema"],"quoted_usd":str(cost),"record_count_metadata_only":count})
    available={x["schema"]:x["record_count_metadata_only"]>0 for x in catalog}
    stage = ("NO_ONE_MINUTE_DATA_STOP" if not available["ohlcv-1m"] else
             "ONLY_MINUTE_BARS_NOT_EXECUTABLE" if not (available["trades"] and available["tbbo"]) else
             "QUOTED_PENDING_LICENSE_AND_OWNER_APPROVAL")
    return {
        "schema":"signal-k4-quote-review-v1",
        "symbol":"ZCZ6", "instrument_id":quote["instrument_id"],
        "decision":stage,"schema_quotes":catalog,
        "minute_bar_data_possible":available["ohlcv-1m"],
        "trades_and_tbbo_metadata_nonzero":available["trades"] and available["tbbo"],
        "metadata_can_overestimate_records":True,
        "total_estimated_usd_all_schemas":str(sum(Decimal(x["quoted_usd"]) for x in catalog)),
        "verified_market_data_rows_acquired":0,
        "owner_purchase_approval_given":False,
        "licensed_data_access_verified":False,
        "event_study_eligible":False,
        "tradable":False,
        "next_step":"Review vendor license and cost; obtain separate owner authorization before any data request.",
    }

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--quote",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args(argv)
    result=decision(json.loads(args.quote.read_text(encoding="utf-8")))
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"k4_quote_decision.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"decision":result["decision"],"tradable":False,"data_downloaded":False}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
