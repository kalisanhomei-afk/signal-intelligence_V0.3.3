# SIGNAL K3.7 pilot data contract v0.1

**Scope:** immutable USDA research observations for **2016, 2020, 2022**. Schema proposal for agent coordination; don't overwrite K3.4/K3.6 frozen datasets.

## Required provenance fields in each observation
- `source_url`: exact official original resource (not a synthesized URL that did not resolve).
- `source_sha256`: SHA-256 of the downloaded raw bytes (hash canonicalization, if any, must be separately named).
- `release_date` or `report_date`: ISO `YYYY-MM-DD` from source.
- `published_at_utc`: exact historical public publication timestamp **only if proven**; otherwise empty.
- `available_at_utc`: independently supported earliest public availability time **only if proven**; otherwise empty.
- `retrieved_at_utc`: this run's actual observed download timestamp; never backdate to a historical date.
- `timestamp_quality`: one of `VERIFIED_PUBLIC_TIMESTAMP`, `OFFICIAL_SCHEDULE_PROXY`, `UNKNOWN`.
- `evidence_url`: direct verifiable time evidence if verified; otherwise blank.
- `quality_status`: e.g. `OK`, `MISSING_OFFICIAL_RELEASE`, `PARSE_ERROR`, `SOURCE_UNAVAILABLE`, `PIT_UNVERIFIED`.

A schedule proxy is **not** a verification of historical public availability. Unknown timestamps must not be filled with inferred values in verified fields.

## A: WASDE output
`research_core/k3_7/wasde/out/wasde_vintages.csv`

Recommended data columns besides provenance: `marketing_year` (e.g. `2019/20`), `commodity`, `region`, `metric`, `value`, `unit`.
Follow prior `research_core/k3_4/integrate.py` conventions where possible. Preserve each monthly **vintage** rather than only the latest value.
Minimum pilot metrics: corn area harvested, yield per harvested acre, production, beginning stocks, imports, total domestic use, exports, ending stocks.

## B: NASS output
`research_core/k3_7/nass/out/nass_state_weekly.csv`

Recommended columns besides provenance: `week_ending`, `state`, `crop`, `very_poor_pct`, `poor_pct`, `fair_pct`, `good_pct`, `excellent_pct`, `good_excellent_pct`. Count only officially reported states/weeks. No interpolation. Report any states missing a condition rating separately.

## C: PIT evidence ledger
`research_core/k3_7/pit/out/pit_evidence_ledger.csv`

Recommended columns: `source_type`, `source_release_date`, `evidence_url`, `published_at_utc`, `available_at_utc`, `timestamp_quality`, `reason`, `evidence_sha256`.
C does not edit A/B outputs; it provides adjudication rules and evidence that D can join by source type/release date/source URL.

## D: Integration
Only after stable A/B/C outputs: produce a join report showing years, months/weeks, coverage gaps, PIT status distribution, and unit/revision checks.
Never interpret a successful accounting join as a predictive edge. Exclude unverified PIT rows from any *certified* result. Do not mix USDA subsequent revisions with what was publicly available at an earlier as-of.
