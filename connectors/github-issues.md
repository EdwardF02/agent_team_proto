# Connector: GitHub Issues

Needs the `gh` CLI authenticated (`gh auth login`), or the GitHub MCP server if your AI tool has it.
Profile keys: `work_items.github.repo` (`owner/name`), `work_items.github.status_via` (`labels` or
`project`), and the status → label (or project column) map in `statuses`.

Item id = `#<number>` (or `owner/name#<number>` across repos).

| Operation | How (gh CLI) |
|---|---|
| `list(status)` | `gh issue list -R <repo> --label "<status-label>" --assignee @me --state open` |
| `read(id)` | `gh issue view <n> -R <repo> --comments` (attachments are links in the body/comments) |
| `create(text)` | `gh issue create -R <repo> --title "…" --body-file <file>` |
| `set_status` | labels: `gh issue edit <n> -R <repo> --remove-label "<old>" --add-label "<new>"`; `done` → `gh issue close <n>` |
| `assign` | `gh issue edit <n> -R <repo> --add-assignee <login>` |
| `comment` | `gh issue comment <n> -R <repo> --body-file <file>` (mention with `@login`) |
| `attach` | GitHub CLI can't upload issue attachments: commit images to the PR branch or a demo branch and link them, or ask the owner to drag them in |

With `status_via: project`, statuses are a GitHub Projects field: use `gh project item-edit` (look up the
project, field and option ids once and store them in the profile).
PRs: `gh pr create / view / review / checks`. CI watch: `gh pr checks <n> --watch` in the background, or
`gh run watch`.
