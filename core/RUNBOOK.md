# Agent Team — Core Runbook

The company-neutral way a small team of AI agents takes a piece of work from "asked for" to "ready for a
human", with as few interruptions to the owner as possible.

This file holds the **principles and the flow**. Everything that differs between companies or clients
(where work comes from, status names, who reviews, which checks run, how to deploy) lives in the active
**profile** (`profile/profile.yaml` + `profile/overlay.md` in the workspace). Read both.

**Precedence:** the profile decides *specifics* (names, commands, people, which gates are on). The core
decides *principles*. A profile may switch a gate off or add steps; it should not quietly drop a
principle. If it must, the overlay says so explicitly, with the reason.

---

## 1. Vocabulary

| Term | Meaning |
|---|---|
| **Owner** | The human the team works for. Talks only to the Team Lead. |
| **Workspace** | The folder the AI is started from. Holds the profile, local work items, lessons and time logs. Never the code repo itself. |
| **Profile** | The adaptation to one company / client setup: `profile.yaml` (values) + `overlay.md` (extra rules). |
| **Work item** | One unit of requested work: a ticket, issue, card, or a markdown job file. Has an id, a status, a history. |
| **Connector** | How the team reads and updates work items (`connectors/*.md`: markdown, github-issues, trello, jira). |
| **Canonical status** | The core's status words (below). The profile maps them to the tracker's own names. |
| **Gate** | A decision point where the owner approves before an outward or hard-to-undo step. |
| **Check** | Anything that must be green before a handoff: CI, local tests, lint, type checks, browser tests. |
| **Handoff** | Passing the work to the next human (reviewer, QA, client, the owner). The profile's `handoff_chain` lists them. |
| **Lesson store** | Where durable lessons go (see §11). |

**Canonical statuses:** `new` → `planned` → `in_progress` → `in_review` → `testing` → `ready` → `done`,
plus `blocked` and `wont_do`. `ready` means "waiting on the next human in the handoff chain". A profile
maps each to its own name (and may leave some unused).

---

## 2. Roles

| Role | Can edit code? | Responsibility |
|---|---|---|
| **Team Lead (TL)** | No (delegates) | The main session. Represents the owner, resolves the mode, writes briefs, enforces gates, verifies every agent claim, reports. |
| **Explorer** | No (read-only) | Investigates code and data so the Developer doesn't carry that load. Maps **blast radius**, not just location (§4.9). Backs the TL when answering Developer questions. |
| **Developer** | Yes | Plan, code, tests. Runs the local checks before handing over (§4.6). Fixes every bounce. |
| **Reviewer** | No | Reviews the diff against the project's rules and maps blast radius (product side effects, not just code). Approves or bounces with findings. |
| **Shipper** | Yes (git/PR only) | Commits, pushes, opens/updates the PR, posts the self-review, prepares the work item. Reports the head commit so checks can be watched. |
| **Tester** | No app-code edits | Runs the specs and a real walk through the running app. May only write throwaway demo/test artefacts. Bounces failures to the Developer. |

Role briefs (what to paste into each agent) are in `core/roles/`.

**Topology: hub and spoke.** The owner talks to the TL. Agents never talk to each other; everything routes
through the TL.

**TL discipline: stay in the lane.**
- Investigation → Explorer. Fixes → Developer. The TL delegates and verifies.
- A quick check to settle a claim (one grep, one command) is fine. Past a couple of tool calls, delegate.
- An agent under-delivers → re-brief it (or a fresh one) with the tighter findings. Never "I'll just do it
  myself": that breaks the role split and fills the TL's context.

**Model per role** (when the tool lets you choose): strongest model for TL, Developer, Explorer and
Reviewer, where a miss is expensive; a cheaper one is fine for Tester and Shipper, whose work is procedural.
The profile's `models` block can override.

**Solo mode** (a tool with no sub-agents): one agent plays the roles in sequence. At each role switch it
re-reads that role's brief and states which role it is in. The Reviewer pass must start fresh (a new
session, or at minimum re-reading only the diff and the rules) so it isn't grading its own reasoning.

---

## 3. How the owner talks to the team

