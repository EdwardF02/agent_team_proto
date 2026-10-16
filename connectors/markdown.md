# Connector: markdown (local job files)

For work that arrives by email or chat. No service, no credentials. Each job is one file in the
workspace, so client material never leaves your machine.

**Location:** `<workspace>/<work_items.markdown.dir>/` (default `jobs/`), one folder per client:
`jobs/<client>/<id>-<slug>.md`. Ids are `<PREFIX>-<n>` (prefix from `work_items.id_prefix`, default `JOB`),
numbered across the workspace.

**File format** — copy `profiles/_template/job-template.md`:
- YAML front matter: `id`, `title`, `client`, `status` (profile's status name), `assignee`, `created`,
  `quoted` (optional), `branch`, `pr`.
- `## Request` — the client's words, pasted verbatim (email/chat), with date and sender.
- `## Agreed scope` — what was agreed, bullet list. The scope rule (core §4.5) checks against this.
- `## Plan`, `## Notes`, `## Delivery` — filled as the job moves.
- `## History` — append-only log, newest last: `- 2026-10-16 14:05 · status → in_progress · <who/why>`.
  Client replies get pasted here verbatim with date.

| Operation | How |
|---|---|
| `list(status)` | `grep -l "^status: <name>" jobs/**/*.md` (or read front matter) |
| `read(id)` | read the file; history = the `## History` section |
| `create(text)` | next free id; new file from the template; paste the text under `## Request`; status `new` |
| `set_status` | edit front matter `status:` and append a History line |
| `assign` | edit `assignee:` + History line |
| `comment` | append to History. Anything meant for the **client** is written as a draft under `## Delivery` (or `drafts/<id>-<n>.md`) for the owner to send — never sent by the team |
| `attach` | save to `jobs/<client>/<id>-files/` and link it from the file |

When the owner pastes a client reply, the TL appends it to History before acting on it.
