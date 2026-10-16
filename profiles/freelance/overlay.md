# Freelance — overlay

One person, several clients, no QA team, no human code reviewer. Work arrives by email or chat.

## §3 Talking to the team — additions
- `start` + a pasted email/chat → the TL creates the job file (client from the sender, or ask), pastes the
  message under `## Request`, then runs Mode A.
- `continue JOB-n` + a pasted client reply → append the reply to the job's History first, then Mode B.
- `invoice <client> [period]` → summarise billable time per job from the timelog (no prices unless
  `rate` is set in clients.yaml; the owner sets prices, the team never quotes them).

## §4 Principles — additions
- **Client separation.** One client per session or batch. Never copy code, data, names or credentials
  from one client's repo or jobs into another's. Secrets stay in env vars.
- **No human reviewer → the Reviewer agent is mandatory on every change**, and on anything touching auth,
  payments or personal data, run a second independent review (fresh session, ideally a different model).
- **Agreed scope is the contract.** `## Agreed scope` empty → the plan gate includes a draft "confirming
  what we'll do" note to the client. Anything outside it → change request (template `change_request`),
  never built before the client says yes. The team writes `{time_or_cost_placeholder}` for the owner to
  fill; it never invents a price.
- **Production belongs to the client.** No production deploy, data change or DNS/hosting change without
  the owner's yes for that specific action, every time.
- **No CI is normal.** When a client repo has no CI, the local checks in clients.yaml are the gate. If it
  has none listed, the Developer runs at least build + tests and says what was run.

## §5 Mode A — additions
- Plan gate also shows: does the plan fit the agreed scope / quote? What will the client see?
- The Tester is still an agent and still required. Only the human QA step is gone.

## §8 Handoff — additions
- First handoff = **owner sign-off**: the TL sends the `owner_signoff` summary with a way to see it
  (running URL, screenshots or a short demo).
- Second = **client delivery**: the TL writes the `client_delivery` draft into the job's `## Delivery`.
  Plain words, no jargon, no internal details (branches, agents, tools). The owner sends it.
- After the owner says "sent", set status `with-client` and log the milestone.

## §11 Wrap — additions
- Time goes to the timelog tagged with client and job (billable).
- Lessons about a client's codebase → `lessons/<client>.md`; never into the client's repo unless the
  owner asks.

## Why
- Change requests in writing protect both sides: a "small extra" built unasked is unpaid work and can
  break something the client didn't agree to.
- With no other human reviewing, the agent reviewer plus the owner's sign-off are the only safety net, so
  neither is optional.
