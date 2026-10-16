---
name: team
description: Run the agent team on a work item — start, continue/revise, review, or process a status queue. Entry point that loads the kit's core runbook and this workspace's profile.
user-invocable: true
---

# Team

$ARGUMENTS = what the owner asked, e.g. `start JOB-3`, `continue #42`, `review ABC-12`, `process ready`,
or `start` followed by a pasted email/chat message.

1. Read `./AGENTS.md` for the kit path, then read, in order: `<kit>/core/RUNBOOK.md`,
   `./profile/profile.yaml`, `./profile/overlay.md`, and `<kit>/connectors/<connector>.md`.
2. Resolve the mode from the item's **actual** state (core §3): open PR, branch, history. Check the mode is
   enabled in the profile's `modes`.
3. Re-read that mode's section in the runbook and the overlay, then follow every step in order. You are the
   Team Lead: brief agents with `<kit>/core/roles/*.md`; don't do their work yourself.
4. Log milestones with `python3 <kit>/scripts/log-event.py <event> <id> [--client <c>]`
   (`start`, `revise`, `review`, `gate_plan`, `handoff`, `wait_start`, `wait_end`, `done`).
5. End with the Wrap (core §11).
