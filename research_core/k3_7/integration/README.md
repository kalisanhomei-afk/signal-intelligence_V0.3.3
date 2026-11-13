# SIGNAL K3.7 Agent D — Exploratory Integration (PIT_UNVERIFIED)

## Follow-up official-source semantics correction (2026-11-13)

[Independent successful QA run 43462897263](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/43462897263) compares all **1,006 NASS** condition rows and **108 WASDE yield** rows directly with original official downloaded source bytes. The original Agent B marker `revision_marker=true` on all 1,006 rows was a false positive caused by generic `Revision Policy:` text in 105/106 official report files; corrected Agent B now reports **0 explicit edition revisions** while preserving `PIT_UNVERIFIED` and **original edition authenticity unverified**. WASDE's raw `Attribute=Yield per Harvested Acre`, `Unit=Bushels` means display quantity is `bushels/harvested-acre`; no numeric conversion.

Agent D rerun with the corrected NASS CSV retained **568 research-only rows**; all 0 PIT-certified. Its previous raw QA run truthfully reported the *pre-correction* revision-marker values; that prior artifact remains historical and is not rewritten. Source evidence timestamps remain unauthenticated: **all 36 archived NASS 2016 reports returned HTTP Last-Modified in September 2018**, never interpreted as 2016 public release time. [Issue #3](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/issues/3) tracks independent PIT evidence.


## Current verified status (2026-11-13)

**EXPLORATORY_INTEGRATION_PASS_PIT_UNVERIFIED.** The original Codex **BLOCKED** report was valid when produced, but has since been resolved by the GitHub Actions cross-run artifact bridge; historical blocked JSON/HTML preserved in `initial_blocked/`.

- Verified source run: [43448555468](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/43448555468) using unchanged exact official-source bytes.
- Independent cross-run SHA-256 and raw receipt checks: [bridge run 43452166061](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/43452166061).
- **Real-source Agent D integration**: [run 43458650573](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/43458650573), Success.
- Unit tests: **10/10 passed**; with raw/source SHA-256 checked and research-only join guard applied.
- Inputs: WASDE **1,512** rows and NASS **1,006** state-week rows.
- Exploratory alignment (NOT a PIT backtest): **568** rows, by year: 2016 **117**, 2020 **119**, 2022 **332**. Excluded **80** candidate alignments without a strictly earlier NASS report.
- **0 historical public availability timestamps certified; 0 PIT-certified joins.**

## Files and reproducibility

- `verify_and_join.py`: read-only production-bundle structural assessment; all outputs have `pit_certified=false`.
- `tests/test_verify_and_join.py`: synthetic **test-only** cases for same-day/future rejection, duplicates, vintage boundaries, percentages, certification refusal and unit warning.
- `acceptance.json`, `acceptance.html`: **current** independently observed source and QA summary.
- `initial_blocked/`: full historical preflight failure reports; retained for audit and not current.
- Integration results from the runner: [data QA artifact](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/actions/runs/43458650573/artifacts/14054827483), including `integration_quality.json` and `structural_alignment_NOT_PIT.csv`.
- The workflow for true source validation lives in Draft [PR #15](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/pull/15), separate from this Agent D code-only Draft PR #12. Do **not** merge to main.

The job retrieves the three exact artifacts from upstream run 43448555468 with GitHub Actions `actions: read`, executes `ci/k37/verify_source_bundles.py` and then runs this module:

```bash
python -B -m unittest discover -s research_core/k3_7/integration/tests -v
python -B research_core/k3_7/integration/verify_and_join.py \
  --input inputs \
  --output integrated
```

The `inputs/` folder must come from the verified GitHub Actions artifact bridge; do not substitute synthetic test fixtures.

## Guardrails and unresolved risks

1. Calendar ordering is **not** evidence of publication or availability when a trade was hypothetically placed. No model, causal claim, official PIT backtest or trading recommendation has been produced.
2. **108** WASDE yield entries have the label `Bushels` despite metric `yield_bushels_per_acre`; verify dimension semantics before promotion.
3. **1,006** NASS rows have a `revision_marker=true`; original historical released edition provenance is not verified.
4. Complete issuance/weekly coverage and sample cross-checks against official printed original reports are outstanding.
5. Original GitHub Actions artifact retention expires **2026-11-27 UTC**. Durable archive work is [Issue #14](https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/issues/14), **not completed**.

**Decision:** technical feasibility PASS, PIT-certified historical backtesting **NO-GO**, pending source/version/time quality evidence.
