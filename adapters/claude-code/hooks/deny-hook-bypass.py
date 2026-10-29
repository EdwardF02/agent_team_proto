#!/usr/bin/env python3
"""PreToolUse (Bash): block attempts to skip git hooks. Fix what the hook reports instead.

`git commit -n` is short for --no-verify and is blocked; `git push -n` means --dry-run and is not.
Accepted gap: -n inside a flag cluster (`-an`); matching clusters would misfire on harmless ones.
"""
import json
import re
import sys

from _common import read_input

cmd = (read_input().get("tool_input") or {}).get("command", "")
# A bare -n is only a flag outside quotes: `git commit -m "fix -n handling"` is fine.
unquoted = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", "''", cmd)
patterns = [
    (r"\bgit\b[^\n;|&]*\s--no-verify\b", "--no-verify", cmd),
    (r"\bgit\b[^\n;|&]*?\scommit\b[^\n;|&]*?\s-n(?=\s|$)", "commit -n", unquoted),
    (r"\bgit\s+-c\s+core\.hooksPath=", "overriding core.hooksPath", cmd),
    (r"\bHUSKY=0\b", "HUSKY=0", cmd),
]
for pat, what, text in patterns:
    if re.search(pat, text):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": f"Hook bypass ({what}) is forbidden by the agent-team runbook (core §4.6). "
                                        "Fix what the hook reports and retry."}}))
        sys.exit(0)
