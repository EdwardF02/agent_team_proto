# Claude Code adapter

Claude Code has every capability the kit uses: sub-agents, hooks, skills, background commands.

## What `scripts/new-workspace.sh` sets up
- `CLAUDE.md` → imports `AGENTS.md` (`@AGENTS.md`).
- `.claude/skills/team` → symlink to this folder's `skills/team` (the `/team` entry skill).
- `.claude/settings.json` from `settings.example.json`, with the kit path filled in:
  - `reread-runbook.py` (UserPromptSubmit) — on a mode request, reminds the TL to re-read the runbook
    section and the overlay before acting.
  - `deny-hook-bypass.py` (PreToolUse, Bash) — blocks `--no-verify` and other hook bypasses.
  - `log-session.py` (SessionStart / SessionEnd) — session boundaries for the time log.

## Roles → sub-agent types
| Role | Spawn as |
|---|---|
| Explorer | `Explore` (read-only) |
| Developer | `general-purpose`, fresh, self-contained brief (not `fork`) |
| Reviewer | `general-purpose` with the reviewer brief (or your own read-only review agent) |
| Shipper | `general-purpose`, fresh |
| Tester | `general-purpose` with the tester brief |

Pass `model` on every spawn per the profile's `models` block (`strongest` → your top model, `fast` → a
cheaper one). Long commands in briefs use `run_in_background`. CI watching: the TL runs the profile's
`checks.ci.watch` command in the background so it is woken when CI finishes.

## Adding a profile-specific hook
Put it in `<workspace>/.claude/hooks/` and register it in the workspace's `.claude/settings.json`.
Company-specific guards (e.g. "never run X as root", "only merge via the guard script") belong there, not
in the kit.
