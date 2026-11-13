# W9 feature ideas: ranked shortlist

Research only. Nothing here is built. Date: 2026-11-11.

## What exists today (from the repo)

- **Discover**: Meta ad search as a durable job, sorted by days active. Text-rubric scores (0–10), `impressions_est` only for Meta-official rows. Search drafts and server-side history.
- **Monitors**: scheduled re-runs, new / stopped / rewritten ad events, daily digest (in-app plus optional Resend email).
- **Swipe Files**: boards, custom references, playbook reports, HMAC guest share links, team boards.
- **Permanent ad archive**: text and Meta-CDN media copied to R2 after every search, capped at 5,000 entries per workspace.
- **Agent surface**: Markdown responses and a read-only MCP server (`search_ads`, `get_board`, `list_monitor_changes`, `get_ad`).
- Not built, and must not be faked: Intelligence, Create, Performance, API keys.

## Budget lens

Metapi bills per returned record: about 3,000 a month, about 910 used. Each idea is tagged:
- **0**: uses data we already hold (the archive, jobs or boards). Costs no records.
- **Low**: costs records only when a user explicitly asks, with a cap.
- **High**: recurring or bulk record pulls.

Effort assumes the current stack: React/Vite, FastAPI, Neon with RLS, the embedded worker, Render free tier. S is about 1–3 days, M about 1–2 weeks, L more than 2 weeks.

## Ranked shortlist

| # | Idea | Effort | Record cost |
|---|---|---|---|
| 1 | Search across your archive and boards | S | 0 (saves records) |
| 2 | Record budget guardrails (preview, caps) | S | saves records |
| 3 | Chrome extension: save from the Meta Ad Library | M | 0 |
| 4 | Brand timeline / ad history from the archive | M | 0 |
| 5 | Long-runner ("winning ad") alerts | S | 0 |
| 6 | "What changed this week" page | S | 0 |
| 7 | Tags, notes and comments on saved ads | S | 0 |
| 8 | Video transcripts and hook text | M | 0 records, needs a speech-to-text vendor |
| 9 | Brief builder from a board | M | 0 |
| 10 | Board export (CSV / ZIP of media) | S | 0 |
| 11 | Arabic / MENA-first search and presets | M | Low |
| 12 | Group variants of one concept | M | 0 |
| 13 | Landing-page capture | M | 0 |
| 14 | Second network (TikTok) | L | High |

### 1. Search across your archive and boards
- **Problem**: users re-run Discover, which burns records, to find ads they have already pulled.
- **Who has it**: Foreplay and Atria (search their own library).
- **Stack**: Postgres full-text search (`simple` + `arabic` configs) over `ad_archive` and saved creatives, under the existing RLS. Builds on `/stored-results`.
- **Cost**: negative. It answers repeat questions from stored data.

### 2. Record budget guardrails
- **Problem**: users cannot see what a search or monitor will cost, and monitors are the recurring burn.
- **Stack**: an estimated record count before a run, a per-workspace monthly cap with a usage meter in Access & Usage, and a monitor frequency floor.
- **Who has it**: no competitor exposes this, because they buy data in bulk. It is a Helix-specific need.
- **Cost**: protects the budget directly.

