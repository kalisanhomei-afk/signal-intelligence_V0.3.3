# SIGNAL K3.8｜Forward-only Official Response Observation Pilot

**Manual workflow registration has been approved and merged via PR #20. Real new-report capture has not yet run.** No background jobs, scheduled fetches, trading, strategy evaluation, site deployment, or changes to `main`. Reference: [Issue #18](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/issues/18).

## Exact pilot scope

Capture **one upcoming NASS Crop Progress report** and **one upcoming monthly WASDE report** as original official plain-text (`.txt`) downloads. This first version captures and validates report identity, **not** each corn metric parsed into the signal model. It does **not** backdate actual public release time; download completion UTC is only a *direct observation by SIGNAL*.

Official calendar, as checked on 2026-11-16:
- NASS next Crop Progress: **Nov 16, 2026 at 16:00 ET = Nov 16 21:00 UTC = Taiwan Nov 17 05:00**. Official [ESMIS Crop Progress](https://esmis.nal.usda.gov/publication/crop-progress) is the authoritative publication page. Holiday/change risk: check actual release there.
- WASDE next report: **Dec 10, 2026 at 12:00 ET = Dec 10 17:00 UTC = Taiwan Dec 11 01:00**. Official [WASDE report page](https://usda.azureedge.us/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report).

These are scheduled floors only, NOT the moment the first actual bytes were accessible. Use `AUTO` after the official release to locate exactly one report-date-matching `.txt` URL directly from the official ESMIS publication page. Discovery fails closed on missing or ambiguous links. The operator may alternatively provide the exact verified official `.txt` URL. Never guess filenames or reuse a past report.

## Current implementation and fail-closed record

`capture.py` requires an exact official `.txt` URL **or the sentinel `AUTO`** and a report date. `AUTO` does not contact ESMIS until the operator-supplied official UTC release barrier has passed; it selects only a uniquely date-matching official ESMIS `.txt` link. The receipt records `source_url_resolution_method` and final official URL. It rejects:
- non-HTTPS, non-USDA/NASS hosts, unsupported formats, nonofficial redirects, 403/404, HTML error pages, zero/oversized/truncated responses;
- a run before the conservative not-before floor, an operator barrier before regular official release hour, a future/old source date, stale report header, wrong document type, or no Corn reference in the report;
- an existing output path, a previously observed identical digest in a *provided* ledger, missing or tampered raw/receipt bytes in replay.

**Source-date precision warning (verified against USDA original July 2026 text):** NASS plain text contains an explicit `Released <month> <day>, <year>` line, which can be day-validated. WASDE ESMIS plain text instead shows headers such as `WASDE - 673 - 8     July 2026` and generally does **not** print the exact release day. We validate report ID plus original **month/year** and the U.S. Feed Grain and Corn table; the exact `--release-date` day remains an **operator assertion based on the official ESMIS release listing**, not a proven date extracted from WASDE bytes. `release_date_precision_from_body=MONTH` and `report_date_confirmed_from_body=null` make this explicit. **Implemented:** `AUTO` preserves the original official ESMIS listing HTML, its SHA-256, UTC request/response receipt and the date-exact TXT URL; replay rechecks those bytes against the receipt. The listing snapshot establishes what this system actually observed, not when USDA first made it public.

One successful response outputs `receipt.json`, `manifest.json`, `objects/SOURCE/YYYY-MM-DD/<sha256>.bin` and, for `AUTO`, `catalog/SOURCE/YYYY-MM-DD/<sha256>.html`. Both official source bytes and official catalog snapshot bytes, SHA-256 hashes, selected release-date URL and UTC ordering are replay checked before the job can upload the artifact.

Precise fields distinguish:
- `response_finished_at_utc` = actual response completed **in this runner**;
- `first_observed_at_utc` = observed by **this exact run**, not world's first publication;
- `safe_feature_not_before_utc` = response finish **plus 120 seconds** by default;
- `published_at_utc`, `available_at_utc` = blank; `timestamp_quality=UNKNOWN` for first public origin.
- `source_originality_certified=false`, `cross_run_global_dedup_verified=false`. A prior manifest, when available, supports conditional duplicate detection but is not an authenticated global history or proof of revision.

For each official direct-source report we separately need an actual parsed corn value and source-to-official cross-check before **DATA_VERIFIED** at the indicator level. A successful raw capture is `SYSTEM_OBSERVATION_READY`, **not** financial PIT backtest readiness.

## How to test now

The PR's `pull_request` event runs only deterministic **offline** unit tests:

```bash
python -B -m unittest discover -s research_core/k3_8/tests -p 'test_*.py' -v
```

The `workflow_dispatch` registration file was merged into the default branch by [PR #20](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/pull/20). The `main` copy is deliberately a fail-closed stub; it **never** downloads a report. For manual capture select exactly branch `codex/k38-forward-pit-capture`, which runs the separately reviewed workflow and pins its observer implementation to commit `d325bd7955ec6fc69e95484276dabd348120d729`. Choose `direct_txt_url=AUTO` to avoid copying filenames. **No future-report capture has been executed yet.**

Example only, **after the report is actually published** (pre-release invocation fails without contacting the catalog):

```bash
python -B research_core/k3_8/capture.py \
  --source NASS \
  --release-date 2026-11-16 \
  --url AUTO \
  --not-before-utc 2026-11-16T21:00:00Z \
  --latency-seconds 120 \
  --output k38-capture
python -B research_core/k3_8/capture.py --verify --output k38-capture
```

`AUTO` looks for the uniquely matching official ESMIS link dated 2026-11-16. A missing report is an explicit failure, never a substitute with November 9 data. For WASDE use 2026-12-10 and 2026-12-10T17:00:00Z.

Official prior-format smoke test: independent GitHub Runner checked 2026-08-03 NASS report (day-level source header) and 2026-07-10 WASDE report (month-level source header) directly from ESMIS, and both parsers passed. These are retrospective **format** checks only.

Additionally, GitHub Runner verified exact-date ESMIS HTML link resolution for the already published Nov 9 NASS and Nov 10 WASDE TXT resources, and **37** independent offline guard tests passed, including catalog tamper detection and clock-order safeguards. These prior-report checks are NOT future-release observations.

The observed raw artifact has default **90-day retention**, not durable immutable archival and not global deduplication. **No public GitHub Release**, cross-run persistent storage, or recurring schedule without separate approval.

## Release decision

**CODE_READY** after independent GitHub CI green; then conduct a two-source manual test after the actual official release with source URL, source-byte SHA256, report identity, finished UTC and independent replay. Reject apparent success if a direct `.txt` report parser does not recognize the newly published USDA layout; fix the parser based on actual original bytes in a separate reviewed PR. Real-report usability **NO-GO** until two independent actual capture artifacts pass.

See [K3.7 original data preservation Issue #14](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/issues/14); existing 90-day raw copy expires **2027-02-14 UTC**. This K3.8 workflow alone is not an automatic archive guarantee.
