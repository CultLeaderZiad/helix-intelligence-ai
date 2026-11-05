# Helix Intelligence

Helix Intelligence is a competitive-ad-intelligence workstation. It lets a
user query competitor ad libraries ("Discover"), and — in loops that are
planned but not yet built — mine recurring creative patterns
("Intelligence"), draft new creative briefed on those patterns ("Create"),
and feed live performance back into the scoring model ("Performance").

This repository currently implements **one loop end-to-end: Discover.**
Features that are not built are not shown: their routes redirect to
`/discover` unless `VITE_ENABLE_EXPERIMENTAL_FEATURES=true`. There is no
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

`main` will automatically deploy.

[Continue working on v0 →](https://v0.app/chat/projects/prj_EHmR27b76XzctNqInu1YZp1CDzTB)