### 3. Chrome extension: save from the Meta Ad Library
- **Problem**: researchers live in the free Ad Library, but it cannot save ads.
- **Evidence**: [Trendtrack](https://www.trendtrack.io/blog-post/the-6-best-facebook-spy-tools-2026), [Atria on Foreplay alternatives](https://www.tryatria.com/blog/foreplay-alternatives-6-other-ad-workflow-tools-that-satisfy).
- **Who has it**: Foreplay (its main growth loop), Atria, Motion.
- **Stack**: a Manifest V3 extension that posts to the existing `POST /api/creatives/custom` with the user's session. Media follows the existing archive path and its Meta CDN allow-list.
- **Cost**: 0 records. Users fill the library themselves.

### 4. Brand timeline / ad history
- **Problem**: the Meta Ad Library mostly shows what is live now. Several reviews give history as the reason to pay rather than use the free library.
- **Evidence**: [Segwise](https://segwise.ai/blog/best-facebook-ad-spy-tools), [Trendtrack](https://www.trendtrack.io/blog-post/the-6-best-facebook-spy-tools-2026).
- **Who has it**: Foreplay (Spyder), Atria, BigSpy.
- **Stack**: a read view over `ad_archive` and monitor events, grouped by brand on a timeline (first seen, stopped, copy changes).
- **Cost**: 0. The data is already archived.

### 5. Long-runner alerts
- **Problem**: "ads still running after 30 or more days" is the common proxy for winning ads.
- **Evidence**: run length is Discover's default sort and the standard heuristic in [roundups](https://www.admapix.com/ad-intelligence/best-ad-spy-tools-2026).
- **Stack**: a threshold on monitor events (days active crosses N), reported in the existing digest.
- **Cost**: 0 extra. It uses runs that already happen.

### 6. "What changed this week" page
- **Problem**: the digest exists only as a notification or email. Users want a page to scan and share.
- **Who has it**: Atria (Radar), PiPiAds and Minea (alerts on new launches). See [Trendtrack on PiPiAds](https://trendtrack.io/blog-post/pipiads-alternatives).
- **Stack**: a page over the existing `GET /api/monitors/events`.
- **Cost**: 0.

### 7. Tags, notes and comments on saved ads
- **Problem**: teams need to record why an ad was saved.
- **Who has it**: Foreplay, Atria, Motion.
- **Stack**: small RLS tables and board UI.
- **Cost**: 0.

### 8. Video transcripts and hook text
- **Problem**: users skim dozens of videos to find hooks. A transcript makes them searchable and copyable.
- **Evidence**: [Minea and BigSpy comparison](https://www.gethookd.ai/learn/bigspy-vs-minea-vs-gethookd-features-pricing-compared/), [Affninja on AI ad-spy tools](https://affninja.com/ai-ad-spy-tools/).
- **Who has it**: Minea (AI transcript), PiPiAds, Foreplay, Atria.
- **Stack**: a worker job over archived media in R2. Local Whisper is too heavy for Render free, so it needs a hosted speech-to-text API with Arabic support and a monthly cap. That is a paid-vendor decision for Ziad.
- **Cost**: 0 Metapi records, plus a speech-to-text bill.

### 9. Brief builder from a board
- **Problem**: teams turn swipe files into creative briefs by hand.
- **Who has it**: Foreplay (Briefs), Atria.
- **Stack**: a template filled from board items and notes, exported to Markdown or PDF. Keep it non-generative so it is not mistaken for the unbuilt Create loop.
- **Cost**: 0.

### 10. Board export
- **Problem**: agencies hand work to clients outside the tool.
- **Who has it**: Foreplay, Atria.
- **Stack**: CSV, plus a ZIP of media streamed from R2.
- **Cost**: 0.

### 11. Arabic / MENA-first experience
- **Problem**: competitors are English- and US-centric. Helix already supports Arabic and RTL.
- **Stack**: MENA country presets, Arabic-aware query expansion and search that ignores diacritics and letter variants. This is a differentiator.
- **Cost**: Low (only searches users choose to run).

### 12. Group variants of one concept
- **Problem**: brands run dozens of near-identical variants, which clutters results.
- **Who has it**: Atria and Motion.
- **Stack**: pg_trgm text similarity plus a media hash. Collapse groups in the UI.
- **Cost**: 0.

### 13. Landing-page capture
- **Problem**: the ad is half the funnel. Users want the destination page too.
- **Who has it**: Minea and AdSpy (the shop behind the ad).
- **Stack**: an HTML and metadata snapshot via the existing `safe_fetch`. Skip screenshots, because a headless browser is too heavy for Render free.
- **Cost**: 0 records.

### 14. Second network (TikTok)
- **Problem**: buyers compare tools on coverage. Atria covers Meta and TikTok ([Dupple](https://dupple.com/tools/atria)), and PiPiAds is TikTok-first.
- **Stack**: a new provider adapter. It adds data cost and terms-of-service risk.
- **Cost**: High. **Defer until paying customers ask.**

## Top 3 recommendation

1. **Archive search (#1) with budget guardrails (#2).** Both are small, and they protect the Metapi budget, which is the binding constraint before 10 customers.
2. **Chrome extension "Save to Helix" (#3).** This is Foreplay's growth loop. It costs no records, and users fill their own library with it.
3. **Brand timeline (#4).** It turns the archive Helix already builds into the "history" feature users pay competitors for, with no new data cost.

Next, if a speech-to-text vendor is approved: transcripts (#8).

## User voice (Reddit / YouTube, via agent-reach)

Grouped by theme, following the agency-agents Feedback Synthesizer method. Read via agent-reach's public-web backend. Reddit blocked full-thread reads, so these quotes come from post bodies in search results.

| Theme | Evidence | Helix today | Ideas |
|---|---|---|---|
| **Saved ads disappear when they stop running** (most repeated) | [r/FacebookAds: "dead link, ad's gone"](https://www.reddit.com/r/FacebookAds/comments/1owpi9c/how_do_you_save_ads_from_facebook_ad_library/), [r/advertising: broken library links rant](https://www.reddit.com/r/advertising/comments/1pun0rq/the_broken_facebook_ad_library_links_situation_is/), [r/PPC: Foreplay "saves ads properly so links don't break"](https://www.reddit.com/r/PPC/comments/1p7zlzm/adspy_vs_foreplay_vs_motion/) | **Already solved** by the permanent archive in R2, but the landing page and onboarding don't say so | Market it. Pairs with #3 extension and #4 timeline |
| **Weekly manual competitor checks** | [r/DigitalMarketing: "Friday mornings… screenshot anything good… still miss half"](https://www.reddit.com/r/DigitalMarketing/comments/1onbl3i/i_feel_like_im_wasting_hours_manually_tracking_my/) | Monitors and digest exist | #5, #6. Make "Monitor this brand" one click from results (D2) |
| **Ad Library UI is unusable at scale** | [r/PPC: "basically unusable… 6 clients"](https://www.reddit.com/r/PPC/comments/1occj59/facebook_ads_library_is_basically_unusable_for/), [r/FacebookAds: "painful for creative research"](https://www.reddit.com/r/FacebookAds/comments/1v1s40h/anyone_else_feel_like_meta_ad_library_is_painful/), [r/FacebookAds: library doesn't scroll](https://www.reddit.com/r/FacebookAds/comments/1iog8jx/fb_library_doesnt_scroll/) | Discover | The Discover improvements below |
| **Hook and CTA breakdowns help juniors** | [r/adtech 2026 tool comparison: GetHookd's hook and CTA breakdown](https://www.reddit.com/r/adtech/comments/1q143pl/we_tried_in_2025_for_ad_research_gethookd_minea/) | Text rubric scores only | #8 transcripts, D5 |
| **Save from your phone while scrolling** | [r/PPC: Foreplay mobile save "is clutch"](https://www.reddit.com/r/PPC/comments/1p7zlzm/adspy_vs_foreplay_vs_motion/) | none | #3 extension, then a mobile share link (D6) |
| **Atria seen as an "AI creative strategist"** | YouTube: [switched from Foreplay to Atria](https://www.youtube.com/watch?v=8OKGCDa-w44), [Atria vs Motion](https://www.youtube.com/watch?v=GUFGnOsY84M) | Intelligence is not built | Do not fake it. Ship deterministic insights first (D4) |

## Discover better: specific improvements

Today Discover keeps only `country`, `min_days_active` and `min_score` as filters, plus language and platform in the UI. Ranked with RICE (agency-agents Sprint Prioritizer), where reach means the share of Discover users who would touch it.

| # | Improvement | Why (theme) | Effort | Records | RICE note |
|---|---|---|---|---|---|
| D1 | **"Already have this" check before a search**: if a matching stored search is under N days old, offer it first and show the record cost of a fresh run | budget, UI at scale | S | saves | Highest. Every search, low effort |
| D2 | **One-click "Monitor this brand"** from a result card or brand header | weekly manual checks | S | Low (capped by #2) | High reach, tiny effort |
| D3 | **Client-side filters on loaded results**: media type (video / image / carousel), status (active / stopped), CTA, landing domain, run-length slider | UI at scale | S | 0 | Filters only the page already fetched, so no re-query |
| D4 | **Deterministic results summary** at the top: number of active ads, median run length, top landing domains, media mix, longest runners. Plain counts, labelled as counts | "strategist" demand, without faking AI | S–M | 0 | Honest stand-in for Intelligence |
| D5 | **Hook line and CTA pulled from ad copy** (first sentence, CTA button), searchable | hook breakdowns | S | 0 | Transcripts (#8) extend it to video |
| D6 | **Paste an Ad Library URL or ad id → archive just that ad** | phone and save flows | S | ≤1 record | Builds on existing Ad Library URL queries |
| D7 | **Group variants** (#12) in results, with a "+7 variants" badge | clutter | M | 0 | Medium |
| D8 | **Compare two brands side by side** (D4 stats for each) | competitive research | M | 0 if both are stored | Medium |
| D9 | **Infinite scroll and a keyboard-driven preview** (j/k, s to save) | "doesn't scroll", speed | S | 0 | Cheap UX win |

**Discover top 3**: D1 (it protects the budget on every search), D3 + D9 (filters and fast browsing with no record cost), D2 (turns a one-off search into a retained monitor).

## Pricing context
Prices vary by source, so check vendor sites. Foreplay is about $49–459 a month ([AdManage](https://admanage.ai/blog/foreplay-alternatives)). Atria starts around $129 a month ([Dupple](https://dupple.com/tools/atria)). Motion is quoted from about $250 to $999 or more a month ([Madgicx](https://madgicx.com/compare/atria-vs-foreplay)).

## Caveats
- Most comparison pages are published by competing vendors.
- The User voice section comes from agent-reach (Reddit search and YouTube search via public-web and yt-dlp). Reddit blocked full-thread and comment reads, so the evidence is post bodies only. X was not searched, because it needs the user's own login.
- Personas used: agency-agents Feedback Synthesizer (themes) and Sprint Prioritizer (RICE).
