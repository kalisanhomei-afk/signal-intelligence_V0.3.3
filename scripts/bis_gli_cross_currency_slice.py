#!/usr/bin/env python3
"""Read only 12 BIS GLI E2.1/E2.2/E2.3 observations from an EXISTING local ZIP.

No network, no historical-vintage certification, no investment model, no external
publish action. Requires the explicitly pinned 2026-11-23 Antigravity receipt hash.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
import zipfile

EXPECTED_ZIP_SHA256 = "87c8b99cca6043ae7737fb9c15159ad5920d0fdf260e9c9a68d03cec7cb95899"
EXPECTED_MEMBER_SHA256 = "1bf5aff7ef3903da56ee0e6400a7390cfdb5dee397857625613233d14eaf7cdc"
MEMBER = "WS_GLI_csv_flat.csv"
MAX_ZIP_BYTES = 5 * 1024 * 1024
MAX_INNER_BYTES = 25 * 1024 * 1024
QUARTERS = ("2026-Q1", "2026-Q2")
CURRENCIES = ("USD", "EUR", "JPY")
DIMENSIONS = (
    "FREQ:Frequency",
    "CURR_DENOM:Currency of denomination",
    "BORROWERS_CTY:Borrowers' country",
    "BORROWERS_SECTOR:Borrowers' sector",
    "LENDERS_SECTOR:Lending sector",
    "L_POS_TYPE:Position type",
    "L_INSTR:Type of instruments",
    "UNIT_MEASURE:Unit of measure",
)
TIME = "TIME_PERIOD:Time period or range"
VALUE = "OBS_VALUE:Observation Value"
UNIT_MULT = "UNIT_MULT:Unit Multiplier"
STATUS = "OBS_STATUS:Observation Status"
NEEDED_COLS = DIMENSIONS + (TIME, VALUE, UNIT_MULT, STATUS)


def series_key(row):
    return ".".join(row[k].split(":", 1)[0].strip() for k in DIMENSIONS)


def parse_signed_decimal(raw, label):
    try:
        x = Decimal(raw)
        if not x.is_finite():
            raise ValueError(label + " is not finite")
        return x
    except (InvalidOperation, TypeError):
        raise ValueError(label + " is not a finite decimal") from None


def inspect_archive_bytes(archive: bytes, *, expected_hash: str = EXPECTED_ZIP_SHA256):
    """Return 12 vetted cells; a verified *current* snapshot, never historical PIT."""
    if not archive or len(archive) > MAX_ZIP_BYTES:
        raise ValueError("Invalid ZIP byte count")
    if hashlib.sha256(archive).hexdigest() != expected_hash:
        raise ValueError("ZIP hash mismatch; refuse new/revised historical dataset")
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        infos = z.infolist()
        if len(infos) != 1 or infos[0].filename != MEMBER or infos[0].file_size > MAX_INNER_BYTES:
            raise ValueError("Unexpected BIS bulk ZIP structure")
        if infos[0].flag_bits & 1:
            raise ValueError("Encrypted ZIP member not permitted")
        raw = z.read(MEMBER)
    if hashlib.sha256(raw).hexdigest() != EXPECTED_MEMBER_SHA256:
        raise ValueError("CSV member hash mismatch")
    rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    if not rows.fieldnames or not set(NEEDED_COLS).issubset(rows.fieldnames):
        raise ValueError("Missing required BIS SDMX columns")
    selected = {}
    for row in rows:
        if row[TIME] not in QUARTERS:
            continue
        key = series_key(row)
        parts = key.split(".")
        if len(parts) != 8:
            continue
        freq, curr, borrowers_cty, borrowers_sector, lender, position, instr, unit = parts
        if (freq, borrowers_cty, borrowers_sector, lender, position, instr) != ("Q", "3P", "N", "A", "I", "B"):
            continue
        if curr not in CURRENCIES or unit not in (curr, "771"):
            continue
        expected_multiplier = "0" if unit == "771" else "6"
        actual_multiplier = row[UNIT_MULT].split(":", 1)[0].strip()
        if actual_multiplier != expected_multiplier:
            raise ValueError(f"Unexpected unit multiplier: {key}: {row[UNIT_MULT]}")
        if row[STATUS].split(":", 1)[0].strip() != "A":
            raise ValueError(f"Non-normal observation status: {key}, {row[TIME]}")
        d = parse_signed_decimal(row[VALUE].strip(), f"{key}/{row[TIME]}")
        k = (curr, row[TIME], "yoy_percent" if unit == "771" else "stock_millions_local_currency")
        if k in selected:
            raise ValueError(f"Duplicate observation: {key}, {row[TIME]}")
        selected[k] = str(d)
    if len(selected) != len(CURRENCIES) * len(QUARTERS) * 2:
        missing = [f"{c}/{q}/{metric}" for c in CURRENCIES for q in QUARTERS
                   for metric in ("yoy_percent", "stock_millions_local_currency") if (c, q, metric) not in selected]
        raise ValueError("Missing expected BIS observations: " + ", ".join(missing))

    result = {}
    for curr in CURRENCIES:
        q1, q2 = QUARTERS
        y1 = Decimal(selected[(curr, q1, "yoy_percent")])
        y2 = Decimal(selected[(curr, q2, "yoy_percent")])
        result[curr] = {
            "geographical_scope": {"USD": "outside United States", "EUR": "outside euro area", "JPY": "outside Japan"}[curr],
            "q1_2026_outstanding_millions_local_currency": selected[(curr, q1, "stock_millions_local_currency")],
            "q2_2026_outstanding_millions_local_currency": selected[(curr, q2, "stock_millions_local_currency")],
            "q1_2026_bis_adjusted_yoy_percent": str(y1),
            "q2_2026_bis_adjusted_yoy_percent": str(y2),
            "q2_minus_q1_yoy_percentage_points": str(y2 - y1),
            "key_growth_series": f"Q.{curr}.3P.N.A.I.B.771",
        }
    return {
        "classification": "LATEST_REVISED_SNAPSHOT_EXPLORATION",
        "source": "BIS WS_GLI(1.0) E2.1/E2.2/E2.3",
        "source_zip_sha256": expected_hash,
        "quarters": list(QUARTERS),
        "selected_cells": len(selected),
        "currency_comparison": result,
        "interpretation_limits": [
            "Growth rates are BIS FX/break-adjusted; stock amounts in unlike currencies must not be added",
            "Borrowers are outside each currency area, so populations differ",
            "Not contemporaneous PIT evidence, not flow-of-funds evidence, not equity alpha",
        ],
        "historical_pit_verified": False,
        "accepted_for_model": False,
        "gate0": "BLOCKED",
    }


def inspect_local_file(path: Path):
    if not path.is_file() or path.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError("Existing local ZIP required; no network fallback")
    return inspect_archive_bytes(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path, help="existing Antigravity research_raw/ ZIP; never download")
    args = parser.parse_args()
    try:
        result = inspect_local_file(args.zip_path)
    except (ValueError, zipfile.BadZipFile, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
