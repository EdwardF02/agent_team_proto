# For an AI reading this repo

You've been pointed at this repo so you can run an agent-team workflow, or adapt it to the tool you are
running in. This file explains the whole structure. Read it, then read the files it names. You do not need
any other setup guide.

## What this is

A workflow for a small team of AI agents working for one human (the **owner**). The main session is the
**Team Lead**. It delegates to an Explorer, a Developer, a Reviewer, a Shipper and a Tester, and only stops
for the owner at **gates** (decision points). The rules are tool-neutral Markdown. Claude Code is the
reference implementation; everything it does can be done another way.

## The map

| Path | What it is | Do you need it? |
|---|---|---|
| `core/RUNBOOK.md` | The rules: vocabulary, roles, principles, Modes A/B/C, gates, handoff, batching, wrap. | **Always.** This is the workflow. |
| `core/roles/*.md` | One brief per role. Paste it into the agent (or into your own head, in solo mode) when that role starts. | Always. |
| `connectors/*.md` | How to list / read / create / set status / assign / comment / attach work items in markdown files, GitHub Issues, Trello or Jira. | The one the profile names. |
| `profiles/<name>/profile.yaml` | The values for one setup: tracker, status names, repos, checks, gates on/off, who receives handoffs, message templates. | The active one. |
| `profiles/<name>/overlay.md` | Extra rules for that setup, organised by runbook section number. | The active one. |
| `profiles/_template/` | A blank, commented profile to copy. | When making a new profile. |
| `adapters/claude-code/` | The Claude Code wiring: an entry skill, hooks, settings. | Read it as an **example** of what to build in your tool. |
| `adapters/generic/AGENTS.workspace.md` | The instruction file a new workspace gets. | Used by the setup script. |
| `scripts/` | `new-workspace.sh` (create a workspace), `log-event.py` + `time-report.py` (time log). | Use them if you can run shell commands. |

**Workspace** = the folder the owner starts you in. It holds `profile/` (a copy of one profile), `jobs/`
(markdown work items), `lessons/`, `timelog/`, and an `AGENTS.md` pointing back to this kit. Client and
company material lives only there, never in this repo.

## How to adapt it to your tool

Work through these in order. For each step, tell the owner what you did.

1. **Instruction file.** Find the file your tool loads automatically for a project (often `AGENTS.md`;
   some tools use their own name). Make the workspace's `AGENTS.md` reach you through it: rename, copy or
   import. If your tool loads nothing automatically, ask the owner to start each session with "read
   AGENTS.md first".
2. **Roles.** If your tool can start sub-agents, map each role to one: read-only roles (Explorer,
   Reviewer) get read-only agents where possible. Each brief is the role file plus a self-contained task
   block (`core/roles/README.md`). If your tool cannot start sub-agents, use **solo mode** (runbook §2):
   play each role in turn, re-read its brief at each switch, and do the Reviewer pass fresh.
3. **Entry command.** If your tool supports custom commands or skills, recreate
   `adapters/claude-code/skills/team/SKILL.md` in its format (`/team start JOB-3`). Otherwise the owner
   types plain requests ("start JOB-3") and `AGENTS.md` routes them.
4. **Hard rules.** `adapters/claude-code/hooks/` enforces three things: block git-hook bypass
   (`--no-verify`), remind the Team Lead to re-read the runbook before a mode action, and log session
   start/end. If your tool can run a script before a command or prompt, port them (they read JSON on stdin;
   only the wiring differs). If not, treat them as rules you follow yourself and keep the owner's gates on.
5. **Work items.** Use the connector the profile names. If your tool has a native integration for that
   tracker (an MCP server, a plugin), use it for the same seven operations. If nothing is available, use
   the `markdown` connector: it needs only file access.
6. **Background work.** The runbook watches CI in the background while testing runs. If your tool can't
   run background commands, check CI at the handoff gate instead. Never skip the check.
7. **Model choice.** `profile.yaml: models` marks which roles deserve the strongest model. Apply it if your
   tool lets you choose per agent; otherwise ignore it.

Write anything tool-specific you build into `adapters/<your-tool>/` with a short README, so the next
session (or the next AI) finds it.

## What you may change, and what you may not

- **Change freely:** profile values, overlay rules, connector details, adapter wiring, message templates.
- **Keep:** the principles in runbook §4 and the gate/handoff structure. A profile may switch a gate off,
  but say so in its overlay with the reason. Do not quietly drop a principle because your tool makes it
  inconvenient: replace the enforcement with a manual step instead.
- **Never:** put company or client details (names, people, URLs, ids, credentials) into `core/`,
  `connectors/` or `adapters/`. They go in a profile or the workspace.

## Starting a session (once adapted)

1. Read `core/RUNBOOK.md`, the workspace's `profile/profile.yaml` and `profile/overlay.md`, and the named
   connector.
2. Wait for the owner's request (`start`, `continue`, `review`, `process`).
3. Resolve the mode from the item's actual state, re-read that section, and follow it step by step.

## Prompt the owner can paste into any AI

> Read `FOR-AI.md` in `<path to this repo>` and adapt the agent team to this tool. My workspace is
> `<path>` with the `<profile>` profile. Tell me what you mapped, what you could not support, and what
> you'll do instead.
