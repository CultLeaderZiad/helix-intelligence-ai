# Helix Intelligence

Helix Intelligence is a competitive-ad-intelligence workstation with three
features:

- **Discover** — search competitor ad libraries, run the search as a durable
  background job, and browse the resulting ads (sorted by days active by
  default). Live.
- **Monitors** — saved Discover searches that re-run on a schedule and report
  new, stopped and rewritten ads. Shown when the workspace is granted the
  `monitors` flag.
- **Boards and share links** — save ads into boards and produce a report
  link. Shown when the workspace is granted the `swipe_files` flag.

Access is granted manually by a platform administrator; there is no trial,
pricing or checkout. W8 removed Create, Intelligence, Performance, the
dashboard, Scout/Lead generation and API keys (see `AUDIT-W8.md`). There is no
faked data or fake UI standing in for unbuilt product.

Read this file first, then follow the links below for the area you're
touching. All four documents are written for a developer or AI agent
with no prior context on this conversation.

## Documentation map

| Document | Read this for |
|---|---|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Frontend stack, project structure, component architecture, the page → hook → service contract, data models |
| [`API_CONTRACTS.md`](./API_CONTRACTS.md) | The FastAPI service contracts, request/response shapes, how the data boundary works |
| [`DEVELOPMENT.md`](./DEVELOPMENT.md) | How to run locally, how to build, environment variables, known TODOs, PLANNED integrations, status reporting rules |

## Status & Reporting Rules

**Rule**: Never claim “zero bugs,” “fully functional,” or “production healthy” from code inspection alone.

When reporting status, changes, or PRs:
1. **What changed** (files modified)
2. **What was verified** (browser / curl / unit tests / none)
3. **What remains unverified** (production / end-to-end flows not yet tested)
4. **P0 next step only**

`main` deploys to Render (free web service, ohio) and Vercel. For the W8 release,
turn Render auto-deploy off first and follow `docs/w8/release-plan.md`.

[Continue working on v0 →](https://v0.app/chat/projects/prj_EHmR27b76XzctNqInu1YZp1CDzTB)

