#!/usr/bin/env python3
"""Wait until CI has finished for one or more commits, printing a line per poll.

  watch-ci.py <sha>... [--provider github-actions|bitbucket] [--repo owner/name] [--interval 30]
              [--timeout-min 70] [--workspace DIR]

Provider and repo default to the workspace profile's checks.ci block. Run it in the background right after a
push (the Team Lead arms it when the Shipper reports the head SHA): external CI can't wake the agent, so
this one-shot loop is what turns "CI finished" into a notification.

Exit: 0 all green · 1 something failed · 2 timed out · 3 config error.
A transient API error counts as "still pending" for that poll, so a network blip never ends the watch.
"""
import argparse
import os
import pathlib
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ci_state import ConfigError, commit_state, config  # noqa: E402


def load_profile(workspace):
    path = pathlib.Path(workspace) / "profile" / "profile.yaml"
    if not path.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(path.read_text()) or {}
    except ImportError:
        return {}  # without PyYAML, pass --provider and --repo


def describe(sha, state, checks):
    done = sum(1 for _, s in checks if s != "pending")
    failed = [n for n, s in checks if s == "failure"]
    line = f"{sha[:10]} {state}"
    if checks:
        line += f" ({done}/{len(checks)} done)"
    if failed:
        line += " failed: " + ", ".join(failed)
    return line


def main(argv=None, get=None, sleep=time.sleep, clock=time.monotonic):
    ap = argparse.ArgumentParser()
    ap.add_argument("shas", nargs="+")
    ap.add_argument("--provider")
    ap.add_argument("--repo")
    ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--timeout-min", type=float, default=70)
    ap.add_argument("--workspace", default=os.environ.get("AGENT_TEAM_WORKSPACE") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    a = ap.parse_args(argv)

    try:
        cfg = config(load_profile(a.workspace), {"provider": a.provider, "repo": a.repo})
    except ConfigError as e:
        print(f"watch-ci: {e}", file=sys.stderr)
        return 3

    kwargs = {"get": get} if get else {}
    deadline = clock() + a.timeout_min * 60
    while True:
        results = {}
        for sha in a.shas:
            try:
                results[sha] = commit_state(cfg, sha, **kwargs)
            except Exception as e:  # network / auth / API shape: show it, keep watching
                results[sha] = (f"lookup error: {type(e).__name__}: {str(e)[:80]}", [])
        print(time.strftime("%H:%M ") + "  ".join(describe(s, *results[s]) for s in a.shas), flush=True)

        states = {state for state, _ in results.values()}
        if states <= {"success", "failure"}:
            return 1 if "failure" in states else 0
        if clock() >= deadline:
            print("watch-ci: TIMEOUT", flush=True)
            return 2
        sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
