# SIGNAL AI / Codex Agent contract

## First action — mandatory
Read `docs/CURRENT_STATUS.md` and check current GitHub PRs, branch ancestry, CI, source evidence and timestamps before making claims, asking for previous artifacts or writing any code. Main is not necessarily the branch with current research.

## Evidence integrity
- Official observed values, historical reconstructions, synthetic fixtures, forward predictions, analyst estimates and inferred assumptions must be labeled separately.
- Enforce point-in-time chronology: never use post-event data in pre-event hypotheses. Preserve original publication time, retrieval time, data vintage, and raw-file SHA-256 only when genuinely available.
- No invented PIT passes, future USDA/EIA outcomes, CI runs, agent executions or market returns.
- Don't conflate code or CI passes with valid market predictions or approved investment decisions.

## Execution contract
- Work on scoped branches and create reviewable PRs. Keep current hypothesis and source-validation gates intact.
- Distinguish PLAN / ASSIGNED / RUNNING (with concrete task or run id) / CODE_DONE / CI_PASS / PIT_VERIFIED / RESEARCH_VALIDATED / DEPLOYED.
- Prefer parallel independent agents for data provenance, model logic, portfolio/risk assessment and adversarial QA, without parallel writes to identical files.
- Do not merge unapproved research code into main, deploy, trade, expose secrets, access prohibited source content, or initiate paid resources without authorization.
- Do not repeat completed audits unless real timestamped evidence conflicts. If blocked twice on the same step, investigate a different technical approach instead of repeating it.

## Last action — mandatory
After real work update the existing `docs/CURRENT_STATUS.md` with branch, PR, commit, automated and live evidence, unresolved blockers, next step, and manual intervention requirement. If unable to write main, open a branch PR and report the precise limitation. Never assert a status update happened without a commit.
