# Helix Intelligence — notes for AI agents

Helix is an invite-only web app for competitor ad research on Meta. This file
says what an agent can and cannot do with it today. It describes only what
exists.

## What the product does

- **Discover** searches the Meta Ad Library for a brand or domain and sorts
  the ads by how many days each has been running.
- **Monitors** re-run a saved search on a schedule and list new, stopped and
  rewritten ads.
- **Boards** keep saved ads together inside one workspace.

## How to read the data honestly

- `days_active` is computed from the ad library's start date. When the source
  does not report one, the value is `null` and the app shows "unknown". Treat
  `null` as unknown, never as 0.
- The score is a rubric of the ad text (hook, clarity, retention). It is not
  a performance prediction and is not based on spend or results.
- `impressions_est` is present only for rows from Meta's official Ad Library
  API, where it is the upper bound of the range Meta reports. Other sources
  carry no reach or spend.
- Every provider is Meta-only. There is no Google, TikTok or LinkedIn data.

## Competitor ads your agents can read

- **Markdown views.** These read routes answer in Markdown when you send
  `Accept: text/markdown`, add `?format=md`, or use the `.md` form:
  stored search results (`/api/discovery/jobs/{id}/results.md`, or
  `/api/discovery/stored-results?query=` for the latest finished search),
  one ad (`/api/creatives/{id}.md`), your boards
  (`/api/boards/items?collection=`), monitor changes
  (`/api/monitors/events.md`) and guest board links
  (`/api/public/boards/{token}.md`).
- **Read-only MCP server** (`agents/mcp` in the repository) with four tools:
  `search_ads`, `get_board`, `list_monitor_changes`, `get_ad`. It only reads
  searches your workspace already ran; it never starts a search or spends
  credits.
- Both use the signed-in user's own session and the same workspace
  row-level security and feature flags as the web app. Guest board links
  need no sign-in but are read-only, expire, and can be revoked.

## What agents cannot do

- There is **no public write API**. Agents cannot create, change or delete
  anything in Helix, and cannot start searches.
- There are no API keys. An earlier unrestricted API-key path was removed
  and will not come back in that form; a read-only, single-workspace token
  design is documented for if keys return.

## Contact

Request access from the sign-up page; an administrator reviews each
request.