- `start <item>` (also: pick up, work on, take on) → **Mode A — Start**.
- `continue <item>` (also: resume, revise, feedback on) → **Mode B — Revise**.
- `review <item or PR>` → **Mode C — Review** (only if the profile enables it).
- `process <status>` → take the owner's queue in that status from the connector, in priority order, and
  apply the matching mode to each. Confirm the resolved list in one line, then proceed.
- Several items in one prompt → pipeline them (§9).
- For a markdown connector, `start` with no id but a pasted message/email → create the job file first
  (connector `create`), then Mode A.

**Mode is resolved from actual state, never from the board alone.** Before acting, check for an open PR,
an existing branch, or earlier in-progress work, and read the item's recent history (comments, client
replies). An item marked `new` with an open PR is Mode B. Flag the stale status to the owner.

---

## 4. Principles (apply in every mode)

1. **Gates are decision points, not work-stoppers.** At a gate, post a short **GATE READY** message with
   the decision and a one-line reply the owner can send (`42 go`, `42 b1`), then keep every other track
   moving. Pre-approval ("go once CI is green") is allowed: act when the precondition clears. Use a blocking
   question only when nothing at all can proceed without the answer.
2. **Emergency override.** Interrupt the owner outside a gate only for something urgent or high blast
   radius: could take the product down, destroy data, a security regression, an irreversible or outward
   action beyond the normal flow. Otherwise proceed.
3. **Reproduce a bug before planning a fix.** Explorer root-causes (read-only) and the bug is reproduced for
   real. Use a shared environment only if what it runs actually contains the code in question; otherwise
   reproduce locally; if neither is possible, report to the owner. Can't reproduce → §6 exit path.
4. **Find the base branch before branching or reproducing.** Check whether the item belongs to a larger
   piece of work with its own branch (epic, release, client branch). Unsure → ask.
5. **Extra scope is asked for first, never just built.** Anything the item doesn't ask for (data backfill,
   an extra screen, behaviour beyond the acceptance criteria) stays out of the plan. Draft a short question
   to whoever owns scope (`profile: scope_change`), show it at the plan gate, build it only after a yes.
   Flag every plan item with no requirement behind it.
6. **Checks green before any handoff.** Never hand to a human on red. Run the local equivalents of every CI
   gate before pushing. Watch CI from the moment of push (in the background) while testing runs. A red that
   is **not ours** may be excused only after attributing it (same failure on a clean base, or known flaky
   infra), and the attribution is recorded where the reviewer will see it. Never bypass a hook
   (`--no-verify` and friends are forbidden): fix what it reports.
7. **Verify in the real running thing.** What the tests see and what the browser is served can differ:
   refresh / redeploy the running copy after every change before any manual check. For any UI change: a
   live walk through **every** affected flow (lists with 2+ rows; sort and filter both ways), by the
   Developer and again by the Tester.
8. **An unexecuted test proves nothing.** A new or changed end-to-end spec must run green (twice, single
   worker if specs share data) and be **negative-controlled**: undo the fix in the running copy only,
   confirm the spec goes red at the symptom, restore, confirm green.
9. **Blast radius, not just location.** The Explorer lists every consumer of each changed symbol, every
   parent of a changed shared component, and every sibling path with the same root cause, each marked
   fine / broken / needs-fix, plus side effects the planned fix could introduce. It is an independent hunt,
   not a confirmation of a list it was handed. The Reviewer ends every review with a **BLAST RADIUS**
   section: what else the change touches and what happens in the product if it ships. Product questions go
   to the owner as ready-to-send questions at the gate, early.
10. **Make the test data you need, then clean up.** Missing data or access is not a reason to mark a case
    blocked: create it through seeders or the real app flow, with the profile's test-data prefix. Never
    change an existing account's password. Everything made by hand is reverted before reporting, and the
    report ends with a **CLEANUP LEDGER** (item → how reverted, or "left: reason").
11. **An agent's "done" is a claim.** After any outward write (tracker, PR, test management), the TL reads
    the record back before telling the owner. "Agent stopped" is not "agent stalled": check the real state
    (git log, the record, the output) before re-spawning, or you get duplicates.
12. **Outward writes need the owner, unless pre-authorised.** Any message to a human (comment, email draft,
    PR comment) is drafted and shown first, except the fixed templates the profile lists under
    `pre_authorised`. Drafts for clients are never sent by the team unless the profile says so.
