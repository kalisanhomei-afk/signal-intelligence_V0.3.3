# AGENTS.md — SIGNAL research collaboration rules

This repository contains the SIGNAL information/research system. The K3.7 pilot is **research-only**. Follow `docs/K3_7_Codex_Orchestration.md` and `docs/K3_7_Data_Contract.md` when working on K3.7.

## Immutable boundaries
- Preserve existing `research_core/k31/`, `k3_2/` through `k3_6/`, website/Pages, `.github/workflows/`, and `main` unless an explicit issue approves a change.
- Work in an isolated branch or cloud task/worktree based on the agreed K3.7 baseline; do not edit another agent's owned files.
- Never merge into `main`, enable schedules, run live trading, or deploy Pages as part of K3.7.
- This is a **public** repository. Never commit credentials, tokens, private investment records, personal information, or restricted third-party content.

## Research integrity
- Do not invent observations, publication times, missing months or source URLs.
- Distinguish (1) reported publication date, (2) verified public availability time, (3) retrieval time, and (4) forecasting as-of time.
- Scheduled timestamps and inferred availability are **proxies**, never PIT-certified evidence. Missing evidence remains missing.
- Preserve source URL, raw content digest (SHA-256), units, marketing year, vintage and revisions; no silent forward-filling.
- Prevent target leakage. Future WASDE data may be labels only, never features at an earlier as-of.
- Keep observed facts, assumptions, retrospective accounting, forecast evaluation, and trading claims separate.

## Agent ownership (K3.7 pilot)
- Agent A owns `research_core/k3_7/wasde/`.
- Agent B owns `research_core/k3_7/nass/`.
- Agent C owns `research_core/k3_7/pit/`.
- Agent D owns `research_core/k3_7/integration/` and integration-only tests **after** A/B/C submit independent outputs.
- Changes to shared contracts or previous modules require a separate review; do not silently broaden scope.
- Pilot years only: **2016, 2020, 2022**. A ten-year backfill is outside this phase.

## Delivery and verification
1. Inspect the existing K3.3–K3.6 schema and unit conventions before writing code.
2. Implement using Python standard library where feasible; no new dependency without justification and approval.
3. Add deterministic offline fixtures and unit tests; online official-source tests are separate and clearly labeled.
4. Report exact test commands, observed results, input/output files, source gaps, PIT evidence level, and known limitations.
5. Propose changes through a PR targeting the K3.7 integration baseline. Do not self-merge or claim a model has predictive/trading edge.
