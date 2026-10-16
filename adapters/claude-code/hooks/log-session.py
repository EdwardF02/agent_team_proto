#!/usr/bin/env python3
"""SessionStart / SessionEnd: append a session boundary to the workspace time log. Prints nothing."""
import os
import subprocess
import sys

from _common import read_input, workspace

event = sys.argv[1] if len(sys.argv) > 1 else "session_event"
session = read_input().get("session_id", "")
kit = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
subprocess.run([sys.executable, os.path.join(kit, "scripts", "log-event.py"), event, "-", "--note", session,
                "--workspace", str(workspace())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
