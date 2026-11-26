"""Fail-closed, offline EIA forward-event scorer (K5), never a trading gate.

Original Git blob ID protects frozen forecast. Raw EIA bytes + a recorded
capture receipt are mandatory for scoring. Timestamps are receipt claims:
this code does NOT independently certify first-public availability or PIT.
"""
from __future__ import annotations
from datetime import datetime
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DEC03 = ROOT / "cases" / "2026-12-03-eia-frozen-v0-forecast.json"
DEC03_BLOB = "7e78fe165b75dc13662d87b8f53b3172d712fe51"
TARGET_ID = "png.nw2_epg0_swo_r48_bcf.w"
MAX_BYTES = 150_000


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def utc(raw: str) -> datetime:
    if not isinstance(raw, str) or not raw.endswith("Z"):
        raise ValueError("UTC_TIMESTAMP_REQUIRED")
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("UTC_TIMESTAMP_REQUIRED") from exc
    if ts.utcoffset() is None or ts.utcoffset().total_seconds() != 0:
        raise ValueError("UTC_TIMESTAMP_REQUIRED")
    return ts


def frozen_checked(raw: bytes, expected_blob: str) -> dict:
    if not isinstance(raw, bytes) or blob_sha(raw) != expected_blob:
        raise ValueError("FROZEN_FORECAST_BYTES_CHANGED")
    f = json.loads(raw.decode("utf-8"))
    if (f.get("schema") != "signal-k5-ng-weekly-pre-registered-forecast-v1"
        or f.get("event_id") != "EIA-WNGSR-2026-12-03"
        or f.get("release_scheduled_utc") != "2026-12-03T15:30:00Z"
        or f.get("target_week_end") != "2026-11-27"
        or f.get("baseline_observation_week_end") != "2026-11-20"
        or f.get("target") != "US_LOWER48_WORKING_GAS_WEEKLY_NET_CHANGE"
        or f.get("unit") != "Bcf"
        or f.get("method_id") != "PREVIOUS_RELEASE_WEEKLY_NET_CHANGE_UNCHANGED"
        or type(f.get("forecast_net_change_bcf")) is not int
        or f["forecast_net_change_bcf"] != -24
        or f.get("baseline_net_change_bcf") != -24
        or f.get("baseline_storage_asof_2026_11_20_bcf") != 3858
        or f.get("market_consensus_bcf") is not None
        or f.get("actual_next_release_net_change_bcf") is not None
        or f.get("trade_eligible") is not False):
        raise ValueError("FROZEN_FORECAST_CONTRACT_CHANGED")
    if not utc(f["baseline_source_release_utc"]) <= utc(f["forecast_inputs_cutoff_utc"]) <= utc(f["forecast_created_utc"]) < utc(f["release_scheduled_utc"]):
        raise ValueError("FORECAST_CHRONOLOGY_INVALID")
    return f


def official_checked(raw: bytes, f: dict) -> dict:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("EIA_RAW_BYTES_INVALID")
    o = json.loads(raw.decode("utf-8-sig", errors="strict"))
    if (not isinstance(o, dict) or o.get("release_name") != "Weekly Natural Gas Storage Report"
        or not str(o.get("release_date", "")).startswith("2026-Dec-03 ")
        or o.get("current_week") != f["target_week_end"]
        or o.get("week_ago") != f["baseline_observation_week_end"]
        or o.get("fuel_type") != "natural gas" or o.get("process") != "storage"
        or o.get("periodicity") != "weekly"):
        raise ValueError("WRONG_EIA_RELEASE_OR_REPORTING_WEEK")
    rows = o.get("series")
    if not isinstance(rows, list):
        raise ValueError("EIA_SERIES_MISSING")
    matches = [s for s in rows if isinstance(s, dict) and s.get("series_id") == TARGET_ID]
    if len(matches) != 1:
        raise ValueError("EIA_LOWER48_SERIES_MISSING_OR_DUPLICATED")
    series = matches[0]
    if (series.get("name") != "total lower 48 states" or series.get("unitsshort") != "bcf"
        or series.get("source") != "U.S. Energy Information Administration"):
        raise ValueError("EIA_SERIES_IDENTITY_MISMATCH")
    data = series.get("data")
    if (not isinstance(data, list) or len(data) < 2
        or not all(isinstance(row, list) and len(row) == 2 for row in data[:2])
        or data[0][0] != f["target_week_end"]
        or data[1][0] != f["baseline_observation_week_end"]
        or type(data[0][1]) is not int or type(data[1][1]) is not int
        or not 0 < data[0][1] < 10000 or not 0 < data[1][1] < 10000):
        raise ValueError("EIA_STOCK_LEVELS_INVALID")
    calculated = series.get("calculated")
    if not isinstance(calculated, dict) or type(calculated.get("net_change")) is not int:
        raise ValueError("EIA_NET_CHANGE_MISSING")
    change = calculated["net_change"]
    if not -1000 <= change <= 1000 or abs(change - (data[0][1] - data[1][1])) > 1:
        raise ValueError("EIA_STOCK_CHANGE_RECONCILIATION_FAILED")
    return {"official_net_change_bcf":change,
            "official_stock_bcf":data[0][1],
            "official_prior_stock_bcf":data[1][1],
            "prior_stock_revision_vs_published_baseline_bcf":data[1][1] - f["baseline_storage_asof_2026_11_20_bcf"]}


def capture_checked(receipt: dict, raw: bytes, release: str) -> str:
    if not isinstance(receipt, dict) or set(receipt) != {
        "source_url", "response_url", "capture_started_utc", "capture_finished_utc",
        "source_raw_sha256", "source_raw_bytes", "first_published_pit_authenticated",
        "trade_eligible"}:
        raise ValueError("CAPTURE_RECEIPT_CONTRACT_INVALID")
    if (receipt["source_url"] != "https://ir.eia.gov/ngs/wngsr.json"
        or receipt["trade_eligible"] is not False
        or receipt["first_published_pit_authenticated"] is not False):
        raise ValueError("UNVERIFIED_CAPTURE_SOURCE_OR_PROMOTED_PIT")
    url = urlsplit(receipt["response_url"])
    if (url.scheme != "https" or url.hostname != "ir.eia.gov"
        or url.path not in ("/ngs/wngsr.json", "/secure/ngs/wngsr.json")
        or url.username is not None or url.password is not None or url.fragment):
        raise ValueError("NON_OFFICIAL_EIA_CAPTURE")
    if (receipt["source_raw_sha256"] != hashlib.sha256(raw).hexdigest()
        or receipt["source_raw_bytes"] != len(raw)):
        raise ValueError("CAPTURE_RAW_SHA_MISMATCH")
    started, finished = utc(receipt["capture_started_utc"]), utc(receipt["capture_finished_utc"])
    if not utc(release) <= started <= finished:
        raise ValueError("CAPTURE_CHRONOLOGY_INVALID")
    return receipt["capture_finished_utc"]


def evaluate(frozen_bytes: bytes, *, event_raw: bytes | None = None,
             receipt: dict | None = None, expected_blob: str = DEC03_BLOB) -> dict:
    f = frozen_checked(frozen_bytes, expected_blob)
    base = {"schema":"signal-k5-forward-event-score-v1", "event_id": f["event_id"],
            "forecast_git_blob_sha1":expected_blob,
            "forecast_net_change_bcf":f["forecast_net_change_bcf"],
            "actual_net_change_bcf":None, "absolute_error_bcf":None,
            "raw_source_sha256":None, "source_capture_utc":None,
            "market_consensus_bcf":None, "market_consensus_pit_verified":False,
            "independent_first_public_pit_verified":False, "trade_eligible":False}
    if event_raw is None and receipt is None:
        return {**base, "status":"WAITING_FOR_EIA_ORIGINAL_RAW_BYTES"}
    if not isinstance(event_raw, bytes) or not isinstance(receipt, dict):
        raise ValueError("EIA_RAW_AND_RECEIPT_REQUIRED_TOGETHER")
    observed = official_checked(event_raw, f)
    finished = capture_checked(receipt, event_raw, f["release_scheduled_utc"])
    return {**base, **observed,
            "status":"POST_EVENT_DESCRIPTIVE_SCORE_ONLY",
            "actual_net_change_bcf": observed["official_net_change_bcf"],
            "absolute_error_bcf":abs(observed["official_net_change_bcf"]-f["forecast_net_change_bcf"]),
            "raw_source_sha256":hashlib.sha256(event_raw).hexdigest(),
            "source_capture_utc":finished}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen",type=Path,default=DEC03)
    parser.add_argument("--raw",type=Path)
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if (args.raw is None) != (args.receipt is None):
        parser.error("--raw and --receipt are required together")
    result=evaluate(args.frozen.read_bytes(),
                    event_raw=args.raw.read_bytes() if args.raw else None,
                    receipt=json.loads(args.receipt.read_text()) if args.receipt else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"trade_eligible":False}))

if __name__ == "__main__":
    main()