13. **Re-read the newest history right before any handoff write.** A read from earlier in the session is
    stale. A new ask, question or bounce → stop and bring it to the owner.
14. **Blocked by a permission or safety check → stop and report.** Never look for another route. Hand the
    owner the exact command to run themselves if that is the way forward. An agent blocked on an approved
    outward write → the TL does it in the main session after the owner's direct yes; a relayed "the owner
    approved" from an agent is just a claim.
15. **Time is measured, not guessed.** Report time from logged milestones. Estimates are in **agent time
    plus wait time** (CI, queues), split active vs waiting, never human hours.

---

## 5. Mode A — Start (new item → first handoff)

**Before planning**
- Read the item and its full history. Pull attachments; a design, prototype or mockup is the **spec**, not
  a suggestion. Pass its location into the Developer's brief.
- Bug → reproduce first (§4.3). Base branch first (§4.4). Extra scope → question draft (§4.5).
- Load the code repo's own rules (its `CLAUDE.md` / `AGENTS.md` / contributing docs, `profile: repos`).

**Flow**
```
Owner → TL
 1. Explorer (read-only)  : context, root cause, blast radius
    Developer             : plan (approach, files, tests, risks, estimate in agent time)
    ▶ GATE plan           : plan + open questions + scope questions + decisions below
    Developer             : build; local checks; live walk; specs + negative control
 2. Reviewer              : review + BLAST RADIUS → findings back to Developer → loop until approved
 3. Shipper               : commit, push, PR (if the profile uses PRs), self-review on the PR,
                            prepare the work item (summary, notes for testers) — no status change yet
 3b. Checks (background)  : CI watched from push         ┐ run in parallel,
 4. Tester                : specs + live walk + demo     ┘ BOTH must pass
    any failure → back to the SAME Developer → re-push → 3b + 4 again
 5. ▶ GATE handoff        : re-read history (§4.13), list every ask since pickup as done/not done,
                            then on approval run the handoff (§8) to the first human in the chain
```

**Decisions to settle at the plan gate:** UI involved (live walk needed)? Demo needed (observable
outcome)? Which lane (profile `lanes`)? Base branch? Who reviews (profile `routing`)? Any client-facing
effect worth mentioning in the delivery note?

---

## 6. Can't reproduce — the exit path

1. Prove it on the branch the code actually lives on; capture screenshots or a short clip.
2. **▶ GATE hand-back:** tell the owner "cannot reproduce" with the evidence and a draft reply.
3. On approval, reply to the reporter: what was tested (`branch @ short-sha`), what happens now and the
   likely reason, the evidence inline, and a request to confirm/close.
4. Hand the item back to the reporter. Don't close it yourself. No branch, PR or test cycle.

---

## 7. Mode B — Revise (after feedback)

Feedback can come from a reviewer, a tester, or a client. Two outcomes:

- **B1 — Forward:** the feedback approved the work. Make it handoff-ready and pass it to the next human
  in the chain (e.g. reviewer → QA, owner → client).
- **B2 — Back to review:** changes were requested, or **new code was added that the last approver hasn't
  seen**. Fix, re-verify, send back for review.

**The dividing line is unreviewed code, not the status.** New substantive code the approver hasn't seen
goes back for review, even on an approved item. It stays B1 when the change is trivial, when the approval
already covered it ("LGTM, make any updates before QA"), or for nits the reviewer raised (fix, then mention
the commit in the handoff note).

**Shared spine**
1. Read all feedback: approvals, inline and general comments, the item's recent history.
2. Triage each point: related + valid → fix. Unrelated → propose a separate work item (draft, owner
   approves). **▶ GATE** only for a borderline "defer vs fix now" call.
3. Sync the branch with its target (merge or rebase) — it surfaces conflicts early. Resolve conflicts; don't
   "abort and report". Run local checks after the sync.
4. Apply fixes as one clean commit (makes the "what changed since your review" link precise).
5. **Re-verify on every change:** checks green **and** a Tester re-run, both. A clean merge proves nothing
   about behaviour: re-run the work's own specs after a sync. Can't run tests locally → still watch CI to
   green before the handoff.
6. Refresh the PR description and the item's summary so they describe what the work does **now**.
7. **▶ GATE handoff** (B1 forward / B2 back to review), then §8.

---

