"""One-shot Dec-03 EIA WNGSR acquisition, fail-closed and non-trading.

Requires EIA's actual post-release raw JSON and HTTPS response chronology.
Do not run before the scheduled publication. All writes are exclusive; the
previous Nov-19 capture and both frozen forecast blobs remain untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

from research_core.k5.eia_postrelease_capture import fetch as official_fetch
from research_core.k5.forward_event_score import (
    DEC03, DEC03_BLOB, MAX_BYTES, capture_checked, evaluate,
    frozen_checked, official_checked, utc,
)

SOURCE = "https://ir.eia.gov/ngs/wngsr.json"
RELEASE = "2026-12-03T15:30:00Z"
EVENT_STEM = "EIA_WNGSR_20261203_"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def capture(output_dir, fetcher=official_fetch, clock=now):
    """Return an explicit status. Never infer first-public PIT or market alpha."""
    if utc(clock()) < utc(RELEASE):
        return {"status": "BLOCKED_RELEASE_NOT_YET_DUE", "source_raw_sha256": None,
                "trade_eligible": False}
    try:
        frozen = DEC03.read_bytes()
        f = frozen_checked(frozen, DEC03_BLOB)
        raw, src = fetcher()
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
            raise ValueError("EIA_RAW_BYTES_INVALID")
        if not isinstance(src, dict) or set(src) != {
            "requested_url", "response_host", "response_path",
            "capture_started_utc", "capture_finished_utc"}:
            raise ValueError("EIA_FETCH_RECEIPT_INVALID")
        if (src["requested_url"] != SOURCE
            or src["response_host"] != "ir.eia.gov"
            or src["response_path"] not in ("/ngs/wngsr.json", "/secure/ngs/wngsr.json")):
            raise ValueError("EIA_FETCH_SOURCE_INVALID")
        receipt = {
            "source_url": SOURCE,
            "response_url": "https://" + src["response_host"] + src["response_path"],
            "capture_started_utc": src["capture_started_utc"],
            "capture_finished_utc": src["capture_finished_utc"],
            "source_raw_sha256": hashlib.sha256(raw).hexdigest(),
            "source_raw_bytes": len(raw),
            "first_published_pit_authenticated": False,
            "trade_eligible": False,
        }
        # Reparse source bytes and independently enforce source, date and time.
        official_checked(raw, f)
        capture_checked(receipt, raw, RELEASE)
        score = evaluate(frozen, event_raw=raw, receipt=receipt)
        stem = EVENT_STEM + receipt["source_raw_sha256"][:16]
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths = {
            "raw": root / (stem + "_original.json"),
            "receipt": root / (stem + "_receipt.json"),
            "score": root / (stem + "_score.json"),
        }
        if any(path.exists() for path in paths.values()):
            raise ValueError("EVIDENCE_COLLISION_NO_OVERWRITE")
        owned = []
        try:
            with paths["raw"].open("xb") as dest:
                owned.append(paths["raw"])
                dest.write(raw)
            for key, payload in (("receipt", receipt), ("score", score)):
                with paths[key].open("x", encoding="utf-8") as dest:
                    owned.append(paths[key])
                    json.dump(payload, dest, ensure_ascii=False, indent=2)
                    dest.write("\n")
        except BaseException:
            for path in reversed(owned):
                path.unlink(missing_ok=True)
            raise
        return {"status": "OFFICIAL_RAW_AND_SCORE_CAPTURED",
                "source_raw_sha256": receipt["source_raw_sha256"],
                "source_capture_utc": receipt["capture_finished_utc"],
                "raw_file": paths["raw"].name, "receipt_file": paths["receipt"].name,
                "score_file": paths["score"].name, "actual_net_change_bcf":
                    score["actual_net_change_bcf"],
                "absolute_error_bcf": score["absolute_error_bcf"],
                "trade_eligible": False}
    except (ValueError, KeyError, TypeError, OSError, HTTPError, URLError,
            TimeoutError, UnicodeError) as exc:
        return {"status": "BLOCKED_EIA_RESULT_NOT_VALIDATED",
                "error_type": type(exc).__name__,
                "reason": str(exc)[:120] if isinstance(exc, ValueError) else None,
                "source_raw_sha256": None, "trade_eligible": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = capture(args.output_dir)
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "OFFICIAL_RAW_AND_SCORE_CAPTURED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
