#!/usr/bin/env python3
"""PreToolUse: machine-enforce the runbook's "never" rules instead of trusting the prompt.

  1. Password changes: a command that runs a DB client or app console AND sets a password
     (on while profile test_data.never lists "change existing passwords", the default).
  2. Merges: agents never merge a PR while the profile's merge gate is on (default). The owner merges.
  3. Handoff on red: moving an item to the profile's in_review status is blocked while the head commit of
     its branch isn't green in CI (core §4.6, "never hand off on a red check").

Fail-open on our own errors: malformed input or a failed lookup never blocks; (3) then warns instead.
The owner can always run a blocked command themselves.
"""
import json
import os
import re
import subprocess
import sys

from _common import profile, read_input

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(KIT, "scripts"))
from ci_state import ConfigError, commit_state, config  # noqa: E402

RUNS_DB = re.compile(r"\bartisan\s+tinker\b|\brails\s+(?:c|console|runner)\b|\bmanage\.py\s+shell\b|\bphp\s+-r\b"
                     r"|^(?:sudo\s+)?(?:docker\s+(?:compose\s+)?exec\b.*?\s)?(?:mysql|mariadb|psql|sqlite3)\b")
SETS_PASSWORD = re.compile(r"Hash::make|\bbcrypt\s*\(|password_hash\s*\(|\bset_password\s*\(|make_password\s*\("
                           r"|\bupdate\b[^;]*\bset\b[^;]*\bpassword\b", re.I)
CLI_MERGE = re.compile(r"\bgh\s+pr\s+merge\b|\bglab\s+mr\s+merge\b|/pullrequests/\d+/merge\b|/pulls/\d+/merge\b")
MCP_MERGE = re.compile(r"merge_?pull_?request|merge_pr$", re.I)


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": reason + " (agent-team guards.py; the owner can run it themselves.)"}}))
    sys.exit(0)


def warn(msg):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": msg}}))
    sys.exit(0)


def is_on(value, default=True):
    """Profile switches are written on/off, which YAML may have turned into booleans."""
    if value is None:
        return default
    return value is True or str(value).lower() in ("on", "true", "yes")


def _split(cmd):
    """Split on && || ; | newline ( ) OUTSIDE quotes, so a quoted pattern like "a|b" stays one segment."""
    out, cur, q, i = [], [], None, 0
    while i < len(cmd):
        c = cmd[i]
        if q:
            if c == "\\" and q == '"' and i + 1 < len(cmd):
                cur.append(cmd[i:i + 2]); i += 2; continue
            if c == q:
                q = None
            cur.append(c)
        elif c in "'\"":
            q = c; cur.append(c)
        elif c == "\\" and i + 1 < len(cmd):
            cur.append(cmd[i:i + 2]); i += 2; continue
        elif cmd[i:i + 2] in ("&&", "||"):
            out.append("".join(cur)); cur = []; i += 2; continue
        elif c in ";|\n()":
            out.append("".join(cur)); cur = []
        else:
            cur.append(c)
        i += 1
    out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]


def segments(cmd):
    segs = _split(cmd)
    # `bash -c '...'` payloads run as commands too
    for m in re.finditer(r"\b(?:ba|z)?sh\s+-l?c\s+(['\"])(.*?)(?<!\\)\1", cmd, re.S):
        segs += _split(m.group(2))
    return segs


def check_password(cmd, prof):
    never = " ".join((prof.get("test_data") or {}).get("never") or ["change existing passwords"]).lower()
    if "password" not in never:
        return
    # Only when a segment actually RUNS a console / DB client, so a grep or a doc edit that merely
    # mentions Hash::make passes.
    if any(RUNS_DB.search(s) for s in segments(cmd)) and SETS_PASSWORD.search(cmd):
        deny("Never change an existing account's password. If a login fails, check the account exists, then "
             "ask the owner. Test fixtures set passwords in seed code, not through a console.")


