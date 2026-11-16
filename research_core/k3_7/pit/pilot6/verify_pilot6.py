"""Fail-closed six-case historical source/independent-content evidence gate.

Verifies exact USDA *currently archived* source bytes, target dates and
national statistic, not the historical timestamp or initial file edition.
Contemporaneous media page claims are recorded, never certified as original
USDA byte identity or historical public access.
"""
import argparse
import csv
import hashlib
import io
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

EXPECTED = {(s, y) for s in ("WASDE", "NASS") for y in (2016, 2020, 2022)}


def check(ok, reason):
    if not ok:
        raise AssertionError(reason)


def hash_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def csv_data(blob):
    return list(csv.DictReader(io.StringIO(blob.decode("utf-8-sig"))))


def validate_wasde(original: bytes, r: dict) -> dict:
    if r["source_member"]:
        with ZipFile(io.BytesIO(original)) as z:
            check(r["source_member"] in z.namelist(), "WASDE source archive missing member")
            blob = z.read(r["source_member"])
            check(hash_bytes(blob) == r["source_member_sha256"], "WASDE CSV member hash mismatch")
    else:
        blob = original
    hit = [
        a for a in csv_data(blob) if
        a["ReportTitle"] == "U.S. Feed Grain and Corn Supply and Use" and
        a["ReleaseDate"] == r["release_date"] and
        a["MarketYear"] == r["marketing_year"] and
        a["Commodity"] == "Corn" and a["Region"] == "United States" and
        a["Attribute"] == "Ending Stocks" and
        a["AnnualQuarterFlag"] == "Annual" and
        a["Unit"] == r["official_unit"]
    ]
    check(len(hit) == 1, "Ambiguous/missing original WASDE corn ending stocks record")
    check(Decimal(hit[0]["Value"]) == Decimal(r["official_numeric_value"]),
          "WASDE observed numerical value not equal to catalog")
    return {"kind": "WASDE", "year": r["year"], "release_date": r["release_date"],
            "metric": r["metric"], "marketing_year": r["marketing_year"],
            "verified_official_raw_numeric_value": hit[0]["Value"],
            "official_publication_clock_field_noncertifying": hit[0].get("ReleaseTime", "")}


def validate_nass(original: bytes, r: dict) -> dict:
    body = original.decode("utf-8-sig")
    release_date = date.fromisoformat(r["release_date"])
    formatted = f"Released {release_date.strftime('%B')} {release_date.day}, {release_date.year}"
    check(formatted in body, "Official NASS released date missing or mismatched")
    head = re.search(r"(?im)^Corn Condition\s*-\s*Selected States:\s*Week Ending[^\n]*", body)
    check(head is not None, "NASS corn condition section missing")
    within = body[head.end():]
    row = re.search(r"(?m)^18 States\s*\.+:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", within)
    check(row is not None, "NASS original 18-state condition summary missing")
    a = [int(v) for v in row.groups()]
    check(a == r["national_condition_five_categories"], "NASS original five ratings mismatch")
    check(sum(a) == 100, "NASS national share total unequal to 100")
    check(a[3] + a[4] == int(r["official_numeric_value"]), "NASS good+excellent mismatch")
    return {"kind": "NASS", "year": r["year"], "release_date": r["release_date"],
            "metric": r["metric"], "verified_official_raw_numeric_value": str(a[3] + a[4]),
            "national_condition_five_categories": a}


def run(catalog: Path, inp: Path, out: Path):
    j = json.loads(catalog.read_text(encoding="utf-8"))
    samples = j["records"]
    check(len(samples) == 6 and {(x["kind"], x["year"]) for x in samples} == EXPECTED,
          "PIT6 catalog must have exactly six unique selected records")
    check(j["certified_public_timestamp_count"] == 0, "Catalog falsely claims certification")
    findings = []
    for r in samples:
        check(r["timestamp_quality"] == "UNKNOWN" and
              r["published_at_utc"] == r["available_at_utc"] == "" and
              r["pit_certified"] is False, "Uncertified historical access falsely promoted")
        check(r["raw_official_bytes_historical_public_by_utc"] is None and
              r["raw_official_version_historical_first_issuance_confirmed"] is False and
              r["media_first_public_capture_at_utc"] is None,
              "Evidence catalog incorrectly certifies first availability")
        check(r["source_url"].startswith("https://"), "Unapproved source scheme")
        kind = r["kind"]
        subdir = "wasde/wasde_raw" if kind == "WASDE" else "nass/nass-bundle/raw"
        p = inp / subdir / (r["raw_source_sha256"] + ".bin")
        check(p.is_file(), f"Missing source raw input: {p}")
        raw = p.read_bytes()
        check(hash_bytes(raw) == r["raw_source_sha256"], "Source SHA-256 mismatch")
        value = validate_wasde(raw, r) if kind == "WASDE" else validate_nass(raw, r)
        value.update({
            "source_url": r["source_url"],
            "verified_raw_source_sha256": r["raw_source_sha256"],
            "third_party_article_url": r["content_evidence_url"],
            "third_party_article_date_claim": r["content_evidence_date_claim"],
            "third_party_article_value_match_claim_recorded_in_catalog": r["content_value_check"],
            "historical_media_snapshot_cryptographically_verified": False,
            "historical_official_file_edition_verified": False,
            "independent_historical_public_timestamp_verified": False,
            "timestamp_quality": "UNKNOWN",
            "pit_certified": False,
            "conclusion": "ORIGINAL_ARCHIVED_VALUES_VERIFIED_PUBLIC_TIME_NOT_CERTIFIED",
        })
        findings.append(value)
    output = {
        "schema": "signal-k37-pit6-source-qa-v1", "source_run_id": j["source_artifact_run_id"],
        "pilot_sample_count": len(findings), "verified_current_archived_source_value_count": len(findings),
        "third_party_article_claims_recorded_not_tamperproof": len(findings),
        "byte_identical_original_historical_vintage_certified": 0,
        "historical_public_timestamp_certified": 0, "pit_certified_rows": 0,
        "ready_for_historical_pit_backtest": False,
        "result": "VALUE_CORROBORATION_PILOT_PASS_PIT_UNVERIFIED",
        "findings": findings,
        "blocking_gaps": [
            "Publisher page original initial publication timestamp is not independently authenticated",
            "Third-party news numerical quotations are not byte-identical USDA source snapshots",
            "2016 and 2020 WASDE bytes are currently delivered via a later consolidated archive",
            "No contemporaneously captured identical source original-byte SHA for any selected release",
            "No feature from these six examples can be promoted to a certified historical PIT backtest",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "pit6_source_value_gate.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in output.items() if k != "findings"}, ensure_ascii=False))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.catalog, args.input, args.output)
