#!/usr/bin/env python3
"""Keep the time log's wait brackets honest, so time-report.py's ACTIVE column means something.

ACTIVE = an agent is working (CI running alongside an agent counts). CI running alone, or waiting on the
owner, is a WAIT and must sit between wait_start and wait_end.

  Stop:              open items with no agent working and no open wait → block once and ask the Team Lead
                     to log wait_start (saying whether a CI watch is still running or it's simply idle).
  PreToolUse(Agent): spawning an agent ends the wait of the item its brief is about → wait_end (silent).

"The item a brief is about" = the FIRST item id in it. Briefs mention other items too (related work, the
previous branch), and closing every mentioned item's wait would log time for work nobody did.
Fail-safe: any error → exit 0 with no output.
"""
import glob
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

from _common import profile, read_input, workspace

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LOG_EVENT = os.path.join(KIT, "scripts", "log-event.py")
ACTIVE_WINDOW = 180  # seconds since a sub-agent transcript was last written
START_EVENTS = {"start", "revise", "review"}
END_EVENTS = {"handoff", "done"}
# Claude Code keeps each running sub-agent's transcript here (symlinks to the real files).
AGENT_OUTPUTS = "/tmp/claude-*/*/*/tasks/a*.output"


def id_regex():
    pat = (profile().get("work_items") or {}).get("id_pattern") or r"[A-Z][A-Z0-9]+-\d+"
    return re.compile(rf"\b(?:{pat})\b", re.I)


def subject_item(text, rx):
    m = rx.search(text or "")
    return m.group(0).upper() if m else None


def item_state():
    """{item: {'open': bool, 'waiting': bool}} from today's time log."""
    path = workspace() / "timelog" / (datetime.now().strftime("%Y-%m-%d") + ".jsonl")
    state = {}
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return state
    for line in lines:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        item, e = (ev.get("item") or "").upper(), ev.get("event")
        if not item or item == "-":
            continue
        s = state.setdefault(item, {"open": False, "waiting": False})
        if e in START_EVENTS:
            s["open"] = True
        elif e in END_EVENTS:
            s["open"], s["waiting"] = False, False
        elif e == "wait_start":
            s["waiting"] = True
        elif e == "wait_end":
            s["waiting"] = False
    return state


def waiting_on_tool(path):
    """True if the transcript ends on a tool call still awaiting its result.

    An agent blocked on a long test run writes nothing for many minutes, so file age alone would call
    it finished. A finished agent ends on the result of its hand-back instead.
    """
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 65536))
            last = fh.read().splitlines()[-1]
        msg = json.loads(last).get("message") or {}
        content = msg.get("content")
        return msg.get("role") == "assistant" and isinstance(content, list) and any(
            c.get("type") == "tool_use" for c in content)
    except Exception:
        return False


def busy_items(rx):
    """Items named in the briefs of live agents; unkeyed=True if a live agent names none."""
    now, items, unkeyed = time.time(), set(), False
    for f in glob.glob(AGENT_OUTPUTS):
        try:
            if now - os.path.getmtime(f) > ACTIVE_WINDOW and not waiting_on_tool(f):
                continue
            with open(f) as fh:
                head = fh.read(20000)
        except OSError:
            continue
        item = subject_item(head, rx)
        if item:
            items.add(item)
        else:
            unkeyed = True
    return items, unkeyed


def ci_watch_running():
    try:
        return bool(subprocess.run(["pgrep", "-f", "watch-ci[.]py"], capture_output=True, text=True).stdout.strip())
    except Exception:
        return False


def log(event, item):
    subprocess.run([sys.executable, LOG_EVENT, event, item, "--workspace", str(workspace())], capture_output=True)


def on_stop(d):
    if d.get("stop_hook_active"):
        return
    open_items = sorted(i for i, s in item_state().items() if s["open"] and not s["waiting"])
    if not open_items:
        return
    busy, unkeyed = busy_items(id_regex())
    if unkeyed:
        return  # an agent with no item id is running: can't tell, don't nag
    idle = [i for i in open_items if i not in busy]
    if not idle:
        return
    why = ("a CI watch is still running with no agent alongside" if ci_watch_running()
           else "no agent or CI is running (waiting on the owner, or idle)")
    cmds = "; ".join(f"python3 {LOG_EVENT} wait_start {i}" for i in idle)
    print(json.dumps({"decision": "block", "reason": (
        f"Time log: {why} for {', '.join(idle)}, and no wait is open. That time is a WAIT, not active. "
        f"Log it now: {cmds}. Skip only if an agent for that item is genuinely still running.")}))


def on_agent_spawn(d):
    ti = d.get("tool_input") or {}
    rx = id_regex()
    item = subject_item(ti.get("prompt"), rx) or subject_item(ti.get("description"), rx)
    if item and item_state().get(item, {}).get("waiting"):
        log("wait_end", item)


def main():
    d = read_input()
    ev = d.get("hook_event_name")
    if ev == "Stop":
        on_stop(d)
    elif ev == "PreToolUse" and d.get("tool_name") == "Agent":
        on_agent_spawn(d)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
