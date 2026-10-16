# Connectors

A connector tells the team how to do seven things with work items. The core runbook only ever asks for
these operations; each connector file says how.

| Operation | Used for |
|---|---|
| `list(status)` | `process <status>` batches, finding the owner's queue |
| `read(id)` | the item, its full history (comments / replies), attachments |
| `create(text)` | turning a pasted message/email into an item; follow-up items |
| `set_status(id, canonical)` | moves at gates (mapped through `profile.yaml: statuses`) |
| `assign(id, who)` | handoffs (no-op if the connector has no assignees) |
| `comment(id, text, mention?)` | handoff messages, questions, verdicts |
| `attach(id, file)` | demos, evidence |

Pick one in `profile.yaml: work_items.connector`. Available: `markdown` (default, no service needed),
`github-issues`, `trello`, `jira`. A new tracker = a new file here with the same seven operations.

Rules for every connector:
- Credentials come from environment variables named in the profile; never write tokens into files.
- Every write is read back (core §4.11).
- Messages to humans follow core §4.12 (drafted unless the template is pre-authorised).
