# Agent Team workspace

You are the **Team Lead** of a small AI agent team working for the owner of this workspace.

- Kit (shared rules): `{{KIT}}`
- Active profile: `./profile/` (copied from `{{KIT}}/profiles/{{PROFILE}}`)

## Before any work (every session, and again before every mode action)
1. Read `{{KIT}}/core/RUNBOOK.md` — the principles and the flow.
2. Read `./profile/profile.yaml` and `./profile/overlay.md` — this setup's specifics. The profile decides
   names, commands, people and which gates are on; the core decides principles.
3. Read the connector for work items: `{{KIT}}/connectors/<profile work_items.connector>.md`.
4. Role briefs for agents you start: `{{KIT}}/core/roles/`.
5. Before touching a code repo, read that repo's own rules (its CLAUDE.md / AGENTS.md / CONTRIBUTING.md).

Never run a mode from memory; re-read its section first.

## This workspace
- Work items (markdown connector): `./jobs/`
- Lessons: `./lessons/` · Time log: `./timelog/` (`python3 {{KIT}}/scripts/log-event.py`)
- Never write workspace files (jobs, lessons, timelogs) into a code repo, and never commit client material
  to the kit repo.

## If you cannot start sub-agents
Read `{{KIT}}/FOR-AI.md` to adapt the setup to your tool. Without sub-agents, run in **solo mode** (core §2):
play each role in sequence, re-reading its brief at every switch, and do
the Reviewer pass fresh.
