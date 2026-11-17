"""SIGNAL K4: fixed-scope, metadata-ONLY Databento historical cost preflight.

Uses vendor's free symbology and metadata endpoints. NO timeseries.get_range,
NO batch job, NO data purchase, NO automatic subscription, NO trading.
An already-authorized Databento account API key is necessary, supplied by
DATABENTO_API_KEY in the execution environment; never saved in a file or logs.

Run from repository root after a separate account/access review:
  python -m research_core.k4.vendor_quote_only --output local-private-k4-quote
"""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path

DATASET = "GLBX.MDP3"
SYMBOL = "ZCZ6"
START = "2026-11-10T16:30:00Z"
END = "2026-11-10T19:30:00Z"
SCHEMAS = ("ohlcv-1m", "trades", "tbbo")


class QuoteGateError(ValueError):
    pass


def validated_usd(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise QuoteGateError("INVALID_VENDOR_COST_TYPE")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise QuoteGateError("INVALID_VENDOR_COST") from exc
    if not amount.is_finite() or amount < 0:
        raise QuoteGateError("INVALID_VENDOR_COST")
    return str(amount)


def metadata_only_preflight(client, *, clock=None):
    """Accept an injected historical metadata client for independent offline tests."""
    r = client.symbology.resolve(
        dataset=DATASET,
        symbols=[SYMBOL],
        stype_in="raw_symbol",
        stype_out="instrument_id",
        start_date="2026-11-10",
        end_date="2026-11-11",
    )
    if not isinstance(r, dict) or SYMBOL in r.get("not_found", []) or not r.get("result", {}).get(SYMBOL):
        raise QuoteGateError("TARGET_FUTURES_CONTRACT_NOT_RESOLVED")
    instrument_mappings = r["result"][SYMBOL]
    if not isinstance(instrument_mappings, list) or len(instrument_mappings) != 1:
        raise QuoteGateError("TARGET_FUTURES_CONTRACT_AMBIGUOUS")
    mapping = instrument_mappings[0]
    if not isinstance(mapping, dict) or not str(mapping.get("s", "")).isdigit():
        raise QuoteGateError("TARGET_FUTURES_CONTRACT_INSTRUMENT_ID_UNVERIFIED")

    queries = []
    for schema in SCHEMAS:
        kwargs = dict(dataset=DATASET, symbols=[SYMBOL], schema=schema,
                      stype_in="raw_symbol", start=START, end=END)
        # Metadata queries only. Never invoke timeseries or batch endpoints.
        count = client.metadata.get_record_count(**kwargs)
        cost = client.metadata.get_cost(**kwargs)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise QuoteGateError("INVALID_VENDOR_RECORD_COUNT")
        queries.append({"dataset": DATASET, "raw_symbol": SYMBOL, "schema": schema,
                        "start_utc": START, "end_utc": END,
                        "record_count_metadata_only": count,
                        "vendor_quoted_usd": validated_usd(cost)})
    t = clock or datetime.now(timezone.utc)
    if t.tzinfo is None:
        raise QuoteGateError("TIMESTAMP_OFFSET_REQUIRED")
    return {
        "schema": "signal-k4-vendor-metadata-quote-only-v1",
        "request_scope": "ONE_CONTRACT_ONE_EVENT_THREE_SCHEMAS_NO_PURCHASE",
        "quoted_at_utc": t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "vendor": "Databento", "dataset": DATASET, "raw_symbol": SYMBOL,
        "instrument_id": str(mapping["s"]),
        "quote_rows": queries,
        "data_download_requests": 0, "trading_orders": 0,
        "actual_history_downloaded": False,
        "license_to_redistribute_verified": False,
        "market_data_asof_authenticated": False,
        "status": "VENDOR_METADATA_QUOTED_NO_HISTORY_PURCHASED",
        "next_required_review": "Owner must separately approve actual data acquisition and its access/usage license.",
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args(argv)
    key = os.environ.get("DATABENTO_API_KEY", "")
    if not key or len(key) < 8:
        print(json.dumps({"status": "BLOCKED_NO_DATABENTO_ACCOUNT_API_KEY",
                          "metadata_queried": False, "historical_data_downloaded": False}))
        return 2
    try:
        import databento as db
        result = metadata_only_preflight(db.Historical(key=key))
    except ImportError:
        print(json.dumps({"status": "DEPENDENCY_MISSING", "historical_data_downloaded": False}))
        return 2
    except QuoteGateError as exc:
        print(json.dumps({"status": "QUOTE_FAILED_CLOSED", "reason": str(exc),
                          "historical_data_downloaded": False}))
        return 2
    except Exception as exc:
        # NEVER surface upstream error messages which may leak request headers,
        # account IDs or authentication details in CI logs.
        print(json.dumps({"status": "QUOTE_PROVIDER_UNAVAILABLE",
                          "error_class": type(exc).__name__,
                          "historical_data_downloaded": False}))
        return 2
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "databento_quote_only.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "symbol": result["raw_symbol"],
                      "costs_usd": {x["schema"]: x["vendor_quoted_usd"] for x in result["quote_rows"]},
                      "actual_history_downloaded": False, "trading_orders": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
