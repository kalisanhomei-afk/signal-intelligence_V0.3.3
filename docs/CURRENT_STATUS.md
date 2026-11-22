# 視界 SIGNAL — CURRENT_STATUS / cross-chat handoff

Updated: 2026-11-17 Asia/Taipei. This is a **main-branch handoff index**, not proof that experimental research branches were merged or that forecast outcomes are known.

## Objective
Research official and independent evidence, model causal supply/demand and stock-flow drivers, build timestamped falsifiable hypotheses, and evaluate tradable financial implications only after proper out-of-sample and point-in-time (PIT) tests. Not merely a news aggregator. Favor verifiable forecasts and risk-adjusted decisions.

## Live GitHub snapshot
Repository: https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3
- Main branch has existing source, tests, workflows and older release instructions. Do not equate its README V0.3.3 deployment note to the current research feature state.
- Draft PR #24: https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/pull/24 research overview, joint corn/gas hypothesis cards and a preflight; **not merged**.
- Draft PR #23: https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/pull/23 natural-gas weekly storage hypothesis scout; base `codex/k37-orchestration`, **not merged to main**.
- Draft PR #22: https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/pull/22 corn-stock-surprise hypothesis gate; base `codex/k37-orchestration`, **not merged to main**.
- Draft PR #19: https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/pull/19 K3.8 forward-only USDA capture; base `codex/k37-orchestration`, **not merged to main**.
- Additional historical K3.7 investigation branches/PRs exist. Always check live branch, PR and CI state before claiming completed.
- Current status and actual transaction/deployment claims **must** be verified against concrete evidence; this document does not certify any PIT event or forecast outcome.

## Most important operational gates
1. Maintain immutable source publication UTC, actual retrieval UTC, original raw bytes SHA-256 only where bytes are available, data vintage and pre-event freeze.
2. Forward predictions may NOT consume data first released after the prediction timestamp. No invented future official releases, values or market-consensus estimates.
3. Frozen research preflight ≠ real-world validated prediction ≠ an investment or trading authorization.
4. No trading, financial execution, changes to production secrets, paid resources, or risky deployment without explicit authorization.

## Parallel agent workstreams (planned roles, not claimed running)
- A: official-data capture, rights, PIT and vintage checks.
- B: independent forecasting/hypothesis and falsification tests.
- C: financial implication/risk and portfolio translation, no real trades.
- D: independent source reproducibility, chronology and forward-bias review.

