# Helix Intelligence — Legal, Privacy & Accessibility Audit (Wave L0)

**Date**: September 30, 2026  
**Auditor**: Full-Stack Product Compliance Engineering  
**Application**: Helix Intelligence (`CultLeaderZiad/helix-intelligence-ai`)  
**Deployment**: Vite/React 19 on Vercel (`https://helix-intelligence-ai-six.vercel.app/`) & FastAPI on Render  
**Operator**: Helix, operated by Ziad Sabry (Individual Operator, Cairo, Egypt — Pre-revenue Beta)  
**Contact**: `[CONTACT EMAIL]`  
**Governing Laws Analyzed**: EU/UK GDPR, CCPA/CPRA, Egypt Data Protection Law (Law 151/2020), Saudi PDPL (Royal Decree M/19), UAE PDPL (Federal Decree-Law No. 45/2021). Strictest standard applied where provisions diverge.

---

## 1. Data Inventory

The following table documents every personal, account, and operational data field collected and processed across Helix Intelligence:

| Field Name | Collection Surface | Stored Location | Purpose & Legal Basis | Retention Period | Cited Code Reference |
|---|---|---|---|---|---|
| `id` (UUID) | User Registration | PostgreSQL `users` table | Primary key, user identifier (Contractual Necessity) | Lifetime of user account | [`backend/app/models/user.py:20`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/user.py#L20) |
| `email` | Registration / Sign-in | PostgreSQL `users` table | Authentication, notifications, account recovery (Contractual Necessity) | Lifetime of account | [`backend/app/models/user.py:21`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/user.py#L21) |
| `password_hash` | Registration / Password Change | PostgreSQL `users` table | Secure password authentication via bcrypt (Security / Contractual) | Overwritten on change, purged on delete | [`backend/app/models/user.py:22`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/user.py#L22) |
| `full_name` | Registration / Profile Settings | PostgreSQL `users` table | Display name inside collaborative workspace (Legitimate Interest) | Lifetime of account | [`backend/app/models/user.py:23`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/user.py#L23) |
| `avatar_url` | Profile Settings | PostgreSQL `users` table | Optional profile avatar presentation | Lifetime of account | [`backend/app/models/user.py:24`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/user.py#L24) |
| `role` & `admin_permissions` | System / Admin Console | PostgreSQL `users` table | Role-based authorization & security access control (Contractual) | Lifetime of account | [`backend/app/models/user.py:25-28`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/user.py#L25-L28) |
| `trial_started_at`, `trial_expires_at` | Registration / System | PostgreSQL `users` table | Enforce 7-day beta trial limits (Contractual Necessity) | Duration of trial + account lifespan | [`backend/app/models/user.py:29-30`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/user.py#L29-L30) |
| `signup_metadata` (UTM & Referrer) | `src/lib/utm.js` on Signup | PostgreSQL `users` table | First-touch marketing attribution (`utm_source`, `utm_medium`, `utm_campaign`, `referrer`, `landing_path`, `user_agent`) (Consent / Legitimate Interest) | Lifetime of account | [`backend/app/models/user.py:33`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/user.py#L33) & [`src/lib/utm.js:15-80`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/lib/utm.js#L15-L80) |
| `password_reset_token_hash`, `password_reset_expires_at` | Reset Password Flow | PostgreSQL `users` table | Ephemeral single-use cryptographic token for password resets | Expires in 60 minutes | [`backend/app/models/user.py:34-35`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/user.py#L34-L35) |
| `encrypted_secret` & `key_suffix` | API Keys / BYOK Settings | PostgreSQL `workspace_provider_credentials` | Stores encrypted customer AI API keys (Fernet AES-GCM) to run models under BYOK (Consent / Contractual) | Until user deletes key or terminates account | [`backend/app/models/workspace_provider_credential.py:15-30`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/workspace_provider_credential.py#L15-L30) |
| Support Ticket (`type`, `subject`, `message`, `context_data`) | Support Modal / Page | PostgreSQL `support_tickets` & `support_ticket_replies` | User customer service, bug resolution, browser version context (Legitimate Interest) | Duration of account + 12 months for quality audit | [`backend/app/models/support.py:15-45`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/support.py#L15-L45) |
| Public Search Queries & Saved Creatives | Discovery, Intelligence, Swipe Files | PostgreSQL `scrape_jobs`, `creatives`, `saved_creatives`, `monitors`, `playbooks` | Caching public ad transparency data, personal swipe collections, competitor diff tracking | 30 days for scrape caches; user-initiated until deleted | [`backend/app/models/ad.py`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/ad.py) & [`creative.py`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/creative.py) |
| Scout Lead Records (`company_name`, `domain`, `contact_name`, `contact_email`, `phone`, `social_url`) | Scout Lead Generation | PostgreSQL `leadgen_leads` | Aggregating publicly disclosed B2B directory information (Legitimate Interest / Public Provenance) | Beta duration or until individual requests opt-out / deletion | [`backend/app/models/scout.py:20-55`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/models/scout.py#L20-L55) |

---

## 2. Cookies and Storage Inventory

The application operates an ultra-lean client storage policy. No cross-site tracking beacons, third-party marketing pixels, or advertising identifiers are deployed.

### Cookies
| Cookie Name | Purpose | Duration | Essential? | Cited Code Reference |
|---|---|---|---|---|
| `helix_access_token` | HTTP-only session bearer authorization token | Session / 7 days | **Yes (Strictly Essential)** | [`backend/app/api/routers/auth.py`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/api/routers/auth.py) |

### Local Storage (`localStorage`)
| Key Name | Purpose | Duration | Essential? | Cited Code Reference |
|---|---|---|---|---|
| `helix_access_token` | Client-side API authentication token | Persistent | **Yes (Strictly Essential)** | [`src/services/http.js:76`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/services/http.js#L76) |
| `helix_auth_token` | Fallback API authentication token | Persistent | **Yes (Strictly Essential)** | [`src/services/http.js:76`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/services/http.js#L76) |
| `helix_cached_user` | Cached user profile data for immediate UI rendering | Persistent | **Yes (Strictly Essential)** | [`src/context/AuthContext.jsx:40`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/context/AuthContext.jsx#L40) |
| `helix_lang` / `helix_search_lang` | User interface and query language selection (`en` / `ar`) | Persistent | **Yes (Functional / Preference)** | [`src/context/LanguageContext.jsx:414`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/context/LanguageContext.jsx#L414) |
| `helix_signup_attribution` | First-touch attribution parameters (captured on first landing) | Persistent | **Functional / Analytics** (Requires opt-in/disclosure) | [`src/lib/utm.js:46`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/lib/utm.js#L46) |
| `helix_update_read_{id}` | Tracks viewed changelog/announcement updates | Persistent | **Yes (Functional / UI State)** | [`src/components/NotificationBell.jsx:48`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/components/NotificationBell.jsx#L48) |
| `helix_banner_dismissed_{id}` | Remembers dismissed status of top announcement banners | Persistent | **Yes (Functional / UI State)** | [`src/components/UpdatesBanner.jsx:45`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/components/UpdatesBanner.jsx#L45) |
| `helix_latest_search` | Caches active search parameters for state recovery | Persistent | **Yes (Functional / UI State)** | [`src/context/SearchContext.jsx:93`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/context/SearchContext.jsx#L93) |
| `helix_search_history` | Recent searches array for autocomplete | Persistent | **Yes (Functional / UI State)** | [`src/context/SearchContext.jsx:108`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/context/SearchContext.jsx#L108) |
| `helix_active_creative` | Selected creative ID for slide-out brief preview | Persistent | **Yes (Functional / UI State)** | [`src/context/SearchContext.jsx:123`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/context/SearchContext.jsx#L123) |
| `helix_brief_drafts` | Locally saved creative brief form drafts | Persistent | **Yes (Functional / User Data)** | [`src/context/SearchContext.jsx:201`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/context/SearchContext.jsx#L201) |

### Session Storage (`sessionStorage`)
| Key Name | Purpose | Duration | Essential? | Cited Code Reference |
|---|---|---|---|---|
| `chunk_reload_lock` | Single-reload circuit breaker protecting against infinite reload loops during chunk stale deployments | Browser Session | **Yes (Strictly Essential)** | [`src/App.jsx:24`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/App.jsx#L24) & [`src/components/ErrorBoundary.jsx:30`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/components/ErrorBoundary.jsx#L30) |
| `helix_mock_session` | Mock token storage used only in local simulated sandbox mode | Browser Session | **Functional / Test Only** | [`src/services/mock/authService.mock.js:63`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/services/mock/authService.mock.js#L63) |

---

## 3. Third-Party External Processors

All external integrations invoked by either the frontend client or backend services are documented below:

| Processor / Entity | Integration Point | Data Transferred | Purpose | Processing Region & Legal Safeguard | Cited Code Reference |
|---|---|---|---|---|---|
| **Vercel Inc.** | Frontend Hosting & CDN | Visitor IP address, HTTP headers, requested URLs | SPA hosting, global edge asset routing | USA / Global Edge. DPA / Standard Contractual Clauses (SCCs). | [`vite.config.js`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/vite.config.js) |
| **Render Services Inc.** | Backend API Hosting | Client IP address, HTTP request payloads | FastAPI backend hosting, background task execution | USA (Oregon) / EU (Frankfurt). Standard Contractual Clauses (SCCs). | [`backend/main.py`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/main.py) |
| **PostgreSQL (Neon / Supabase)** | Backend DB Client | All database tables, user records, encrypted BYOK keys | Cloud relational database storage | USA / EU (AWS/GCP regions). AES-256 encrypted at rest. | [`backend/app/db/session.py`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/db/session.py) |
| **Google LLC (Gemini API)** | Backend AI Provider | Ad text copy, prompt briefs, visual descriptions (zero user PII) | AI ad scoring, pattern clustering, brief generation | USA (Google Cloud). Enterprise API non-training terms. | [`backend/app/services/providers/gemini_provider.py`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/services/providers/gemini_provider.py) |
| **OpenAI Inc.** | Backend AI Provider | Ad text copy, brief synthesis prompts (zero user PII) | Secondary AI inference & text generation | USA. API Data Privacy Agreement (non-training). | [`backend/app/services/providers/openai_provider.py`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/services/providers/openai_provider.py) |
| **Meta Platforms Inc. (Ad Library API)** | Backend Scraper Pipeline | Search queries (brand names, keywords, country codes) | Fetching public ad transparency disclosures | USA / Global. Official public transparency repository. | [`backend/app/services/ad_library.py`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/services/ad_library.py) |
| **Tavily Technologies** | Backend Search Provider | Search query strings (brand name, domain) | Real-time web search for ad intelligence discovery | USA. Service terms. | [`backend/app/services/search_service.py`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/services/search_service.py) |
| **TikHub / ScrapeGraph / Scrapling** | Backend Scout Lead Gen | Target search handle / public URL | Fetching public business directory & social profile records | USA / EU. Public data extraction. | [`backend/app/services/scout_service.py`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/services/scout_service.py) |
| **Resend / SMTP** | Backend Email Notification | User email, user name, password reset verification links | Transactional emails (password reset, invitations) | USA / EU. Transactional delivery DPA. | [`backend/app/services/notifications.py`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/backend/app/services/notifications.py) |
| **Meta CDN (`fbcdn.net`)** | Frontend Direct Client GET | User IP address (standard browser image request) | Rendering thumbnail images and video previews for public ads | USA / Global. Third-party content CDN. | [`src/features/discover/CreativeCard.jsx`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/features/discover/CreativeCard.jsx) |

---

## 4. Embeds & Remote Assets

- **Fonts**: 100% self-hosted locally via `@fontsource-variable/inter` and `@fontsource-variable/jetbrains-mono`. Zero network calls to Google Fonts or Typekit.
- **Logos & UI Artwork**: Local SVGs and WebP/PNG assets served from the `/public` root.
- **External CDN Media**: Scraped ad video snippets and creative thumbnails are hosted by Meta's public content delivery network (`*.fbcdn.net`).
- **Iframes**: None.
- **Analytics Scripts**: Zero loaded in production. (Cookieless Plausible analytics code exists in `index.html` gated conditionally behind `VITE_ANALYTICS_DOMAIN`, currently deactivated).

---

## 5. Marketing Claims & Proof Audit

A line-by-line review of marketing copy revealed several claims that are unverified, simulated, or legally inadvisable for an unregistered pre-revenue beta:

| Location | Finding / Wording | Reality / Audit Assessment | Required Action in Wave L3 |
|---|---|---|---|
| [`src/features/marketing/Hero.jsx:157`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/features/marketing/Hero.jsx#L157) & [`L297`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/features/marketing/Hero.jsx#L297) | `{(indexedCounter / 1000000).toFixed(2)}M+` starting at `14.25M+` with a simulated random counter interval | **Simulated / Fictitious Counter**. Not backed by actual indexed database volume. | Remove fictitious ticking counter; replace with honest copy e.g. "Public Ad Transparency Index (Beta Catalog)" or clearly label "Example Metric". |
| [`src/features/marketing/Hero.jsx:45-150`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/features/marketing/Hero.jsx#L45-L150) | Interactive terminal scenarios featuring Nike, Gymshark, Alo Yoga with timestamps ("1m ago", "2m ago") | **Interactive Mock Simulation**. Real-time streams and timestamps are synthetic demo data. | Label terminal prominently as "Interactive Simulation / Demonstration Example". |
| [`src/features/marketing/PricingSection.jsx:12-60`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/features/marketing/PricingSection.jsx#L12-L60) | Pricing tiers listed as "$49 / mo", "$199 / mo", "Custom" with "Start free trial" and feature caps | **Pre-Revenue Beta**. No paid payment processor (Stripe) is connected; platform is currently free beta. | Add explicit disclaimer: "Pre-revenue Beta: Free access during preview. Commercial pricing planned for future general availability." |
| [`src/features/marketing/LoopsSection.jsx:225-240`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/features/marketing/LoopsSection.jsx#L225-L240) | Mock Nike ad card ("Nike Pegasus 41", "SCORE: 94.2", "EST. REACH 1.4M", "VELOCITY +340%/wk") | **Demonstration UI Asset**. Reach and velocity metrics are synthetic illustration. | Add "Example Analysis" badge to card preview. |
| [`src/features/marketing/LoopsSection.jsx:530-545`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/features/marketing/LoopsSection.jsx#L530-L545) | "REACH LEADERBOARD" showing impressions for Nike, Gymshark, On Running | **Demonstration Mockup**. | Label as "Sample Leaderboard Calculation". |
| [`src/features/marketing/LoopsSection.jsx:607-613`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/features/marketing/LoopsSection.jsx#L607-L613) | Helix Scout demo displaying mock contact data (`hello@helixx.xo.je`, `+966 50 123 4567`) | **Synthetic Demo Record**. | Ensure clearly indicated as example output. |
| [`src/features/marketing/MarketingFooter.jsx:268`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/features/marketing/MarketingFooter.jsx#L268) | Hardcoded badge: `ALL SYSTEMS OPERATIONAL` | **Hardcoded Decorative String**. Not tied to an active ping/health check. | Replace with dynamic API health check ping or honest wording: "Beta Preview — Status Checks Active". |
| [`src/features/marketing/MarketingFooter.jsx:24`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/features/marketing/MarketingFooter.jsx#L24) | "We maintain a 99.9% uptime target." | **Unsubstantiated SLA**. Pre-revenue beta provides no formal uptime guarantee. | Replace with standard beta disclaimer: service provided "as is" without uptime warranties. |
| [`src/features/marketing/MarketingFooter.jsx:54-65`](file:///d:/A%20Done%20Projects%20-%20N8N%20-%20Veo3%20-%20Agents/Apps/Projects/Coding/Helixa-intelligence/helix-intelligence-ai/src/features/marketing/MarketingFooter.jsx#L54-L65) | "SOC2 & TLS 1.3 Standards" ... "Continuous Vulnerability Audits: Automated penetration testing and daily dependency sweeps guarantee platform integrity..." | **False / Uncertified Compliance Claim**. Helix is not SOC2 certified; an individual pre-revenue operator cannot claim SOC2. | Remove SOC2 and enterprise audit claims immediately. Replace with honest technical description: "TLS 1.3 encryption in transit, AES-256 for credentials at rest." |

---

## 6. Images, Icons & Licensing Review

| Asset Path | Nature & Content | Origin & Source | License Status | Action Required |
|---|---|---|---|---|
| `public/brand/helix-logo.svg`, `helix-mark.svg`, `helix-wordmark.svg`, `public/brand/helix-logo.png`, `helix-mark.png` | Brand logos, emblem, wordmark | Custom designed vector artwork for Helix | Owned proprietary artwork | None (fully compliant) |
| `public/icon.svg`, `public/apple-icon.png`, `public/icon-*-32x32.png` | Favicon and mobile touch icons | Derived from Helix brand logo | Owned proprietary artwork | None (fully compliant) |
| `public/placeholder-logo.svg`, `placeholder.svg`, `placeholder.jpg`, `placeholder-user.jpg` | Local fallback silhouettes | Geometric SVG / placeholder vectors | Public domain / created in-house | None |
| `lucide-react` icons (throughout frontend) | UI icons | Lucide project | ISC License (Permissive open source) | Fully compliant |
| Meta Ad Library Thumbnails | Scraped public creative thumbnails | Direct from Meta transparency repository | Third-party public ad collateral (Nominative fair use for indexing) | Clear disclaimer on public sources and takedown request path |

---

## 7. Automated Axe Accessibility Audit (WCAG 2.2 AA)

A complete automated scan was executed using Playwright and `axe-core` 4.10.2 against all 12 key public and authenticated views of Helix Intelligence:

### Summary of Audit Results
| Route / Surface | Accessibility Violations | Impact Level | Status |
|---|---|---|---|
| **Landing Page (`/`)** | 1 | Critical | Action Needed |
| **Sign In (`/sign-in`)** | 1 | Critical | Action Needed |
| **Sign Up (`/sign-up`)** | 1 | Critical | Action Needed |
| **Docs Overview (`/docs`)** | 2 | 1 Critical, 1 Serious | Action Needed |
| **Docs Detail (`/docs/user-guide/quickstart-account-and-trial`)** | 0 | None | **Pass (Clean)** |
| **Public Playbook (`/public-playbook`)** | 1 | Critical | Action Needed |
| **Discover Console (`/discover`)** | 0 | None | **Pass (Clean)** |
| **Intelligence Console (`/intelligence`)** | 1 | Critical | Action Needed |
| **Create Studio (`/create`)** | 0 | None | **Pass (Clean)** |
| **Monitors Console (`/monitors`)** | 1 | Critical | Action Needed |
| **Performance Console (`/performance`)** | 0 | None | **Pass (Clean)** |
| **Scout Lead Gen (`/scout`)** | 0 | None | **Pass (Clean)** |

### Specific Violations Identified

#### 1. `aria-required-parent` (Critical — 5 pages: `/`, `/sign-in`, `/sign-up`, `/docs`, `/public-playbook`)
- **Element**: `.pill-logo` inside `src/components/ui/PillNav.jsx:234`
- **Issue**: The logo `<Link>` carries `role="menuitem"`, but its parent container `<nav>` is not a `role="menubar"` or `role="menu"` (the `role="menubar"` is placed further down on the child `<ul>`).
- **Remediation**: Remove `role="menuitem"` from the home logo link, or place the logo inside a semantic landmark with appropriate hierarchy.

#### 2. `target-size` (Serious — 1 page: `/docs`)
- **Element**: Category sub-links in `src/pages/docs/DocsOverviewPage.jsx` (`.gap-1.5.hover:text-accent.items-center`)
- **Issue**: Touch target height/width is below the WCAG 2.2 AA minimum threshold (24x24 CSS pixels) with insufficient spacing.
- **Remediation**: Add `py-1` or `min-h-[28px]` touch padding to doc navigation anchor links.

#### 3. `select-name` (Critical — 2 pages: `/intelligence`, `/monitors`)
- **Elements**: 
  - `src/pages/IntelligencePage.jsx:481`: `<select value={timeWindow}>`
  - `src/pages/MonitorsPage.jsx:131`: `<select value={filter}>`
- **Issue**: `<select>` dropdown elements lack an accessible name (`aria-label` or `<label for="...">`).
- **Remediation**: Add `aria-label="Filter intelligence by timeframe"` and `aria-label="Filter monitors by status"`.

---

## 8. Wave Roadmap & Action Plan

1. **Wave L1 (Legal Pages)**:
   - Create accessible routes: `/privacy`, `/terms`, `/cookies`, `/refunds`, `/legal`.
   - Update footer links from modal popups to direct accessible routes.
   - Include public data removal/takedown contact path.
   - Display "Last updated: September 30, 2026".
2. **Wave L2 (Consent & Data Minimisation)**:
   - Implement cookie notice / modular consent component behind a feature flag.
   - Add explicit consent checkbox to signup and contact forms with separate marketing opt-in.
   - Implement self-service "Delete my account and data" and "Export my data" (JSON).
3. **Wave L3 (Honesty Cleanup)**:
   - Replace fictitious ticking counter with truthful descriptive beta metrics.
   - Label simulated terminal scenarios and preview cards with "Demonstration Example".
   - Replace hardcoded "All systems operational" with honest status or real health ping.
   - Purge false "SOC2" and "99.9% SLA" claims.
4. **Wave L4 (Accessibility WCAG 2.2 AA)**:
   - Fix `.pill-logo` ARIA role parent mismatch.
   - Fix `<select>` accessible naming in Intelligence and Monitors.
   - Increase touch targets in Docs overview to 24px+.
   - Add skip-to-content and verify keyboard navigation.
