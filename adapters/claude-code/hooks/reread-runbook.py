#!/usr/bin/env python3
"""UserPromptSubmit: when the owner asks for a mode action on a work item, remind the Team Lead to re-read
the runbook section and the profile overlay before acting (never run a mode from memory)."""
import re
import sys

from _common import AGENT_REPORT_MARKERS, profile, read_input

prompt = read_input().get("prompt", "")
if not prompt or any(m in prompt for m in AGENT_REPORT_MARKERS):
    sys.exit(0)

id_pattern = (profile().get("work_items") or {}).get("id_pattern") or r"[A-Z][A-Z0-9]+-\d+"
verb = re.search(r"\b(pick(\s+up)?|start|work\s+on|take\s+(on|over)|continue|resume|revise|review|process)\b", prompt, re.I)
target = re.search(rf"({id_pattern}|#\d+|\b(new|ready|in[ -]?review|in[ -]?progress|to[ -]?do|my\s+queue)\b)", prompt, re.I)
if verb and target:
    print("[agent-team] Before acting: re-read the core RUNBOOK section for this mode and ./profile/overlay.md. "
          "Resolve the mode from the item's actual state (PR, branch, history). Follow every step in order; "
          "checks green + Tester pass before ANY handoff.")
