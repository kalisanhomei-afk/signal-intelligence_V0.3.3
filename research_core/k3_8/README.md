# SIGNAL K3.8｜Forward-only Official Response Observation Pilot

**CODE_ONLY until manual workflow registration is explicitly approved.** No background jobs, scheduled fetches, trading, strategy evaluation, site deployment, or changes to `main`. Reference: [Issue #18](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/issues/18).

## Exact pilot scope

Capture **one upcoming NASS Crop Progress report** and **one upcoming monthly WASDE report** as original official plain-text (`.txt`) downloads. This first version captures and validates report identity, **not** each corn metric parsed into the signal model. It does **not** backdate actual public release time; download completion UTC is only a *direct observation by SIGNAL*.

Official calendar, as checked on 2026-11-16:
- NASS next Crop Progress: **Nov 16, 2026 at 16:00 ET = Nov 16 21:00 UTC = Taiwan Nov 17 05:00**. Official [ESMIS Crop Progress](https://esmis.nal.usda.gov/publication/crop-progress) is the authoritative publication page. Holiday/change risk: check actual release there.
- WASDE next report: **Dec 10, 2026 at 12:00 ET = Dec 10 17:00 UTC = Taiwan Dec 11 01:00**. Official [WASDE report page](https://usda.azureedge.us/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report).

These are scheduled floors only, NOT the moment the first actual bytes were accessible. The directly published `.txt` URL must be obtained from the **specific new official report** after publication and copied exactly; do NOT use current indexes, last month's files, the day-after-updated consolidated CSV, or invented URL paths.

## Current implementation and fail-closed record

`capture.py` requires one explicitly operator-specified official `.txt` URL and report date. It rejects:
- non-HTTPS, non-USDA/NASS hosts, unsupported formats, nonofficial redirects, 403/404, HTML error pages, zero/oversized/truncated responses;
- a run before the conservative not-before floor, an operator barrier before regular official release hour, a future/old source date, stale report header, wrong document type, or no Corn reference in the report;
- an existing output path, a previously observed identical digest in a *provided* ledger, missing or tampered raw/receipt bytes in replay.

One successful response outputs `receipt.json`, `manifest.json`, and `objects/SOURCE/YYYY-MM-DD/<sha256>.bin`; all source bytes and receipts are checked before the job can upload the artifact.

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

The `workflow_dispatch` input contract is already authored in `.github/workflows/signal-k38-manual-capture.yml`, but **GitHub only enables it after that workflow is registered on the repository default branch**. This Draft PR is isolated and has deliberately NOT been merged to `main`. Therefore a **manual Run workflow button should not yet be expected or used**. Registration is a separate explicit owner review/governance decision before future live collection.

Example only, after registration and selecting a freshly released **real** official resource URL:

```bash
python -B research_core/k3_8/capture.py \
  --source NASS \
  --release-date 2026-11-16 \
  --url '<ACTUAL_OFFICIAL_NOV_16_NASS_TXT_URL>' \
  --not-before-utc 2026-11-16T21:00:00Z \
  --latency-seconds 120 \
  --output k38-capture
python -B research_core/k3_8/capture.py --verify --output k38-capture
```

The actual CLI command must replace the displayed URL placeholder; it is **not** an existing or valid URL. For WASDE use Dec 10 and 2026-12-10T17:00:00Z.

The observed raw artifact has default **90-day retention**, not durable immutable archival and not global deduplication. **No public GitHub Release**, cross-run persistent storage, or recurring schedule without separate approval.

## Release decision

**CODE_READY** after independent GitHub CI green; then conduct a two-source manual test after the actual official release with source URL, source-byte SHA256, report identity, finished UTC and independent replay. Reject apparent success if a direct `.txt` report parser does not recognize the newly published USDA layout; fix the parser based on actual original bytes in a separate reviewed PR. Real-report usability **NO-GO** until two independent actual capture artifacts pass.

See [K3.7 original data preservation Issue #14](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/issues/14); existing 90-day raw copy expires **2027-02-14 UTC**. This K3.8 workflow alone is not an automatic archive guarantee.
