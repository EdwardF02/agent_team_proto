# Connector: Trello

Uses the Trello REST API with an API key and token (create them at trello.com/power-ups/admin; store as
env vars named in `work_items.trello.key_env` / `token_env`, defaults `TRELLO_KEY` / `TRELLO_TOKEN`).
Profile keys: `work_items.trello.board_id`, and `statuses` mapping each canonical status to a **list id**
(look them up once: `GET /1/boards/<board_id>/lists`).

Item id = the card's short id or short link. Base URL `https://api.trello.com/1`, auth as query params
`key=$TRELLO_KEY&token=$TRELLO_TOKEN`.

| Operation | How |
|---|---|
| `list(status)` | `GET /lists/<list_id>/cards` |
| `read(id)` | `GET /cards/<id>?attachments=true&checklists=all` + comments: `GET /cards/<id>/actions?filter=commentCard` |
| `create(text)` | `POST /cards` with `idList=<new list>&name=…&desc=…` |
| `set_status` | `PUT /cards/<id>` with `idList=<target list id>` |
| `assign` | `POST /cards/<id>/idMembers` with `value=<member id>` |
| `comment` | `POST /cards/<id>/actions/comments` with `text=…` (mention with `@username`) |
| `attach` | `POST /cards/<id>/attachments` multipart `file=@<path>` |

Use `curl -sS -G` / `--data-urlencode` so text with spaces and symbols is encoded. Never echo the token.
