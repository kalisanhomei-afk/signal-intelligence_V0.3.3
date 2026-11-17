#!/usr/bin/env python3
"""Project continuity contract: validate durable handoff artifacts. Standard library only."""
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
agent = root / "AGENTS.md"
status = root / "docs/CURRENT_STATUS.md"
errors = []
for path in (agent, status):
    if not path.is_file():
        errors.append("Missing required file: " + str(path.relative_to(root)))
    elif len(path.read_text(encoding="utf-8").strip()) < 250:
        errors.append("Incomplete handoff file: " + str(path.relative_to(root)))

if status.exists():
    data = status.read_text(encoding="utf-8").lower()
    if not any(token in data for token in ("下一步", "next action", "next step")):
        errors.append("CURRENT_STATUS.md must include explicit next action")
    if not any(token in data for token in ("阻塞", "blocker", "未完成")):
        errors.append("CURRENT_STATUS.md must identify blockers")
if agent.exists():
    data = agent.read_text(encoding="utf-8").lower()
    if "current_status.md" not in data:
        errors.append("AGENTS.md must direct agents to CURRENT_STATUS.md")

# Nonblocking continuity notice: do not require changing state file for a
# docs-only PR and never claim that a PR body is an authenticated test result.
base = __import__("os").environ.get("GITHUB_BASE_REF", "")
if base:
    try:
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", "origin/" + base + "...HEAD"],
            cwd=root, text=True, stderr=subprocess.DEVNULL,
        ).splitlines()
        material = [p for p in changed if not p.startswith((".github/", "docs/")) and p != "AGENTS.md"]
        if material and "docs/CURRENT_STATUS.md" not in changed:
            print("NOTICE: Code/content changed without updating docs/CURRENT_STATUS.md. "
                  "PR reviewer must verify status evidence or document why update is unnecessary.")
    except subprocess.CalledProcessError:
        print("NOTICE: could not evaluate changed files against base")

for err in errors:
    print("ERROR: " + err, file=sys.stderr)
if errors:
    sys.exit(1)
print("PASS: AGENTS.md and docs/CURRENT_STATUS.md have minimum handoff contract")
