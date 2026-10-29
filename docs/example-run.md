# Example run: one job, start to handoff

A freelance job under the `freelance` profile, followed from the client's email to the owner's sign-off.
The conversation is a condensed illustration of how a run reads. **Every terminal block is real output**
from this kit's hooks and scripts; where CI is involved, the CI API's answers were faked (as in
`tests/`), everything else ran for real. Timestamps in the CI lines are trimmed.

---

## 1. The request comes in

```
owner › start  [pastes the client's email]
        "Hi, invoice totals are wrong when a customer uses a discount code on a taxed product.
         Example: order #1042. Can you fix it this week? — Dana, Acme"
```

The Team Lead creates `jobs/acme/JOB-7-invoice-totals.md` from the profile's job template, pastes the
email verbatim under **Request**, and logs the start:

```
python3 ~/agent-team/scripts/log-event.py start JOB-7 --client acme
```

## 2. Explore and reproduce before planning

It's a bug, so the Explorer reproduces it before anyone plans a fix (core §4.3) and maps the blast radius,
not just the line to change (§4.9):

```
Explorer → TL
  Reproduced on local with a copy of order #1042: total 108.90, expected 107.80.
  Cause: discount applied after tax in InvoiceTotals::compute(); the cart applies it before.
  Blast radius: InvoiceTotals is also used by the PDF export and the monthly revenue report.
  The report's past figures would change if it recalculates history — it doesn't (it reads stored totals).
```

## 3. Plan gate: the owner decides, everything else runs on its own

```
TL › owner
  Plan for JOB-7 (invoice totals with discount + tax):
  - Apply the discount before tax, matching the cart. One function, plus tests for 4 combinations.
  - PDF export picks up the fix automatically; stored invoices are not recalculated.
  Question: should existing wrong invoices be corrected? That's outside the request → change-request draft ready.
  OK to build?

owner › ok, build it. skip the old invoices for now
```

The wait for the owner is bracketed (`wait_start` → `wait_end`), so it doesn't count as work.

## 4. Build, and the first guard

The Developer writes the fix and the tests. Lint fails on a long line; it tries to commit around it:

```
Developer › git commit -n -m wip
hook      ✗ Hook bypass (commit -n) is forbidden by the agent-team runbook (core §4.6).
            Fix what the hook reports and retry.
```

It fixes the lint error and commits normally. The Reviewer bounces once (missing test for a 100%
discount), the Developer adds it, the Reviewer approves.

## 5. Ship, watch CI, test, in parallel

The Shipper pushes and reports the head commit. The TL starts the CI watcher in the background; the
Tester runs the specs and walks the invoice screen at the same time.

```
$ python3 scripts/watch-ci.py 4f2c9e1a7b3d
4f2c9e1a7b pending (0/2 done)
4f2c9e1a7b pending (1/2 done)
4f2c9e1a7b failure (2/2 done) failed: e2e
exit 1
```

Exit 1 wakes the TL. Had it tried to hand the job over anyway, the guard would have refused, with the
branch and the failing check named:

```
hook ✗ Handoff needs green CI on the head commit (core §4.6). Not green:
       shop:JOB-7-fix-invoice-totals @ f32dc538c2 is failure (e2e).
       Watch CI to green (scripts/watch-ci.py), fix any red, then hand off.
```

The failure goes back to the **same** Developer: an end-to-end test still expected the old, wrong total.
It updates the expectation, re-pushes, CI goes green, the Tester re-runs and passes.

## 6. Handoff gate

Before handing off, the TL re-reads the job's history and lists every ask since pickup as done / not done,
then sends the owner the profile's `owner_signoff` template:

```
TL › owner
  Ready for your sign-off: JOB-7 Invoice totals with discount + tax
  - What changed: discount now applied before tax, same as the cart
  - See it: local, order #1042 → 107.80
  - Checks: unit ✓ e2e ✓ (CI green on 9b41d07), Tester walk ✓
  - Time so far: 1h30m active
```

The owner asks for one tweak (show the discount line on the PDF). That's Mode B: triage, fix, re-verify
(CI **and** Tester again), then a second handoff. The client's delivery note is a **draft** in the job
file; the owner sends it.

## 7. Time, from logged milestones

```
$ python3 scripts/time-report.py --since 2026-10-20 --client acme
item            client           active     wait     span  last event
JOB-7           acme              1h56m    0h48m    2h44m  wait_start
```

2h44m from start to the last handoff, of which 48 minutes were waits (the owner reading the plan, the
owner reviewing the first handoff), so 1h56m of work: the number that goes on the invoice. The open
`wait_start` at the end is the job waiting for the owner to send the delivery note.
