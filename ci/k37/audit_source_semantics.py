"""Independent K3.7 QA of official source semantics, NOT historical PIT certification.

Compare every NASS state/corn rating with the 2026-11-13 downloaded official text
and every WASDE yield value/unit to the official CSV inside original raw bytes.
Classify generic NASS Revision Policy separately from report-specific revisions.
"""
import argparse
import csv
from datetime import date
from email.utils import parsedate_to_datetime
from collections import Counter
from decimal import Decimal
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

YEARS = {"2016", "2020", "2022"}
RATINGS = ("very_poor_pct", "poor_pct", "fair_pct", "good_pct", "excellent_pct")
EXPLICIT = re.compile(r"(?im)^[ \t]*(?:Revised\b|Corrected\b|Correction[ \t]+(?:Notice|to|of)\b|Revision[ \t]+(?:Notice|to|of)\b)")
POLICY = re.compile(r"(?im)^\s*Revision Policy:")


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def records(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def corn_section(text):
    match = re.search(r"Corn Condition\s*-\s*Selected States\s*:\s*Week Ending[^\n]*", text, re.I)
    if not match:
        return ""
    remaining = text[match.end():]
    end = re.search(r"(?mi)^\s*[A-Za-z][A-Za-z /]+\s*-\s*Selected States\b", remaining)
    return remaining[:end.start()] if end else remaining


def nass_audit(root, fixed_dir):
    old = records(root / "nass-out/nass_state_weekly.csv")
    new = records(fixed_dir / "nass_state_weekly.csv")
    require(len(old) == len(new) == 1006, "NASS observation count changed")
    key = lambda r: (r["report_date"], r["week_ending"], r["state"], r["source_sha256"])
    old_by = {key(r): r for r in old}
    new_by = {key(r): r for r in new}
    require(len(old_by) == len(old) and set(old_by) == set(new_by), "NASS observations/sources changed")
    for k, original in old_by.items():
        corrected = new_by[k]
        for col in (*RATINGS, "good_excellent_pct", "source_url", "retrieved_at_utc", "source_version_id"):
            require(original[col] == corrected[col], "NASS numbers/provenance modified during classification repair")

    ledger = [json.loads(l) for l in (root / "nass-bundle/source_manifest.jsonl").read_text().splitlines() if l.strip()]
    report_sources = [x for x in ledger if x.get("role") == "report" and x.get("status") == "DOWNLOADED"]
    require(len(report_sources) == 106, "Unexpected official NASS source count")
    # HTTP Last-Modified describes a server resource, NOT first public release.
    # An archive migration can post-date the historical report by years.
    modified_date_audit = {}
    for item in report_sources:
        year = item["expected_report_date"][:4]
        group = modified_date_audit.setdefault(year, {"SAME_CALENDAR_DATE": 0, "LATER_DATE": 0,
                                                      "EARLIER_DATE": 0, "HEADER_MISSING": 0})
        raw_header = item.get("last_modified", "")
        if not raw_header:
            group["HEADER_MISSING"] += 1
            continue
        modified = parsedate_to_datetime(raw_header).date()
        original = date.fromisoformat(item["expected_report_date"])
        label = "SAME_CALENDAR_DATE" if modified == original else (
            "LATER_DATE" if modified > original else "EARLIER_DATE")
        group[label] += 1
    blocks = {}
    policy_count = explicit_count = 0
    for item in report_sources:
        raw = (root / "nass-bundle" / item["raw_path"]).read_bytes().decode("utf-8-sig", errors="replace")
        policy_count += bool(POLICY.search(raw))
        explicit_count += bool(EXPLICIT.search(raw))
        blocks[item["source_sha256"]] = corn_section(raw)
    require(explicit_count == 0, "Explicit release-specific revision notices present: manual review needed")
    matched = 0
    for k, row in new_by.items():
        text = blocks.get(row["source_sha256"], "")
        pattern = rf"(?m)^\s*{re.escape(row['state'])}\s*\.+:\s*([\d\s-]+)"
        hits = list(re.finditer(pattern, text))
        require(len(hits) == 1, "NASS original table row not uniquely located: " + repr(k))
        raw_values = hits[0].group(1).split()[:5]
        require(raw_values == [row[c] for c in RATINGS], "NASS values do not match original report")
        require(old_by[k]["revision_marker"] == "true", "Legacy marker unexpected")
        require(row["revision_marker"] == "false", "Policy text still falsely marks revised edition")
        require(row["quality_status"] == "PIT_UNVERIFIED", "Corrected output falsely certifies PIT")
        require(row["source_version_status"] == "ARCHIVE_RETRIEVED_EDITION_ORIGINALITY_UNVERIFIED",
                "Unverified source edition mislabelled original")
        require(row["available_at_utc"] == "", "Historical availability must remain unknown")
        matched += 1
    return {"source_reports": len(report_sources),
            "reports_containing_boilerplate_revision_policy": policy_count,
            "reports_containing_explicit_revision_notice": explicit_count,
            "http_last_modified_metadata_by_report_year": modified_date_audit,
            "http_last_modified_not_publication_evidence": True,
            "old_revision_marked_rows": len(old),
            "corrected_release_revision_marked_rows": 0,
            "independently_text_matched_state_week_rows": matched,
            "original_edition_verified": False,
            "classification": "NO_EXPLICIT_RELEASE_SPECIFIC_REVISION_NOTICE_OBSERVED",
            "pit_certified": False}


def raw_csvs(file):
    b = file.read_bytes()
    if b[:2] == b"PK":
        with ZipFile(io.BytesIO(b)) as z:
            return [z.read(n) for n in z.namelist() if n.lower().endswith(".csv")]
    return [b]


def wasde_audit(root):
    rows = records(root / "wasde/wasde_vintages.csv")
    yields = [r for r in rows if r["metric"] == "yield_bushels_per_acre"]
    require(len(yields) == 108, "WASDE yield count unexpectedly changed")
    index = set()
    for digest in {r["source_sha256"] for r in yields}:
        source = root / "wasde_raw" / (digest + ".bin")
        require(source.exists(), "WASDE raw source missing")
        for blob in raw_csvs(source):
            for r in csv.DictReader(io.StringIO(blob.decode("utf-8-sig"))):
                if (r["Attribute"] == "Yield per Harvested Acre" and
                        r["Commodity"] == "Corn" and r["Region"] == "United States" and
                        r["AnnualQuarterFlag"] == "Annual"):
                    index.add((digest, r["ReleaseDate"], r["MarketYear"], Decimal(r["Value"]), r["Unit"]))
    for r in yields:
        key = (r["source_sha256"], r["release_date"], r["marketing_year"], Decimal(r["value"]), r["unit"])
        require(key in index, "WASDE yield differs from original official CSV")
        require(r["available_at_utc"] == "" and r["timestamp_quality"] == "UNKNOWN",
                "WASDE unavailable PIT source incorrectly certified")
    years = dict(Counter(r["release_date"][:4] for r in yields))
    require(set(years) == YEARS and all(x == 36 for x in years.values()), "Pilot years unexpectedly missing")
    require(all(r["unit"] == "Bushels" for r in yields), "Official raw WASDE unit semantics changed")
    return {"original_attribute": "Yield per Harvested Acre",
            "official_raw_unit": "Bushels",
            "canonical_display_unit": "bushels/harvested-acre",
            "numeric_transform_required": False,
            "preserve_original_unit": True,
            "original_csv_yield_records_matched": len(yields), "by_year": years,
            "pit_certified": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--rebuilt-nass", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    out = {"schema_version": "K37_SOURCE_SEMANTICS_QA_V1",
           "source_run_id": 43448555468,
           "status": "SOURCE_VALUES_AND_SEMANTICS_QA_PASS_PIT_UNVERIFIED",
           "historical_availability_certified": 0, "pit_certified_rows": 0,
           "nass": nass_audit(args.input / "nass", args.rebuilt_nass),
           "wasde": wasde_audit(args.input / "wasde"),
           "outstanding": ["Confirm archive edition originality for each release",
                           "Independently verify historical public availability times",
                           "Audit complete official release calendar coverage",
                           "Preserve original official source ZIPs before artifact expiry"]}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "source_semantics_audit.json").write_text(
        json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
