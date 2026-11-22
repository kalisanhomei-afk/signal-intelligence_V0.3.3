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

## Next action
Review the current research draft PR #24 and the dependent K4/K5 PRs against the correct base branches. Prioritize actual PIT evidence, point-in-time release checks and independent acceptance; do not silently merge or deploy these drafts.
