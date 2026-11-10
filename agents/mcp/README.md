# Helix read-only MCP server

Competitor ads your agents can read. Four read-only tools, all answering in
Markdown with the same labels as the app:

| Tool | Reads | Never does |
|---|---|---|
| `search_ads(query, min_days, sort)` | `GET /api/discovery/stored-results` — the latest finished search your workspace ran for that query | start a search or spend credits |
| `get_board(board)` | `GET /api/boards/items` — one of your boards | change a board |
| `list_monitor_changes(monitor_id?)` | `GET /api/monitors/events` | create or run a monitor |
| `get_ad(ad_id)` | `GET /api/creatives/{id}` | — |

Ads with no reported start date show run length "unknown" (never 0), the score is a text rubric (not a
performance prediction), reach appears only for Meta-official rows, and all
data is Meta-only.

## Setup

```bash
pip install -r agents/mcp/requirements.txt
HELIX_API_URL=https://<api-host>/api HELIX_ACCESS_TOKEN=<your session token> python agents/mcp/server.py
```

Claude Desktop / Claude Code config:

```json
{ "mcpServers": { "helix": {
  "command": "python", "args": ["agents/mcp/server.py"],
  "env": { "HELIX_API_URL": "https://<api-host>/api", "HELIX_ACCESS_TOKEN": "<token>" } } } }
```

## Auth today, and the token design if keys return

Today the server uses **your own session token**. Every request goes through
the same auth, workspace row-level security and feature flags as the web
app, and it expires like a session. There is no separate key system: the
old unrestricted API-key path was removed and is not coming back in that
form.

If long-lived agent tokens are added later, the design is:

- **Read-only by construction.** Scope `read:ads read:boards read:monitors`.
  The dependency that accepts these tokens is mounted only on the GET routes
  above and rejects every other method.
- **One workspace.** The token row holds `org_id`; auth binds
  `helix.org_ids` to exactly that id (no platform-admin bypass, no owner
  fallback), so RLS limits every query to that workspace.
- **Stored as a hash only** (SHA-256 of a 256-bit random secret, shown
  once), with `expires_at` (at most 90 days), `revoked_at`, `last_used_at`
  and a creator id. Revocation takes effect on the next request.
- **Inherits the workspace's flags.** A token cannot reach Monitors if the
  workspace is not granted `monitors`. Rate limits apply per token.
- **No write scope exists.** Writes stay in the signed-in app.
