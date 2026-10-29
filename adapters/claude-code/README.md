# Claude Code adapter

Claude Code has every capability the kit uses: sub-agents, hooks, skills, background commands.

## What `scripts/new-workspace.sh` sets up
- `CLAUDE.md` → imports `AGENTS.md` (`@AGENTS.md`).
- `.claude/skills/team` → symlink to this folder's `skills/team` (the `/team` entry skill).
- `.claude/settings.json` from `settings.example.json`, with the kit path filled in:
  - `reread-runbook.py` (UserPromptSubmit) — on a mode request, reminds the TL to re-read the runbook
    section and the overlay before acting.
  - `deny-hook-bypass.py` (PreToolUse, Bash) — blocks `--no-verify`, `commit -n` and other hook bypasses.
  - `guards.py` (PreToolUse, Bash + MCP) — no password changes through a console or DB client; no agent
    merges while the profile's merge gate is on; no move to `in_review` while the branch head's CI isn't
    green (looks the branch up with `git ls-remote`, CI through `scripts/ci_state.py`).
  - `account-guard.py` (PreToolUse, Playwright MCP) — on the local app, logins only with
    `test_data.login_prefix` accounts. Off when that key is unset.
  - `wait-bracket.py` (Stop + PreToolUse Agent) — asks the TL to log `wait_start` when nothing is working
    on an open item, and logs `wait_end` when an agent is spawned for it.
  - `log-session.py` (SessionStart / SessionEnd) — session boundaries for the time log.

Every guard fails open: if its own lookup breaks it warns instead of blocking, and the owner can always
run a blocked command themselves. Tests: `python3 -m unittest discover -s tests` from the kit root.

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
`checks.ci.watch` command in the background so it is woken when CI finishes. For GitHub Actions or
Bitbucket Pipelines that is `scripts/watch-ci.py <sha>…` (exit 0 green, 1 red, 2 timeout).

## Adding a profile-specific hook
Put it in `<workspace>/.claude/hooks/` and register it in the workspace's `.claude/settings.json`.
Company-specific guards (e.g. "never run X as root", "only merge via the guard script") belong there, not
in the kit.
