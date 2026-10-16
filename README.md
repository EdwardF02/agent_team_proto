# Agent Team

A portable way to run a small team of AI coding agents — Team Lead, Explorer, Developer, Reviewer,
Shipper, Tester — that takes a piece of work from "asked for" to "ready for a human" with as few
interruptions to you as possible.

It started as one company's in-house workflow and was split into a **company-neutral core** plus
**profiles** that adapt it to each place you work: a team with tickets, code review and QA, or a solo
freelancer taking jobs by email.

## How it fits together

```
core/          the principles and the flow (modes, gates, handoffs) + role briefs     ← same everywhere
connectors/    where work items live: markdown files, GitHub Issues, Trello, Jira     ← pick one
profiles/      the adaptation: statuses, people, checks, gates on/off, templates       ← one per setup
adapters/      tool wiring (Claude Code reference setup)                               ← or see FOR-AI.md
scripts/       workspace setup, time log, time report
```

A **workspace** is the folder you start your AI in. It gets a copy of one profile plus your own jobs,
lessons and time log. Workspaces live outside this repo, so client and company material never ends up here.

## Quick start (freelance)

```bash
git clone <this repo> ~/agent-team
~/agent-team/scripts/new-workspace.sh ~/freelance freelance
cd ~/freelance
# edit profile/clients.yaml (one entry per client), then start your AI here
```

Then talk to it in plain words:

- `start` + paste a client's email → it creates `jobs/<client>/JOB-1-….md`, plans, and stops for your OK
- `continue JOB-1` + paste the client's reply → it triages the feedback and revises
- `python3 ~/agent-team/scripts/time-report.py --since 2026-10-01 --client acme` → billable time

## The flow in one picture

```
you → Team Lead
  Mode A  Start   : explore → plan ▶GATE → build → review ⟲ → ship → checks ‖ test → ▶GATE → handoff
  Mode B  Revise  : read feedback → triage → sync → fix → re-verify → ▶GATE → forward / back to review
  Mode C  Review  : review someone's PR → post findings → deterministic verdict (optional per profile)
```

Gates are where you decide; everything between them runs on its own. Which gates exist, and who receives
each handoff (reviewer, QA, you, a client), is set by the profile.

## Making a profile for a new place

1. `cp -r profiles/_template profiles/<name>` and fill in `profile.yaml`: connector, status names,
   repos, checks, gates, handoff chain, routing, templates.
2. Put rules that only apply there in `overlay.md`, under the core section they extend.
3. Keep confidential profiles (real people, internal URLs, ids) in a private repo or in the workspace only.

## Using another AI

Point it at **`FOR-AI.md`**. That one file explains the whole structure to an AI and how to adapt it to
whatever tool it runs in (instruction file, sub-agents or solo mode, hooks or manual rules, tracker
access). Claude Code is the reference setup in `adapters/claude-code/`; any other tool can rebuild the
same thing from that description.

## Principles worth stealing even if you use nothing else

- The lead delegates and verifies; it doesn't do the work itself.
- Reproduce a bug before planning a fix.
- Extra scope is asked for, never quietly built.
- Never hand off on a red check; never bypass a hook.
- An unexecuted test proves nothing — and a test never seen failing proves little.
- Map the blast radius, not just the line to change.
- An agent's "done" is a claim until you read the record back.
- Time is measured from logged milestones, not guessed.

## License

MIT — see `LICENSE`.