def check_merge_cli(cmd, prof):
    if is_on((prof.get("gates") or {}).get("merge")) and CLI_MERGE.search(cmd):
        deny("Merging is an owner gate in this profile. Report the PR as ready to merge instead.")


def branch_heads(repo_path, item):
    """[(branch, sha)] on origin whose name contains the item id as a whole token."""
    out = subprocess.run(["git", "-C", os.path.expanduser(repo_path), "ls-remote", "--heads", "origin"],
                         capture_output=True, text=True, timeout=20, check=True).stdout
    pat = re.compile(rf"(?<![A-Za-z0-9]){re.escape(item)}(?![0-9])", re.I)
    heads = []
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        branch = ref[len("refs/heads/"):]
        if pat.search(branch):
            heads.append((branch, sha))
    return heads


def check_handoff(item, prof):
    repos = prof.get("repos")
    if not isinstance(repos, list):
        warn(f"guards: no repo list in the profile, so CI was NOT checked for {item}'s handoff. Confirm it's green yourself.")
    try:
        cfg = config(prof)
        heads = [(r.get("name", "?"), b, sha) for r in repos if r.get("path") for b, sha in branch_heads(r["path"], item)]
        if not heads:
            warn(f"guards: no pushed branch found for {item}, so CI was NOT checked. Confirm it's green yourself.")
        bad = []
        for repo, branch, sha in heads:
            state, checks = commit_state(cfg, sha)
            if state != "success":
                failing = [n for n, s in checks if s != "success"]
                bad.append(f"{repo}:{branch} @ {sha[:10]} is {state}" + (f" ({', '.join(failing)})" if failing else ""))
    except ConfigError as e:
        warn(f"guards: {e}, so CI was NOT checked for {item}'s handoff. Confirm it's green yourself.")
    except Exception as e:  # git / network / API: never block on our own failure
        warn(f"guards: CI lookup failed ({type(e).__name__}), so it was NOT checked for {item}. Confirm it's green yourself.")
    if bad:
        deny("Handoff needs green CI on the head commit (core §4.6). Not green: " + "; ".join(bad)
             + ". Watch CI to green (scripts/watch-ci.py), fix any red, then hand off.")


def review_status(prof):
    return str((prof.get("statuses") or {}).get("in_review") or "").strip().lower()


def handoff_item(tool, ti, cmd, prof):
    """The item being moved to in_review by this call, or None."""
    target = review_status(prof)
    if not target:
        return None
    if cmd:  # GitHub Issues connector: gh issue edit N --add-label <in_review label>
        m = re.search(r"\bgh\s+issue\s+edit\s+#?(\d+)\b.*--add-label[=\s]+['\"]?([^'\"\s]+)", cmd)
        return m.group(1) if m and m.group(2).lower() == target else None
    if re.search(r"atlassian.*__(transitionJiraIssue|executeWrite)$", tool, re.I):  # Jira connector
        if tool.endswith("executeWrite"):
            if "transition" not in (ti.get("name") or "").lower():
                return None
            ti = ti.get("inputs") or {}
        tid = str(ti.get("transitionId") or (ti.get("transition") or {}).get("id") or "").lower()
        tname = str(ti.get("transitionName") or "").lower()
        if target in (tid, tname):
            return str(ti.get("issueIdOrKey") or "").upper() or None
    return None


def main():
    d = read_input()
    tool, ti = d.get("tool_name") or "", d.get("tool_input") or {}
    prof = profile()
    cmd = (ti.get("command") or "") if tool == "Bash" else ""
    if cmd:
        check_password(cmd, prof)
        check_merge_cli(cmd, prof)
    elif MCP_MERGE.search(tool.rsplit("__", 1)[-1]) and is_on((prof.get("gates") or {}).get("merge")):
        deny("Merging is an owner gate in this profile. Report the PR as ready to merge instead.")
    item = handoff_item(tool, ti, cmd, prof)
    if item:
        check_handoff(item, prof)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass
