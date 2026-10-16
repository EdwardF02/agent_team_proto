# Agent Team kit — maintainer notes

This repo is the **kit** (shared rules), not a place to run work. To run a team, create a workspace:
`scripts/new-workspace.sh <dir> <profile>` and start the AI there.

When editing the kit:
- `core/` must stay company-neutral: no company names, people, URLs, ids, ticket keys or client details.
  A rule that only holds for one setup goes in that profile's `overlay.md`.
- Every core rule should make sense for both a team with tickets/QA (see `profiles/_template`) and a solo
  freelancer (see `profiles/freelance`). If it doesn't, it belongs in a profile.
- New tracker → a new `connectors/<name>.md` with the seven operations in `connectors/README.md`.
- New AI tool → `adapters/<tool>/`. The core never names a specific AI tool's features.
- Keep rules as short bullets; the story behind a rule goes in the "Why" section of its file.
