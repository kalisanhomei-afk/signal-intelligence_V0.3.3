# 視界 SIGNAL — CURRENT_STATUS / cross-chat handoff

Updated: 2026-11-22 Asia/Taipei (R1c source audit). This is a **stacked research-branch handoff index**, not a claim that these drafts were merged to main or forecast outcomes are known.

## Current R1c research gate (latest as of 2026-11-22; supersedes earlier chronological R1c snapshots)
- R0 #26, R1a #27, R1b #28, R1c #29: all **Draft / unmerged**; PR #29 branch `research/global-capital-flow-r1c-capture-pilot-20261122`.
- Antigravity **externally reported** 2/2 one-off official-source downloads (Fed H.6 HTML, Treasury TIC 2020-03-16 ZIP). Actual source bytes are retained **only** in Antigravity local `research_raw/`, not available in this ChatGPT session. Raw body SHA-256 values below are reported from Antigravity verification; no claim of independent local rehash.
- TIC 2020-03-16 ZIP: requested `https://www.treasury.gov/resource-center/data-chart-center/tic/Documents/ticrel_20200316.zip`; final `https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/ticrel_20200316.zip`; reported 2,810,284 B, SHA-256 `4c8b61acb50851f277168b5b897ffd5aba5cab2fb589d44ef74c75890a3b4196`; retrieval completed `2026-11-22T04:34:51.627322Z`; HTTP Last-Modified `2026-02-10 15:47:24 GMT`; 49 members, a member `slt3d_globl.tic` shows ZIP timestamp **2020-04-10**, after nominal 2020-03-16 release. Post-release metadata anomaly is NOT proof of later data revision, but defeats unqualified original-bytes certification.
- TIC member `slt3d_globl.tic` remains `QUARANTINE_TIMESTAMP_POST_RELEASE`; other ZIP members **HISTORICAL_BYTES_NOT_CERTIFIED**. Official source listing and general revisions confirmed; full release vintage, exact UTC, data rights and investable total return label remain UNVERIFIED.
- Document: `docs/research/GLOBAL_CAPITAL_FLOW_R1C_TIC_RECEIPT_PIT_AUDIT_20261122.md`, structured file: `docs/research/global_capital_flow_r1c_tic_receipt_20261122.json`. Original ZIP / receipt not committed to Git.
- R1c `EXTERNAL_CAPTURE_REPORTED`, `SOURCE_PIT_BLOCKED`; Gate 0 = BLOCKED, M0/M1/M2 NOT_RUN, no trading/deployment, no new agent launched.
- **Next**: single-value compare 2020-03-16 original press release vs `npr_history.csv` in the *retained* ZIP, using correct definitions; no re-download, no repeat of existing 8/8 offline tests. If cannot match safely, record BLOCKED rather than invent.

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
- **CORRECTION:** prior 8/8 claim was false: original `tests/test_capture_official_research.py` had SyntaxError (missing closing parenthesis at end of last test). On 2026-11-22, exact GitHub original code and test files were mirrored locally and verified by Git blob SHA; after the one-character syntax fix plus changing a misleading hypothetical TIC URL to an explicit fixture URL, the corrected original-source test suite actually ran: 8/8 PASS, `python -m unittest discover -s tests -p 'test_capture_official_research.py' -v`. This is offline only.
- **Official-network capture state updated:** the ChatGPT container remains DNS/BYTES BLOCKED, but the user-provided Antigravity execution report documents one successful external H.6 historical HTML response capture on 2026-11-22. Raw file resides only in Antigravity local `research_raw/`; it has not been transferred into this verification session. SHA/metadata below are EXTERNALLY_REPORTED_BY_ANTIGRAVITY, not independently rehashed from raw bytes by ChatGPT. No historical-original certification/full PIT/license clearance or investable return data.
- **Do not conflate** hash of bytes downloaded *now* with proof bytes at historical release time. Receipts hard-code `contemporaneous_original_file_certified=false`, `accepted_for_model=false`, `license_status=UNVERIFIED`.
- R1c CODE_DONE / LOCAL_OFFLINE_TEST_PASS_AFTER_FIX / H6_EXTERNAL_CAPTURE_REPORTED (not independently raw-verified here); TIC_ZIP_NOT_CAPTURED; Gate 0 remains BLOCKED. No forecast/backtest/trade/paid resources/agent execution/main merge. Automated PR continuity CI outcome not claimed before checking.
- Next: run exactly two approved-source captures in network-enabled research environment, inspect raw receipts, and decide whether historical versions and rights support full PIT before modeling.

## 2026-11-22 R1c independent test correction and external H.6 evidence intake
- **Defect corrected, reproducibly:** GitHub test blob `1e853b16d6296f6533baa2d9b39a2cd31234a0f4` was matched byte-for-byte in an isolated local mirror. Original suite failed Python syntax parsing at line 103 (`'(' was never closed`). Corrected suite **8/8 PASS locally** on 2026-11-22; mirrored capture script Git blob `80f923346064e3034b4ae3361a7481fb4d359fbc` was unchanged. The earlier "8/8 PASS" asserted before executing was erroneous and is superseded. GitHub auto-continuity CI alone does NOT test the capture helper.
- **Safer test fixture:** ambiguous TIC URL in unit test replaced with explicit non-real fixture URL, so it cannot be treated as a verified Treasury ZIP link. No ZIP URL supplied without official href verification.
- **Antigravity-reported actual capture (NOT independently rehashed by ChatGPT; raw bytes retained in external local environment):** `https://www.federalreserve.gov/releases/h6/20200827/`; HTTP 200; 191,846 bytes; retrieval UTC `2026-11-22T04:22:48.589646Z`–`2026-11-22T04:22:48.760946Z`; raw SHA-256 `6db9a4424239062bbb3a8012cf46fee9dfadd2a8943e2740d87813ff05f0535b`; receipt SHA-256 `855e8f8b19efac12be69a179a5224e8d95a99f6d84b7dc2d6d8bf6264342eb05`; header `Last-Modified: Thu, 03 Sep 2020 20:30:04 GMT`. Source HTML title/release date and `18,327.0` were reportedly verified externally. `Last-Modified` later than publication is a WARNING about byte-level PIT authenticity, *not* proof that historical reported values themselves changed on that date.
- **Governance:** `.gitignore` excludes `research_raw/` to reduce accidental exposure via `git add .` (does not protect already-tracked files; none claimed). No original bytes, raw file or personal data committed. Existing receipt stays `CAPTURED_NOT_PIT_VERIFIED`; `accepted_for_model=false`; `license_status=UNVERIFIED`. Gate 0 remains BLOCKED. No live source values independently inspected in this turn.
- **Next:** verify official Treasury archive ZIP anchor direct href before external TIC capture; do not guess links. Keep original H.6 bytes and receipt on Antigravity device for independent later check. Model work stays blocked.

## Next action
For **global-capital-flow R1c**: compare a single exact 2020-03-16 TIC press-release number with an appropriately mapped member in the existing Antigravity-held ZIP, quarantine the post-release-timestamp member, and retain Gate 0 BLOCKED until data rights and investable total-return/PIT evidence are demonstrated. For the **separate K4/K5** line: retain original independent PIT validation gates and never modify frozen evidence or silently merge drafts.
