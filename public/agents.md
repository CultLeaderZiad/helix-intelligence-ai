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

## Access for agents

- There is **no public write API**. Agents cannot create, change or delete
  anything in Helix.
- The HTTP API behind the web app requires a signed-in user of an approved
  workspace and enforces row-level security per workspace. It is not a
  public or stable integration surface.
- There are no API keys. An earlier unrestricted API-key path was removed
  and will not come back in that form.

## Contact

Request access from the sign-up page; an administrator reviews each
request.
