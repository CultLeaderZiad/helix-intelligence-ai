# Helix Intelligence

Helix Intelligence is a competitive-ad-intelligence workstation. It lets a
user query competitor ad libraries ("Discover"), and — in loops that are
planned but not yet built — mine recurring creative patterns
("Intelligence"), draft new creative briefed on those patterns ("Create"),
and feed live performance back into the scoring model ("Performance").

This repository currently implements **one loop end-to-end: Discover.**
Everything else in the sidebar is a real navigation entry pointing at a
placeholder screen (`PendingLoopPage`) that says so plainly — there is no
faked data or fake UI standing in for unbuilt product.

Read this file first, then follow the links below for the area you're
touching. All five documents are written for a developer or AI agent
with no prior context on this conversation.

## Documentation map

| Document | Read this for |
|---|---|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Frontend stack, project structure, component architecture, the page → hook → service contract, data models |
| [`DESIGN_SYSTEM.md`](./DESIGN_SYSTEM.md) | Design tokens, typography, spacing, motion rules, accent discipline, anti-patterns that must not be reintroduced |
| [`API_CONTRACTS.md`](./API_CONTRACTS.md) | The mock ⇄ future-FastAPI service contracts, request/response shapes, how the data boundary works |
| [`DEVELOPMENT.md`](./DEVELOPMENT.md) | How to run locally, how to build, environment variables, known TODOs, PLANNED integrations |

## What this is not

- **Not a Next.js app**, despite what an earlier version of this file said.
  It is a client-only **Vite + React 19** single-page app using
  `react-router-dom` for routing. There is no server component, no API
  route, and no SSR anywhere in this repository today.
- **Not connected to a real backend yet.** Every byte of data currently
  rendered comes from in-memory fixtures in `src/data/`, served through a
  mock service layer that simulates latency, pagination, and failure. See
  [`API_CONTRACTS.md`](./API_CONTRACTS.md) for exactly how the swap to a
  real FastAPI backend is designed to happen without touching a single
  component.
- **Not connected to a database yet.** A future Neon Postgres integration
  is PLANNED — see [`DEVELOPMENT.md`](./DEVELOPMENT.md) — but nothing in
  this codebase talks to Neon, Postgres, or any other datastore today.

## Quick start

```bash
pnpm install
pnpm dev       # http://localhost:3000
```

See [`DEVELOPMENT.md`](./DEVELOPMENT.md) for build commands, environment
variables, and troubleshooting.

## Built with v0

This repository is linked to a [v0](https://v0.app) project. You can
continue developing by visiting the link below — start new chats to make
changes, and v0 will push commits directly to this repo. Every merge to
`main` will automatically deploy.

[Continue working on v0 →](https://v0.app/chat/projects/prj_EHmR27b76XzctNqInu1YZp1CDzTB)
