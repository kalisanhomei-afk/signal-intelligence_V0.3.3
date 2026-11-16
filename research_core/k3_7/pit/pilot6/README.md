# SIGNAL K3.7 — Six-report historical evidence pilot (2016/2020/2022)

**Decision: VALUE-CORROBORATION PILOT ONLY; PIT_UNVERIFIED.**

Exactly six immutable USDA source examples are recorded in `evidence_candidates.json`:

| Year | WASDE U.S. corn ending stocks (June release) | NASS U.S. corn good/excellent |
|---|---|---|
| 2016 | 2016-06-10, 2016/17, 2008 million bu | 2016-06-06, 75% |
| 2020 | 2020-06-11, 2020/21, 3323 million bu | 2020-06-08, 75% |
| 2022 | 2022-06-10, 2021/22, 1485 million bu | 2022-06-06, 73% |

Values were cross-checked against contemporaneous articles by DTN and Farm Progress; the exact source URL, source hash and article URL are retained in the JSON catalog. Sources: https://www.dtnpf.com/agriculture/web/ag/news/article/2016/06/09/dependent-independent-numbers ; https://www.dtnpf.com/agriculture/web/ag/news/article/2016/06/06/numbers-neutral-bearish ; https://www.dtnpf.com/agriculture/web/ag/news/article/2020/06/11/usda-releases-june-crop-production ; https://www.farmprogress.com/farm-operations/usda-crop-progress-corn-quality-on-the-rise ; https://www.dtnpf.com/agriculture/web/ag/news/article/2022/06/10/usda-releases-june-crop-production ; https://www.dtnpf.com/agriculture/web/ag/news/article/2022/06/06/usda-crop-progress-report-94-corn-73 .

## What the automated check actually proves

After `ci/k37/verify_source_bundles.py` rechecks original raw content against SHA-256, `verify_pilot6.py` independently checks:

- The named original USDA consolidated CSV member (2016/2020) or direct June 2022 CSV contains exactly one correct U.S. corn ending-stocks row with matching release date, marketing year and value.
- The original downloaded NASS TXT has the correct release header and 18-state national Corn Condition row with all five exact percentages.
- No source date, third-party article timestamp or CSV `ReleaseTime` is promoted into `published_at_utc` or `available_at_utc`.
- Third-party article publication dates and numeric claims were reviewed externally in 2026, **not independently captured/cryptographically timestamped as of the original release day**. Archived publisher pages may have subsequently changed.
- The consolidated 2016–2020 WASDE ZIP is an after-the-fact historical distribution, **not a byte-identical source proven to have existed in June 2016/2020**.

All six remain `timestamp_quality=UNKNOWN`, `pit_certified=false`, certified historical file-version count zero. Even a successful GitHub CI run is **not** PIT certification, nor a basis for a point-in-time backtest.

## Next decision

Instead of demanding historically identical bulk ZIPs for every data element, consider a separately reviewed metric-level historical evidence contract: contemporaneous, independently timestamped report contents could establish that **specific numbers** were public by a conservative cutoff, without proving the current ZIP bytes were public. That requires a formal schema and independent immutable/archival timestamp check, not simply the current HTML article date.

Keep this exploratory pilot out of formal portfolio allocation/trading signals until the PIT gate passes. Source GitHub Artifacts from run 43448555468 expire November 27, 2026 UTC; evidence preservation is tracked by Issue #14.
