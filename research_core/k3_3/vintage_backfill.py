#!/usr/bin/env python3
"""SIGNAL K3.3: deterministic multi-release USDA WASDE corn-vintage collection.

Research-only data intake. No forecast, no trading, no claim of lookahead-free model.
Uses an explicit USDA.gov URL manifest verified against the official archive listing.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BASE = "https://www.usda.gov/sites/default/files/documents/"
TITLE = "u.s. feed grain and corn supply and use"
URL_PATH = re.compile(r"^/sites/default/files/documents/oce-wasde-report-data-(20\d{2})-(0[1-9]|1[0-2])\.csv$")
REQUIRED = {"ReleaseDate", "ReportTitle", "Commodity", "Region", "MarketYear", "Attribute", "Value", "Unit", "ProjEstFlag"}
FIELDS = ["release_at", "marketing_year", "metric", "value", "unit", "source_url", "verification"]
MAX_DOWNLOAD = 35 * 1024 * 1024
LATEST_CURATED = "2026-11"  # dated manifest; not an auto-updated archive crawler

# Source fallback is a USDA-owned mirror only. The actual download URL is recorded in the audit.
MIRROR_HOST = "usda.azureedge.us"


def clean(s: str) -> str:
    return " ".join((s or "").strip().lower().replace("’", "'").split())


def validate_url(url: str, expected_month: str) -> None:
    u = urlsplit(url)
    if u.scheme != "https" or u.netloc not in ("www.usda.gov", "usda.azureedge.us") or u.query or u.fragment or u.username or u.password:
        raise ValueError(f"Not an approved USDA URL: {url}")
    m = URL_PATH.fullmatch(u.path)
    if not m or f"{m.group(1)}-{m.group(2)}" != expected_month:
        raise ValueError(f"USDA URL does not match expected {expected_month}: {url}")


def manifest(start: str, end: str) -> list[tuple[str, str]]:
    # USDA Archive page at https://www.usda.gov/historical-wasde-report-data-3
    # Explicit missing month: 2025-10 is not listed on the USDA archive page (as of 2026-11-11).
    months = []
    for year in (2023, 2024, 2025, 2026):
        for month in range(1, 13):
            ym = f"{year}-{month:02d}"
            if ym < start or ym > end or ym > LATEST_CURATED or ym == "2025-10":
                continue
            u = f"{BASE}oce-wasde-report-data-{ym}.csv"
            validate_url(u, ym)
            months.append((ym, u))
    if not months:
        raise ValueError("No curated USDA release months within selected range")
    return months


def _fetch_once(url: str, expected_month: str) -> bytes:
    validate_url(url, expected_month)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 SIGNAL-K3.3-vintage-research/1.1"})
    with urlopen(req, timeout=22) as resp:
        validate_url(resp.geturl(), expected_month)
        out = io.BytesIO()
        while True:
            data = resp.read(256 * 1024)
            if not data:
                break
            if out.tell() + len(data) > MAX_DOWNLOAD:
                raise ValueError(f"{expected_month} exceeds 35MB download cap")
            out.write(data)
        return out.getvalue()


def fetch(url: str, expected_month: str) -> tuple[bytes, str]:
    """Retrieve from canonical USDA host; on a 404 try one USDA-hosted mirror.

    Never pretend a missing file was retrieved. Both failed URLs remain in the audit.
    """
    validate_url(url, expected_month)
    try:
        return _fetch_once(url, expected_month), url
    except HTTPError as e:
        if e.code != 404 or urlsplit(url).netloc != "www.usda.gov":
            raise
        alt = urlunsplit(("https", MIRROR_HOST, urlsplit(url).path, "", ""))
        print(f"[WARN] {expected_month}: USDA primary returned HTTP 404; checking official mirror {alt}", flush=True)
        try:
            return _fetch_once(alt, expected_month), alt
        except (HTTPError, URLError) as mirror_error:
            raise FileNotFoundError(
                f"{expected_month}: canonical {url} HTTP 404; mirror {alt} -> {mirror_error}"
            ) from mirror_error


def parse_release_bytes(raw: bytes, expected_month: str, source_url: str) -> tuple[list[dict], dict]:
    validate_url(source_url, expected_month)
    if not raw or len(raw) > MAX_DOWNLOAD:
        raise ValueError(f"Invalid USDA file size: {expected_month}")
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    missing = REQUIRED - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"USDA schema drift for {expected_month}: missing {sorted(missing)}")
    matches: dict[tuple[str, str], dict] = {}
    exclusions = Counter()
    releases = set()
    for lineno, row in enumerate(reader, 2):
        release_str = (row.get("ReleaseDate") or "").strip()
        try:
            release = date.fromisoformat(release_str)
        except ValueError as exc:
            raise ValueError(f"Invalid ReleaseDate {expected_month} line {lineno}: {release_str}") from exc
        if release.strftime("%Y-%m") != expected_month:
            raise ValueError(f"USDA release date mismatch at {expected_month} line {lineno}: {release_str}")
        releases.add(release_str)
        if TITLE not in clean(row["ReportTitle"]):
            exclusions["wrong_table"] += 1; continue
        if clean(row["Commodity"]) != "corn" or clean(row["Region"]) not in ("united states", "us", "u.s."):
            exclusions["wrong_product_or_region"] += 1; continue
        if clean(row["Attribute"]) != "ending stocks":
            exclusions["wrong_attribute"] += 1; continue
        if "proj" not in clean(row["ProjEstFlag"]):
            exclusions["not_projection"] += 1; continue
        if clean(row["Unit"]) not in ("million bushels", "mil. bushels"):
            raise ValueError(f"Wrong U.S. corn unit at {expected_month} line {lineno}: {row['Unit']}")
        my = row["MarketYear"].strip()
        if not re.fullmatch(r"20\d{2}/\d{2}", my):
            raise ValueError(f"Malformed marketing year {my} at {expected_month} line {lineno}")
        try:
            value = float(row["Value"].replace(",", ""))
        except ValueError as exc:
            raise ValueError(f"Bad stock value at {expected_month} line {lineno}") from exc
        if not 0 <= value < 1e7:
            raise ValueError(f"Stock value out of range at {expected_month} line {lineno}")
        # Convention ONLY. Not verified actual web-publication timestamp / trade-time availability.
        ts = datetime.combine(release, time(12), ZoneInfo("America/New_York")).isoformat()
        key = (ts, my)
        item = {"release_at": ts, "marketing_year": my, "metric": "ending_stocks", "value": value,
                "unit": "million_bushels", "source_url": source_url, "verification": "official_consolidated_vintage"}
        if key in matches:
            if matches[key]["value"] != value:
                raise ValueError(f"Conflicting USDA values in {expected_month} for {key}")
            exclusions["same_value_duplicate"] += 1
        else:
            matches[key] = item
    if len(releases) != 1:
        raise ValueError(f"Expected one official release date in {expected_month}; got {sorted(releases)}")
    if not matches:
        raise ValueError(f"No U.S. corn projected ending stocks in {expected_month}; exclusions: {dict(exclusions)}")
    info = {"release_month": expected_month, "release_date": next(iter(releases)),
            "url": source_url, "sha256": hashlib.sha256(raw).hexdigest(),
            "input_bytes": len(raw), "records": len(matches), "excluded": dict(exclusions)}
    return list(matches.values()), info


def collect(sources: list[tuple[str, str]], loader) -> tuple[list[dict], dict]:
    """Partial success is retained with explicit gaps, never invented values."""
    all_rows: dict[tuple[str, str], dict] = {}
    sources_audit, failures = [], []
    for index, (month, url) in enumerate(sources, 1):
        print(f"[K3.3] ({index}/{len(sources)}) Fetching vintage {month}: {url}", flush=True)
        try:
            loaded = loader(url, month)
            if isinstance(loaded, tuple) and len(loaded) == 2:
                raw, retrieved_from = loaded
            else:  # backwards compatible with offline unit-test loaders
                raw, retrieved_from = loaded, url
            validate_url(retrieved_from, month)
            rows, entry = parse_release_bytes(raw, month, url)
            entry["retrieved_from"] = retrieved_from
            sources_audit.append(entry)
            for row in rows:
                key = (row["release_at"], row["marketing_year"])
                if key in all_rows:
                    raise ValueError(f"Duplicate cross-source release+crop-year: {key}")
                all_rows[key] = row
            print(f"[OK] {month}: {len(rows)} U.S. corn vintage row(s)", flush=True)
        except (HTTPError, URLError, FileNotFoundError, ValueError, UnicodeError, OSError) as e:
            if isinstance(e, HTTPError) and e.code == 404 or isinstance(e, FileNotFoundError):
                category = "HTTP_404_MISSING"
            elif isinstance(e, (HTTPError, URLError, OSError)):
                category = "NETWORK_ERROR"
            else:
                category = "PARSE_OR_VALIDATION_ERROR"
            failure = {"month": month, "url": url, "category": category,
                       "error": f"{type(e).__name__}: {e}"}
            failures.append(failure)
            print(f"[ERROR] {month} {category}: {failure['error']}", flush=True)
    ordered = sorted(all_rows.values(), key=lambda r: (r["release_at"], r["marketing_year"]))
    years = defaultdict(list)
    for r in ordered:
        years[r["marketing_year"]].append((datetime.fromisoformat(r["release_at"]), r["value"]))
    transitions = sum(max(0, len(x) - 1) for x in years.values())
    known_missing = ["2025-10"] if sources[0][0] <= "2025-10" <= sources[-1][0] else []
    unavailable = [f["month"] for f in failures]
    volume_gate = transitions >= 24 and len(years) >= 3
    serious_error = any(f["category"] != "HTTP_404_MISSING" for f in failures)
    if not volume_gate:
        status = "FAILED_INSUFFICIENT_HISTORY"
    elif serious_error:
        status = "FAILED_NON_404_SOURCE_ERRORS"
    elif failures:
        status = "PARTIAL_HISTORY_REQUIRES_MISSING_MONTH_REVIEW"
    else:
        status = "COLLECTED_NEEDS_SPOTCHECK"
    audit = {"version": "K3.3.1", "status": status,
             "release_files_requested": len(sources), "release_files_collected": len(sources_audit),
             "records": len(ordered), "marketing_years": sorted(years), "transitions": transitions,
             "meets_volume_gate": volume_gate, "serious_source_error": serious_error,
             "sources": sources_audit, "download_failures": failures,
             "missing_release_months": known_missing + unavailable,
             "warning": "A 404 is a documented missing USDA download; gaps must be reviewed and cannot be imputed. "
                        "12:00 ET is a convention, NOT independent proof of exact web availability or a backtest. "
                        "K3.2 balance validation does not prove investment-model predictive power."}
    return ordered, audit


def write_csv(rows: list[dict], file: Path):
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2023-01")
    p.add_argument("--end", default=LATEST_CURATED)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--min-transitions", type=int, default=24)
    a = p.parse_args()
    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", a.start) or not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", a.end):
        p.error("Invalid YYYY-MM format")
    if a.start > a.end:
        p.error("Start must not be after end")
    sources = manifest(a.start, a.end)
    rows, audit = collect(sources, fetch)
    # Always write the diagnostic files, including when all source downloads fail.
    write_csv(rows, a.output)
    a.audit.parent.mkdir(parents=True, exist_ok=True)
    a.audit.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in audit.items() if k != "sources"}, ensure_ascii=False, indent=2), flush=True)
    if audit["transitions"] < a.min_transitions or len(audit["marketing_years"]) < 3:
        raise SystemExit("FAILED VOLUME GATE: inspect k33-review/vintage_archive_audit.json")
    if audit["serious_source_error"]:
        raise SystemExit("FAILED SOURCE QUALITY GATE: non-404 download or parsing error; inspect audit")
    if audit["download_failures"]:
        print("[WARN] Some USDA releases are unavailable. Data are PARTIAL; check months before backtest.", flush=True)


if __name__ == "__main__":
    main()
