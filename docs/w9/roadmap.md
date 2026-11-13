# W9 roadmap: from sign-up to "this solves my problem"

Companion to [`feature-ideas.md`](./feature-ideas.md). Planning only: nothing below is built yet unless marked **Live**.

## What Helix is for

Helix Intelligence is a competitive ad-intelligence workstation for DTC brands, agencies and media buyers who research Meta ads.

| Problem users name (Reddit, see feature-ideas.md) | How Helix solves it |
|---|---|
| **X — "My saved ads die."** Ad Library links break when an ad stops running. | Every ad Helix finds is archived for good: copy plus media in private storage. **Live** |
| **Y — "I check competitors by hand every Friday and still miss half."** | Monitors re-run searches and send one digest of new, stopped and rewritten ads. **Live**, plus a weekly page (W9) |
| **Z — "The Ad Library is unusable for research."** No saving, no history, clunky UI. | Discover jobs, boards, search over your archive, brand timelines, AI breakdowns (W9) |

Ground rules for every phase:
- No faked data or UI.
- Every AI output is labelled as AI analysis, not measured performance.
- Metapi records are spent only when the user starts a search or monitor, and the user always sees the cost first.
- Everything works in English and Arabic (RTL).

## The user journey (target state after W9)

### 0. Sign up → access
- Sign up, then wait on the access-request screen. An admin grants flags (`discover`, `monitors`, `swipe_files`). **Live**
- **W9:** the approval email links straight to the onboarding wizard. The pending screen says what they will get and roughly how long approval takes.

### 1. First 5 minutes: the "aha"
- The onboarding wizard asks for **your brand and up to 3 competitors**. **Live** (partly; extend it)
- **W9 — stored results first (D1):** if Helix already holds recent results for a competitor, show them instantly at a cost of 0 records. Otherwise start one search and show its record cost first.
- **W9 — results summary (D4):** "Competitor X runs 42 active ads. Median run is 23 days. 60% video. Top landing page: /offer." Plain counts, no invented insight.
- **Aha moment:** seeing the competitor's longest-running ads, sorted, saved forever.

### 2. First session: organise
- Save to a board (**Live**), with **tags and notes in place (#7)**.
- **Search across your archive and boards (#1):** "find that UGC hook ad from last month" without spending records.
- **One-click "Monitor this brand" (D2)** from any result.

### 3. First week: the habit
- The daily digest (**Live**) and a **"What changed this week" page (#6)**. This replaces the Friday screenshot routine.
- **Brand timeline (#4):** what a competitor launched, killed and rewrote over time.
- **Record meter and guardrails (#2):** visible in Access & Usage and before every run. A monthly cap per workspace, with a warning at 80%.

### 4. Premium moments (what makes it feel worth paying for)
- **AI ad breakdown:** one click gives hook, angle, offer, CTA and format for an archived image or video. Labelled as AI analysis. Capped per workspace, 0 records.
- **Brief builder (#9):** turn a board, plus its breakdowns, into a creative brief and export it.
- **Board export (#10):** CSV, ZIP of media, or a share link (share links are **Live**) for clients.
- **Chrome extension (#3):** "Save to Helix" from the Meta Ad Library. The ad is archived and never breaks.
- **Automations:** send monitor events to Slack, a webhook or Google Sheets.
- **Arabic / MENA:** a full RTL experience that competitors lack.

## Build order (stacked draft PRs, never to main)

| Phase | Ships | Effort | Metapi records | New cost |
|---|---|---|---|---|
| **W9-1** | #1 archive and board search · #2 record guardrails and meter · D1 stored results first | S+S | saves | $0 |
| **W9-2** | #7 tags and notes · D2 one-click monitor · D3/D9 client filters, infinite scroll, shortcuts | S | 0 / capped | $0 |
| **W9-3** | #6 weekly page · #4 brand timeline · D4 results summary | M | 0 | $0 |
| **W9-4** | #10 board export · #9 brief builder | M | 0 | $0 (R2 egress is free) |
| **W9-5** | AI ad breakdown (worker job, capped) | M | 0 | AI API, about $1–10 per 1,000 analyses (verify pricing) |
| **W9-6** | Chrome extension · Slack, webhook and Sheets outputs | M | 0 | $5 one-time Chrome Web Store fee |
| Later | TikTok source · Create (original ads from a brief) | L | high | Needs its own design |

Each phase ends with its own PR, its tests, and an updated `API_CONTRACTS.md`.

## Success signals (to check per phase)
- Time to first saved ad under 5 minutes.
- Share of searches answered from stored results: up after W9-1.
- Records per active workspace per month: down after W9-1.
- Weekly active monitors per workspace, and weekly page views.

## Non-goals in W9
- No "clone a competitor's ad" generation.
- No faked Intelligence, Create or Performance screens.
- No paid infrastructure until 10 customers. The exceptions are the AI analysis bill (capped) and the $5 Chrome Web Store fee, and both need Ziad's approval.
