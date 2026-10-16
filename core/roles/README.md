# Role briefs

Paste-ready instructions for each agent. The TL builds a brief as:

1. the role file below (verbatim),
2. the **task block**: repo path, branch, work item id + summary, root cause if known, the exact goal,
   verify commands from `profile.yaml: checks`, and what to report,
3. any profile overlay rules tagged for that role.

Briefs are **self-contained**: a fresh agent, not a copy of the TL's conversation (a copy tends to answer
the conversation instead of doing the task). Bounce loops re-brief a fresh Developer with the findings
appended; read-only roles (Explorer, Reviewer) are safe to resume.
