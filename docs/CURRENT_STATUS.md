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

## Next action
Review the current research draft PR #24 and the dependent K4/K5 PRs against the correct base branches. Prioritize actual PIT evidence, point-in-time release checks and independent acceptance; do not silently merge or deploy these drafts.

## 2026-11-26 K5 prospective control update (branch-scoped; not merged)
- Owner-authorized continuation on existing Draft PR #23, branch `codex/k5-natural-gas-scout`: pre-event freeze for EIA weekly release **2026-12-03 15:30 UTC**, week ending **2026-11-27**.
- New immutable prospective control file: `research_core/k5/cases/2026-12-03-eia-frozen-v0-forecast.json`; creation commit `12d408110a546a612e23e11ae45bdbc270064e81`; Git blob `7e78fe165b75dc13662d87b8f53b3172d712fe51`.
- Control forecast = **−24 Bcf**, pure last-official-week persistence from EIA 2026-11-25 release (week ending 2026-11-20: stock 3,858 Bcf, net −24 Bcf). Forecast declared UTC `2026-11-26T03:28:20Z`; independently witnessed by GitHub commit chronology. NOT an AI prediction, no ex-ante consensus, no official baseline raw SHA, no historical first-public verification, not trade eligible.
- Original 2026-11-19 frozen +61 Bcf file still Git blob `bacc82f549fb3bba74142139d89bec94e386d88e` and was not overwritten. EIA 11/19 report post-event +20 Bcf, absolute error 41 Bcf; post-event text check only, original outcome bytes SHA and receipt UTC missing.
- GitHub Issue #14 K3.7 source-archive preservation closed 2026-11-26 with private evidence repository, but historical source initial-public PIT remains UNVERIFIED.
- Existing K4 December 10 WASDE +1,758 million-bushel control remains frozen; no merge, deployment or trading.
- **Verification status:** New K5 file read back at commit `12d4081` and original Nov 19 file blob unchanged. The Dec 3 freeze is protected by nine new fail-closed offline regression tests (`research_core/k5/tests/test_dec03_prospective_control.py`); CI run `45750037290` on test-fix commit `c7f7894367be877729f0dea0e30d39b8fc6f0b6c` completed SUCCESS with **65/65 offline tests**. Earlier CI run `45750012560` failed 2/65 due to a NUL-byte separator bug in the new *test helper*, corrected at `c7f7894` (not a forecast file edit). CI PASS is engineering-only, does NOT certify outcome raw bytes, original EIA first-public instant, market consensus PIT or predictive alpha.
- **Next required gate:** only after 2026-12-03 EIA actual publication, obtain official first observed raw bytes, acquisition UTC, SHA-256, score as a separate post-event record; independently verify contemporaneous pre-release market consensus or leave null. New GitHub CI if run must be reported by its actual run ID; avoid unnecessary manual dispatch.
- **Operator:** no user action required. **AI Agents:** no new Codex/Antigravity agent session or parallel work is claimed running. This is branch-scoped status, not a claim that `main` was updated.

## 2026-11-26 K5 Dec-03 forward official-only scorer (branch-only)
- New independently reviewable, read-only module `research_core/k5/forward_event_score.py` for Dec-03 EIA raw-byte plus receipt scoring; existing Nov-19 evaluator and both frozen forecast JSON files remain unchanged. It refuses cross-event records, forged hashes, bad units, wrong series, premature or reversed capture receipt times, and retrospective trading/PIT promotion.
- New tests `research_core/k5/tests/test_forward_event_score.py`: 16 synthetic/offline positive and adversarial cases passed in isolated local fixture before GitHub submission. Any synthetic -30 Bcf example is NEVER a real Dec-03 result; the pre-event scoring state leaves outcome/score null. A GitHub-hosted CI result still needs to be checked at the actual new commit before claiming CI_PASS.
- Updated scope is engineering readiness only; NO new EIA source raw capture or PIT certification, no consensus, no deployment or trading. Original fixed Nov-19 scorer remains separate and untouched. Verify the next real report after Dec-03 15:30 UTC with authentic observed bytes and receipt.

## 2026-11-26 K5 Dec-03 source acquisition gate (branch-only)
- Added `research_core/k5/eia_dec03_capture.py`: opt-in one-shot official EIA HTTPS fetch after scheduled time, immutable raw JSON + capture receipt + descriptive score, exclusive/no-overwrite outputs. Reuses existing K5.2 HTTP implementation and K5 Dec-03 event scorer. It never schedules new downloads and cannot establish independent historic first-public timestamp.
- Added `research_core/k5/tests/test_dec03_capture.py`: six offline synthetic smoke/adversarial tests, no official Dec-03 outcome or live fetch. Distinguish local code existence from CI outcome by citing latest actual HEAD run.
- 2026-12-03 event remains `FUTURE_SOURCE_PENDING`: frozen V0 -24 Bcf, original Git blob `7e78fe165b75dc13662d87b8f53b3172d712fe51` intact; raw outcome, source SHA, captured UTC, consensus and alpha still null/NO-GO.
- Reviewer gate: before any real official capture, verify the real EIA publication and permitted network. Capture only in isolated K5 PR #23; no merge, paid API, schedule, production deploy or trade. User need not manually upload files.

## 2026-11-26 K5 Dec-03 prospective event: scheduled notification vs real original-byte capture, operational check
- **New material live verification:** EIA's current WNGSR page https://www.eia.gov/naturalgas/storage/ says **Next Release 2026-12-03**; agency calendar https://ir.eia.gov/ngs/schedule.html says normal Thursday **10:30 ET** = **2026-12-03T15:30Z** = **2026-12-03 23:30 Asia/Taipei**, week end 2026-11-27. K5 frozen pre-event control remains **-24 Bcf**, Git blob `7e78fe165b75dc13662d87b8f53b3172d712fe51`, unchanged.
- Reviewed branch-specific workflow `.github/workflows/signal-k5-natural-gas-scout.yml`: its `on` is **pull_request + workflow_dispatch only**, containing offline tests. **NO scheduled EIA raw acquisition or runtime executor**; `research_core/k5/eia_dec03_capture.py` is one-shot opt-in code requiring actual HTTPS and output directory, NOT automatically invoked by that workflow.
- Existing enabled ChatGPT task `SIGNAL 12月 WASDE 共識追蹤` (`6afba952c6e88191884bceee15b21f49`) now has a **verified extra RDATE 2026-12-03 23:45 Asia/Taipei** for early K5 official-source evidence check, plus the previously existing **2026-12-04 08:00** K5 follow-up rule, retaining WASDE 08:00/20:00 twice-daily cadence from 11/30 through 12/10. Read back current task schedule/prompt and enabled=true. Task is a check/reminder, **not proof that original bytes will be captured or K5 script will execute**. Capture at 23:45 is post scheduled release, not guaranteed first-public capture; if raw bytes aren't accessible require `source_raw_sha256=null`, `PIT_UNVERIFIED`, and explicit BLOCKED; neither task authorizes auto-dispatch of Github Actions.
- Prior PR #23 K5 87/87 code CI `45752189811` **SUCCESS** confirmed again via existing GitHub record; no CI rerun. New code, official result or model score are **not** produced; present as `SCHEDULE_CONFIRMED`, `CAPTURE_EXECUTOR_NOT_DEPLOYED`, `OUTCOME_PENDING`.
- No merge, raw-data upload, market order, deployment or paid work. Next after actual EIA publication: establish real network availability/permission in isolated environment, acquire and hash original bytes if possible, preserve actual UTC receipt, score against immutable forecast, independently evaluate PIT limitations and market consensus. Owner manual step: none at present.
