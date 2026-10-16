#!/usr/bin/env python3
"""PreToolUse (Bash): block attempts to skip git hooks. Fix what the hook reports instead."""
import json
import re
import sys

from _common import read_input

cmd = (read_input().get("tool_input") or {}).get("command", "")
patterns = [
    (r"\bgit\b[^\n;|&]*\s--no-verify\b", "--no-verify"),
    (r"\bgit\s+-c\s+core\.hooksPath=", "overriding core.hooksPath"),
    (r"\bHUSKY=0\b", "HUSKY=0"),
]
for pat, what in patterns:
    if re.search(pat, cmd):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": f"Hook bypass ({what}) is forbidden by the agent-team runbook (core §4.6). "
                                        "Fix what the hook reports and retry."}}))
        sys.exit(0)