## Every new-chat / agent first step
1. Read this file and root `AGENTS.md`, then inspect the actual target branch and the relevant PRs (#19, #22, #23, #24), issue ledger, tests and workflow results.
2. Respect active evidence/experiment freeze windows, including future scheduled release dates. Do not re-run completed source audits without a specific conflict.
3. Distinguish NOT_STARTED, PLAN, ASSIGNED, RUNNING (must have run ID), CODE_DONE, CI_PASS, PIT_VERIFIED, RELEASED, REAL_WORLD_VALIDATED.
4. Deliver next scoped work in branch/PR, record actual commit and CI evidence; after material work update this one file with source links and precise next blocker. If main is protected, propose a PR and do not claim main updated.
5. Stop retrying the same blocker after two failures; identify root cause/alternate path. Do not expand scope into unrelated modules.


## 2026-11-22 new independent proposal — global money/credit/asset pricing
- Research artifact: `docs/research/GLOBAL_CAPITAL_FLOW_RESEARCH_CHARTER_V0_1.md` (new, documentation-only, **PROPOSAL / NOT_TESTED**).
- Scope: test incremental 1-month U.S. equity excess-return forecasting against historical-average and traditional-finance baselines, not presume asset-market fund flows predict returns.
- Branch: `research/global-capital-flow-charter-v0.1-20261122`; Draft PR #26: https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/pull/26 ; initial charter commit `0f280a9b93dbccdcb32974cdfcd65cfd1334f231` (originated from main `e85f5f12613d19943493707b36112a648f20ee0f`); this line is committed in the branch's subsequent status-sync commit.
- Evidence: literature and official metadata definitions verified via linked public pages; **no source raw-byte harvest, no model runs, no PIT_VERIFIED/ALPHA_PASS, no strategy backtest, no agent execution**.
- CI: PR #26 auto-queued the existing non-deployment `Project continuity` check, Run `44982100255` (queued at first observation); no manual CI trigger or research model test. Follow the GitHub Actions result for current status.
- Gate: R0 CHARTER_WRITTEN; R1 source-feasibility/PIT matrix NOT_STARTED. K3.8/K4/K5 frozen sources and draft forecasts untouched. No main merge, deployment, trade, paid resources, or production setting changes.
- Next authorized action: review charter and prepare R1 read-only source feasibility; later actual data acquisition/forecast code requires a separately scoped change and acceptance.
- Human action: **none for review**; explicit authorization required before merging this PR or running any trade/paid data action.

## 2026-11-22 R1 Global Capital Flow metadata feasibility — dependent draft
- Source document: docs/research/GLOBAL_CAPITAL_FLOW_R1_SOURCE_FEASIBILITY_V0_1.md
- R1a = SOURCE_METADATA_REVIEWED (ten official source families incl. FRED license, time-of-release, revisions and source archive discovery).
- R1b = NOT_STARTED (raw data/vintage samples, legal scope, investable total-return label). Gate 0 = BLOCKED; no raw data SHA, no original capture, no model/backtest/alpha, no Agent launched.
- High-priority change to proposed method: current FRED/ALFRED ToS prohibits use in machine-learning/software development or training and limits API archiving; do not ingest FRED/ALFRED for modeling without separate rights clearance. Prefer original public issuers subject to their own terms.
- Time gate: Fed H.15 posts about 16:15 ET after 16:00 signal cutoff; Treasury TIC posts 16:00 ET with ~1.5 month reference-period lag. Historical CFTC backcast classifications are not contemporary evidence.
- Branch: research/global-capital-flow-r1-feasibility-20261122; dependent Draft PR #27: https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/pull/27 (base is R0 Draft PR #26 branch, NOT main); first R1 research commit c1a91eb35a424bca73a3a08ed426ca122ae780e2. Status sync commit follows this original R1 commit. Neither PR merged nor deployed.
- Next: scoped R1b primary-source archived-version samples plus investable total-return/rights verification. No user action for documentation review; merging or high-risk changes require separate approval.

## 2026-11-22 R1b historic page samples — dependent documentation draft
- R1b evidence: `docs/research/GLOBAL_CAPITAL_FLOW_R1B_HISTORICAL_PIT_SAMPLES_V0_1.md`, machine-readable `docs/research/global_capital_flow_r1b_samples_v0_1.json`.
- Verified via public official historical *web pages* (not original raw files): H.6 2015/2020/2021 release schedule switch, July 2020 SA M2 reported 18,327.0 (Aug 2020 release), 18,328.8 (Feb 2021), and revised to 18,321.5 (Mar 2021); Treasury TIC 2010/2015/2020/2025 actual release dates, including shutdown-delayed 2025-08 data released Nov 18 with Sep data and some revised figures. H.15 2016 release changes and Ken French vintage limitations.
- **R1b status PARTIAL:** historical official WEB_TEXT_VERIFIED, but raw byte acquisition and ZIP content validation **BLOCKED** (container lacks official-source raw download access), no original file SHA-256, no verified full PIT, no license/tradable total returns, no backtests. **Gate 0 BLOCKED**, research predictions NOT_STARTED, no agent launched.
- Source evidence and next step: obtain a minimal sample of actual native official H.6 HTML/XML and Treasury historical release ZIP bytes in a permitted environment; record observed retrieval UTC + original bytes SHA-256. Freeze investable total-return labels and usage rights before R2. FRED/ALFRED training restrictions remain in force.
- Branch: `research/global-capital-flow-r1b-pit-samples-20261122`; Draft PR #28: https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/pull/28 (base Draft PR #27 branch, which in turn depends on unmerged Draft PR #26). Initial R1b evidence commit `2b2be5bdbb5a2566c46e4b39afa643fa2e0a1407`. No main merge, paid action, deployment, code changes, or trading authorized.
- This addendum records a documentation delivery only; any auto PR continuity CI is NOT an investment-model validation.

## 2026-11-22 R1c network-isolated original-byte capture pilot
- Scoped branch: `research/global-capital-flow-r1c-capture-pilot-20261122`, based on PR #28 `6b9776ed837ae8c7f816fb5400df435bf67d8b3d`. Draft PR #29 https://github.com/kalisanhomei-afk/signal-intelligence_V0.3.3/pull/29 ; initial R1c code commit `7ba21a162e21ba416d1b82b5d6491daec4d5220d`; final status-sync commit is the next commit on this branch.
- Deliverables: `scripts/capture_official_research.py`, `tests/test_capture_official_research.py`, `docs/research/GLOBAL_CAPITAL_FLOW_R1C_CAPTURE_RUNBOOK.md`. Stdlib-only one-off official H.6 HTML / TIC ZIP capture, SHA-256 receipts, safe allowlist, no automatic discovery, no raw data in Git.
- **Local off-line evidence:** 8 / 8 unit tests PASS in sandbox (mocked responses, NO official network); exact source file must be run in permitted network environment before any official original-body receipt exists.
- **Actual official network capture: BLOCKED.** This container DNS lookup to federalreserve.gov and home.treasury.gov failed and direct download tool failed. No actual official file bytes, no historical-issue-original hash, no full PIT, no confirmed license or investable return data.
- **Do not conflate** hash of bytes downloaded *now* with proof bytes at historical release time. Receipts hard-code `contemporaneous_original_file_certified=false`, `accepted_for_model=false`, `license_status=UNVERIFIED`.
- R1c CODE_DONE / LOCAL_OFFLINE_TEST_PASS; OFFICIAL_CAPTURE_BLOCKED; Gate 0 remains BLOCKED. No forecast/backtest/trade/paid resources/agent execution/main merge. Automated PR continuity CI outcome not claimed before checking.
- Next: run exactly two approved-source captures in network-enabled research environment, inspect raw receipts, and decide whether historical versions and rights support full PIT before modeling.

## Next action
Review the current research draft PR #24 and the dependent K4/K5 PRs against the correct base branches. Prioritize actual PIT evidence, point-in-time release checks and independent acceptance; do not silently merge or deploy these drafts.
