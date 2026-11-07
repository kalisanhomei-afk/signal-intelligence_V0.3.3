#!/usr/bin/env python3
"""R8-B GitHub push gate. Auditable and fail-closed; never calls OpenAI."""
import os
import pathlib
import subprocess
from dataclasses import dataclass

BRANCH = 'refs/heads/signal-evidence-rebuild'
APPROVAL_PATH = 'rebuild_r8/APPROVE_R8B_ONE_CALL.txt'
APPROVAL_VALUE = 'APPROVE_R8B_ONE_CALL=YES'
ARM_MESSAGE = 'SIGNAL_R8B_APPROVE_ONE_PAID_CALL'

@dataclass
class Check:
    approved: bool
    reason: str


def decide(ref: str, attempt: str, commit_msg: str,
           modified_files: list[str], previous: str, current: str,
           sha_matches: bool = True) -> Check:
    if ref != BRANCH:
        return Check(False, 'wrong_branch')
    if attempt != '1':
        return Check(False, 'rerun_blocked')
    if not sha_matches:
        return Check(False, 'sha_mismatch')
    if commit_msg.strip() != ARM_MESSAGE:
        return Check(False, 'commit_message_mismatch')
    if modified_files != [APPROVAL_PATH]:
        return Check(False, 'must_change_approval_file_only')
    if previous.strip() != 'APPROVE_R8B_ONE_CALL=NO':
        return Check(False, 'not_a_no_to_yes_transition')
    if current.strip() != APPROVAL_VALUE:
        return Check(False, 'approval_not_yes')
    return Check(True, 'all_checks_passed')


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], text=True, stderr=subprocess.DEVNULL)


def run_gate() -> Check:
    # This is evaluated on the exact checked-out push commit. A run attempt >1 cannot spend.
    try:
        head_sha = git('rev-parse', 'HEAD').strip()
        sha_matches = (head_sha == os.getenv('GITHUB_SHA', ''))
        parent_sha = git('rev-parse', 'HEAD^').strip()
        message = git('log', '-1', '--format=%B')
        files = git('diff', '--name-only', parent_sha, head_sha).strip().splitlines()
        previous = git('show', f'{parent_sha}:{APPROVAL_PATH}')
        current = pathlib.Path(APPROVAL_PATH).read_text(encoding='utf-8')
        return decide(os.getenv('GITHUB_REF', ''),
                      os.getenv('GITHUB_RUN_ATTEMPT', ''), message,
                      files, previous, current, sha_matches)
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        return Check(False, 'cannot_prove_git_transition')


def main() -> None:
    c = run_gate()
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
        f.write(f'approved={str(c.approved).lower()}\nreason={c.reason}\n')
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
        f.write('### SIGNAL R8-B Paid Gate\n\n')
        f.write(f'- Approved for exactly one HTTP request: **{str(c.approved).lower()}**\n')
        f.write(f'- Reason: `{c.reason}`\n')
        f.write('- Does not imply a successful AI analysis or content verification.\n')
    print(f'R8-B gate: {c.reason}; approved={c.approved}')

if __name__ == '__main__':
    main()
