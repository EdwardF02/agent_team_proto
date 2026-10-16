#!/usr/bin/env python3
"""Append a milestone to the workspace time log: <workspace>/timelog/YYYY-MM-DD.jsonl

  log-event.py <event> <item-id> [--client C] [--note TEXT] [--workspace DIR]

Events: start, revise, review, gate_plan, handoff, wait_start, wait_end, done (any word is accepted).
Use item-id "-" for events not tied to an item (session_start / session_end).
"""
import argparse
import datetime
import json
import os
import pathlib

ap = argparse.ArgumentParser()
ap.add_argument("event")
ap.add_argument("item")
ap.add_argument("--client", default="")
ap.add_argument("--note", default="")
ap.add_argument("--workspace", default=os.environ.get("AGENT_TEAM_WORKSPACE") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
a = ap.parse_args()

now = datetime.datetime.now().astimezone()
logdir = pathlib.Path(a.workspace) / "timelog"
logdir.mkdir(parents=True, exist_ok=True)
row = {"ts": now.isoformat(timespec="seconds"), "event": a.event, "item": a.item}
if a.client:
    row["client"] = a.client
if a.note:
    row["note"] = a.note
with open(logdir / f"{now:%Y-%m-%d}.jsonl", "a") as f:
    f.write(json.dumps(row) + "\n")