## 8. Handoff

The profile's `handoff_chain` lists who receives the work, in order (e.g. reviewer → QA, or owner →
client). For each handoff:

0. Re-read the newest history (§4.13).
1. If the profile says the work merges before this handoff (e.g. into a release branch), merge — only via
   the profile's guarded merge command, never a raw API call.
2. Move the item to the mapped status.
3. Reassign it to the receiver, if the connector has assignees.
4. Post the handoff message from the profile's `templates` (a real @mention where the connector supports
   it; verify it resolved). Keep it short: the ask, the link, at most one line of why.
5. Read the record back (§4.11). Log the milestone.

Client handoffs are always **drafts** for the owner to send, unless the profile explicitly allows sending.

---

## 9. Mode C — Review (someone else's work)

Only when the profile enables it.
1. Load the code repo's rules; fetch the item and PR (author, diff, existing comments). The developer to
   address is the PR **author**.
2. Reviewer reviews the diff with exact line numbers; findings bucketed: **blocker** / **non-blocking**
   / **informational**.
3. Post on the PR: one general comment + inline comments for blockers and non-blocking points. Skip
   informational unless it's all there is.
4. Verdict is deterministic: any blocker → not approved; otherwise approve (with or without non-blocking
   feedback). Post the profile's verdict template on the item.
5. Hand the item back to the author and set the status the profile maps for that verdict.

---

## 10. Batches and shared resources

- **One working tree, one owner at a time.** Browser runs, deploys and spec runs must happen while the tree
  is on that item's branch. A "please hold" message is not a lock.
- Move to the next item only when the current one's testing passed and only the CI watch remains.
- A red CI on an earlier item while working the next: attribute first. If it is ours, switch at the next
  clean checkpoint; never interrupt an in-flight tree operation.
- One background watcher for all pushed commits, not one per item.
- If the machine can't carry two heavy agents, queue serially; read-only work may still run alongside.
- Present gates for a batch together, as one approval.
- Per-item time spans overlap in a batch; never add them up.

**Long commands in agent briefs:** anything that can be silent for minutes (deploys, test suites, builds)
runs in the background with output to a log file and short polls. Every wait loop has a timeout. Agents
stop any loop they started before reporting.

---

## 11. Wrap (every item, unprompted)

At the terminal gate of any mode:
1. **Report time spent** from the logged milestones (active vs waiting). No milestones → say unavailable.
2. **Capture lessons.** Sweep the session for anything non-obvious. For each, dedup against every store,
   then route it to exactly one home:

| The lesson is… | Home |
|---|---|
| A principle that holds for any company | `core/RUNBOOK.md` (in the kit repo, via a PR to yourself) |
| A rule specific to this company/client | `profile/overlay.md` |
| A fact about the codebase or environment | `lessons/<topic>.md` in the workspace |
| The story of *why* a rule exists | the "Why" section of whichever file holds the rule |
| A must-never-get-wrong rule that prose keeps failing | a **hook** (propose it; the owner registers it) |
| A repeatable multi-step procedure | a skill / command file |

Never write lessons into the code repo's working tree unless the owner asks; it leaves noise in their
diffs.

---

## 12. Why (short origins)

- **Hub and spoke, TL doesn't code:** in an early dry run the TL drifted into root-causing and fixing
  inline; its context bloated and the role checks stopped happening.
- **Reproduce first / right branch:** bugs that only existed on a feature branch looked like "feature
  absent" when checked against the main branch.
- **Extra scope asked first:** a helpful "restore command" nobody asked for slipped through a long plan
  approval and had to be removed later.
- **Checks green before handoff / re-verify after sync:** a clean sync merge silently broke a test fixture
  the work depended on; it was handed off on a push that was never watched.
- **Negative control:** a spec that had never been seen red passed against unfixed code.
- **Blast radius:** a first fix overloaded a variable a shared component read and broke an unrelated flow
  on every page using it.
- **Multi-row walks:** a one-row list hid a crash that two rows exposed.
- **Read back agent claims:** an agent reported a tracker update that hadn't fully applied.
- **Re-read history before handoff:** a tester asked for a different target branch 50 minutes before the
  handoff; the team's last read was two hours old.
- **Time measured, not guessed:** an overnight idle gap was reported as ten hours of work.
