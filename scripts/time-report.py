#!/usr/bin/env python3
"""Summarise time per work item from the workspace time log.

  time-report.py [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--client C] [--workspace DIR]

Per item: span = first → last logged event; waits = wait_start → wait_end intervals (an unclosed wait runs
to the next event of that item); ACTIVE = span − waits. Spans of items worked in parallel overlap, so never
add them up as effort. Defaults to today.
"""
import argparse
import datetime
import json
import os
import pathlib
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("--since")
ap.add_argument("--until")
ap.add_argument("--client")
ap.add_argument("--workspace", default=os.environ.get("AGENT_TEAM_WORKSPACE") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
a = ap.parse_args()

today = datetime.date.today().isoformat()
since, until = a.since or today, a.until or a.since or today
rows = []
for f in sorted((pathlib.Path(a.workspace) / "timelog").glob("*.jsonl")):
    if since <= f.stem <= until:
        for line in f.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass

items = defaultdict(list)
for r in rows:
    if r.get("item", "-") != "-" and (not a.client or r.get("client") == a.client):
        items[r["item"]].append(r)


def fmt(sec):
    m = int(sec // 60)
    return f"{m // 60}h{m % 60:02d}m"


if not items:
    print(f"No item events between {since} and {until}.")
    raise SystemExit
print(f"{'item':<16}{'client':<14}{'active':>9}{'wait':>9}{'span':>9}  last event")
for item, evs in sorted(items.items()):
    evs.sort(key=lambda r: r["ts"])
    t = [datetime.datetime.fromisoformat(r["ts"]) for r in evs]
    span = (t[-1] - t[0]).total_seconds()
    wait, open_at = 0.0, None
    for r, ts in zip(evs, t):
        if open_at is not None and r["event"] != "wait_start":
            wait += (ts - open_at).total_seconds()
            open_at = None
        if r["event"] == "wait_start" and open_at is None:
            open_at = ts
    client = next((r["client"] for r in evs if r.get("client")), "")
    print(f"{item:<16}{client:<14}{fmt(span - wait):>9}{fmt(wait):>9}{fmt(span):>9}  {evs[-1]['event']}")
