# Connector: Jira

Preferred: the Atlassian MCP server (tools like get issue, search with JQL, transition, add comment).
Fallback: Jira REST with an API token (env vars named in the profile).
Profile keys: `work_items.jira.site`, `project`, `cloud_id` (if needed), and `statuses` mapping each
canonical status to a **transition id** (transition ids differ per workflow: list them once from the
"get transitions" call and store them).

Item id = the issue key (`ABC-123`).

| Operation | How |
|---|---|
| `list(status)` | JQL: `assignee = currentUser() AND status = "<name>" ORDER BY Rank ASC` (add `sprint in openSprints()` if the team uses sprints) |
| `read(id)` | get issue (fields incl. attachment, parent) + the last ~10 comments |
| `create(text)` | create issue (follow the team's own ticket templates if they have them) |
| `set_status` | transition with the mapped transition id |
| `assign` | edit issue → assignee account id |
| `comment` | add comment; @mentions must be real mention nodes (ADF `mention` with the account id) — verify it resolved |
| `attach` | REST `POST /rest/api/3/issue/<key>/attachments` with header `X-Atlassian-Token: no-check` |

Long rich text (descriptions, bullet lists, mentions) is ADF. Keep comments short; detail goes in the
description or the PR.
