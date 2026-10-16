"""Shared helpers for the kit's Claude Code hooks. Standard library only; PyYAML is optional."""
import json
import os
import pathlib
import re
import sys

AGENT_REPORT_MARKERS = ("<task-notification>", "<agent-message", "[Subagent hand-back]")


def read_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def workspace():
    return pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("AGENT_TEAM_WORKSPACE") or os.getcwd())


def profile():
    """Return the workspace profile as a dict, or {} if missing/unreadable."""
    path = workspace() / "profile" / "profile.yaml"
    if not path.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(path.read_text()) or {}
    except Exception:
        # Fallback: pull the one scalar the hooks need without a YAML parser.
        m = re.search(r"^\s*id_pattern:\s*['\"]?(.+?)['\"]?\s*(#.*)?$", path.read_text(), re.M)
        return {"work_items": {"id_pattern": m.group(1)}} if m else {}
