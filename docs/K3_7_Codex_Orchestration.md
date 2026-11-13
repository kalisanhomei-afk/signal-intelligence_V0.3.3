# SIGNAL K3.7 — Codex parallel pilot execution

**Purpose:** accelerate a small historical-data feasibility pilot without increasing research or maintenance risk. This is *not* a new predictive-model release.

## Baselines
- Production/default: `main` — **do not touch**.
- Existing research: `signal-evidence-rebuild` — keep K31–K3.6 intact.
- Orchestration preparation: `codex/k37-orchestration`. Agent tasks should start from an approved orchestration baseline, in **separate workspaces/branches**, not by sharing a writable checkout.
- Scope frozen to 2016, 2020, 2022 historical pilot. Go/no-go decision before 2016–2025 bulk expansion.

## Parallel workstreams (launch A/B/C together)
| Task | Owner paths | Deliverables | Independent gate |
|---|---|---|---|
| A: USDA WASDE release vintage | `research_core/k3_7/wasde/**` | `wasde_vintages.csv` and manifest/rejection audit; parser/tests | Correct release vintages and supply/use unit checks; missing releases explicit |
| B: USDA NASS state crop condition | `research_core/k3_7/nass/**` | `nass_state_weekly.csv` and manifest/rejection audit; parser/tests | State, week, crop conditions; percentages sum to 100; no synthetic filling |
| C: Point-in-time evidence audit | `research_core/k3_7/pit/**` | `pit_evidence_ledger.csv`, evidence classifications, tests | Verified/proxy/unknown kept distinct; no false PIT certification |
| D: Integration and QA (later) | `research_core/k3_7/integration/**` | Cross-module join, validation/coverage summary, tests and report | Use *only* immutable delivered A/B/C outputs; do not rewrite their outputs |

## Common interface
Read `docs/K3_7_Data_Contract.md` before coding. Producer outputs are append-only vintage records with defined units and provenance. Contract changes must be proposed before dependent edits.

## Ready to start
- Each agent gets **one GitHub issue**, one isolated Codex cloud task/worktree, one branch and one PR.
- Read this file plus `AGENTS.md`, locate prior code and fixtures, then work **only** inside your owned directory.
- Each PR includes a concrete reproducibility summary: exact command, tests passed/failed, successful data periods, missing/blocked periods, and evidence limitations.
- Only D is allowed to integrate after A/B/C have submitted stable outputs.

## Acceptance & stop rules
- A/B/C: offline unit tests all pass; pilot files have schema/units/vintage/source identifiers; no unverified PIT promoted to verified.
- D: full pilot reproducible offline; mismatched units, future observations, missing official releases and unknown times produce explicit error/status, not guesswork.
- No public dashboard, no automatic jobs, no model tuning, no trading signals, no performance claims.
- Human checks PRs and results; do not merge to `signal-evidence-rebuild` until acceptance.
- If official sources are inaccessible/legally restricted, return a **source feasibility report** rather than fabricate files.

## Human operations, kept minimal
1. Review/merge the orchestration-only PR or choose `codex/k37-orchestration` as the baseline for first agent runs.
2. In Codex Cloud choose the existing SIGNAL repository and that base branch; launch **three separate tasks** using the issue prompts.
3. Review three PRs and CI/output evidence. Then launch D as a **fourth** integration task.
4. Only after the pilot passes decide whether to expand to ten years.

GitHub Desktop remains available for reviewing/pulling PR changes. Manually copying ZIP files across branches is **not** the default Codex workflow.
