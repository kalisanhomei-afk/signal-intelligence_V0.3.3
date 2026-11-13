"""K3.7 Agent D: exploratory, provenance-aware structural alignment only.

This script MUST NOT certify historical availability, create trading signals,
replace vintage data, or treat calendar ordering as proof of PIT eligibility.
Inputs are official-source GitHub Actions artifact bundles; run the source
bundle SHA-256 checker separately *before* this script.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

YEARS = (2016, 2020, 2022)
FIELDS = (
    "wasde_release_date", "wasde_marketing_year", "wasde_ending_stocks_million_bushels",
    "wasde_source_sha256", "state", "nass_report_date", "nass_week_ending",
    "nass_good_excellent_pct", "nass_source_sha256", "nass_source_version_id",
    "alignment_rule", "timestamp_quality", "pit_certified",
)


def must(condition, reason):
    if not condition:
        raise ValueError(reason)


def csv_rows(path: Path):
    must(path.is_file(), f"Required official source CSV missing: {path}")
    with path.open(newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        must(reader.fieldnames is not None, f"Missing CSV header: {path}")
        return list(reader)


def d(s: str):
    return date.fromisoformat(s)


def validate_sources(wasde, nass):
    anomalies = Counter()
    must(wasde and nass, "No authentic observations available")
    for r in wasde:
        must(d(r["release_date"]).year in YEARS, "WASDE release year outside pilot")
        must(r["commodity"] == "Corn" and r["region"] == "United States", "WASDE wrong scope")
        must(len(r["source_sha256"]) == 64, "Missing WASDE source digest")
        must(r["timestamp_quality"] in ("UNKNOWN", "OFFICIAL_SCHEDULE_PROXY"), "Unexpected WASDE publication-time certification")
        must(not r["published_at_utc"] and not r["available_at_utc"], "Unreviewed WASDE temporal claims")
        must(r["quality_status"] == "PIT_UNVERIFIED", "WASDE changed vintage quality")
        try:
            must(Decimal(r["value"]).is_finite(), "Nonfinite WASDE numeric value")
        except InvalidOperation as exc:
            raise ValueError("Invalid WASDE numeric value") from exc
        metric, unit = r["metric"], r["unit"]
        if metric.endswith("_million_bushels"):
            must(unit == "Million Bushels", "WASDE stock/flow unit mismatch")
        elif metric.endswith("_million_acres"):
            must(unit == "Million Acres", "WASDE land unit mismatch")
        elif metric == "yield_bushels_per_acre":
            if unit == "Bushels":
                anomalies["YIELD_UNIT_LABEL_AMBIGUOUS_BUSHELS_VS_PER_ACRE"] += 1
            else:
                must(unit in ("Bushels per Acre", "Bushels/Acre"), "WASDE yield unit mismatch")
        else:
            raise ValueError("Unrecognized WASDE metric: " + metric)

    for r in nass:
        must(d(r["report_date"]).year in YEARS and d(r["week_ending"]) < d(r["report_date"]), "Invalid NASS chronology")
        must(r["crop"] == "CORN" and r["calendar_year"] in tuple(map(str, YEARS)), "NASS wrong crop/year")
        must(len(r["source_sha256"]) == 64, "Missing NASS source digest")
        must(r["timestamp_quality"] in ("UNKNOWN", "OFFICIAL_SCHEDULE_PROXY"), "Unexpected NASS publication-time certification")
        must(not r["published_at_utc"] and not r["available_at_utc"], "Unreviewed NASS temporal claims")
        must("PIT_UNVERIFIED" in r["quality_status"], "NASS changed vintage quality")
        vals = [int(r[c]) for c in ("very_poor_pct", "poor_pct", "fair_pct", "good_pct", "excellent_pct")]
        must(all(0 <= x <= 100 for x in vals) and abs(sum(vals) - 100) <= 1,
             "NASS percentage out of range or nonconserving")
        must(int(r["good_excellent_pct"]) == int(r["good_pct"]) + int(r["excellent_pct"]),
             "NASS derived good+excellent mismatch")
        if r.get("revision_marker", "").lower() == "true":
            anomalies["NASS_REVISION_MARKER_TRUE_ORIGINALITY_UNVERIFIED"] += 1
    return anomalies


def align(wasde, nass):
    """Latest older NASS report with *same* crop marketing year and state.

    Strict report date < WASDE release date prevents same-day assumptions.
    This is **not** a legitimate PIT join; no unverified rows are certified.
    """
    stock_rows = [r for r in wasde if r["metric"] == "ending_stocks_million_bushels"]
    groups = defaultdict(list)
    for r in nass:
        groups[(r["marketing_year"], r["state"])].append(r)
    for values in groups.values():
        values.sort(key=lambda r: (r["report_date"], r["week_ending"], r["source_sha256"]))
    aligned, exclusions = [], Counter()
    for stock in stock_rows:
        sd, my = d(stock["release_date"]), stock["marketing_year"]
        for (crop_my, state), candidates in sorted(groups.items()):
            if crop_my != my:
                continue
            earlier = [r for r in candidates if d(r["report_date"]) < sd]
            if not earlier:
                exclusions["NO_STRICTLY_EARLIER_NASS_REPORT"] += 1
                continue
            latest = max(r["report_date"] for r in earlier)
            latest_rows = [r for r in earlier if r["report_date"] == latest]
            if len(latest_rows) != 1:
                exclusions["CONFLICTING_OR_DUPLICATE_LATEST_REPORT"] += 1
                continue
            row = latest_rows[0]
            must(d(row["report_date"]) < sd, "Future or same-day NASS row leaked")
            aligned.append({
                "wasde_release_date": stock["release_date"],
                "wasde_marketing_year": my,
                "wasde_ending_stocks_million_bushels": stock["value"],
                "wasde_source_sha256": stock["source_sha256"],
                "state": state, "nass_report_date": row["report_date"],
                "nass_week_ending": row["week_ending"],
                "nass_good_excellent_pct": row["good_excellent_pct"],
                "nass_source_sha256": row["source_sha256"],
                "nass_source_version_id": row["source_version_id"],
                "alignment_rule": "RESEARCH_ONLY_REPORT_DATE_STRICTLY_LESS_THAN_RELEASE_DATE",
                "timestamp_quality": "PIT_UNVERIFIED",
                "pit_certified": "false",
            })
    return aligned, exclusions


def report(wasde, nass, aligned, anomalies, excluded):
    wyears = Counter(x["release_date"][:4] for x in wasde)
    nyears = Counter(x["calendar_year"] for x in nass)
    jyears = Counter(x["wasde_release_date"][:4] for x in aligned)
    md = {str(y): {"wasde_metric_rows": wyears[str(y)],
                   "wasde_release_months": len({r["release_date"][:7] for r in wasde if r["release_date"][:4] == str(y)}),
                   "nass_state_week_rows": nyears[str(y)],
                   "nass_observed_report_dates": len({r["report_date"] for r in nass if r["calendar_year"] == str(y)}),
                   "exploratory_aligned_state_rows": jyears[str(y)]} for y in YEARS}
    return {
        "status": "STRUCTURAL_ALIGNMENT_PIT_UNVERIFIED",
        "research_only": True,
        "calendar_ordering_is_not_PIT_evidence": True,
        "pit_certified": False,
        "certified_join_rows": 0,
        "source_run_id": 43448555468,
        "source_artifact_ids": {"wasde": 14049815789, "nass": 14049291864, "pit": 14049231951},
        "input_counts": {"wasde_metric_rows": len(wasde), "nass_state_week_rows": len(nass)},
        "alignment": {"rows": len(aligned), "by_pilot_year": md, "excluded": dict(excluded)},
        "quality_warnings": dict(anomalies),
        "release_coverage_unverified": True,
        "source_version_originality_unverified": True,
        "historical_public_availability_verified": 0,
        "next_required": ["Independent source-to-official-report spot check",
                          "Resolve WASDE yield-unit label and NASS revision/originality semantics",
                          "Audit expected report coverage per year",
                          "Obtain per-vintage public-time evidence before any PIT-certified backtest"],
    }


def run(inputs: Path, output: Path):
    wasde = csv_rows(inputs / "wasde/wasde/wasde_vintages.csv")
    nass = csv_rows(inputs / "nass/nass-out/nass_state_weekly.csv")
    anomalies = validate_sources(wasde, nass)
    aligned, exclusions = align(wasde, nass)
    summary = report(wasde, nass, aligned, anomalies, exclusions)
    must(all(summary["alignment"]["by_pilot_year"][str(y)]["wasde_metric_rows"] > 0 and
             summary["alignment"]["by_pilot_year"][str(y)]["nass_state_week_rows"] > 0
             for y in YEARS), "Missing entire pilot year")
    must(all(r["pit_certified"] == "false" for r in aligned), "PIT status incorrectly promoted")
    output.mkdir(parents=True, exist_ok=True)
    with (output / "structural_alignment_NOT_PIT.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(aligned)
    (output / "integration_quality.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run(args.input, args.output)


if __name__ == "__main__":
    main()
