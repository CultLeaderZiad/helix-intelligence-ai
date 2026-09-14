# Quick Start: Credit Balances & Daily Limits

Helix Intelligence uses a transparent credit ledger. Every loop and operation has an explicit credit cost tied to real compute.

---

## 1. Where to Find Your Balance

You can check your credit standing and consumption at any time:

1. **Top Workspace Banner**: Displays your remaining daily credits and active trial countdown.
2. **Billing & Meter Page**: Visit [/billing](/billing) in your workspace sidebar for:
   - Total Organization Credit Balance.
   - Daily Quota Used today vs. Daily Maximum.
   - Exact UTC Reset Timestamp (**00:00 UTC**).
   - Historical consumption graph and itemized audit log.

---

## 2. In-App Credit Cost Schedule

Every operation deducts a fixed number of credits. These values match the live system billing engine:

| Action | Cost (Credits) | Real Operation |
| :--- | :--- | :--- |
| **Discover Search Job** | `1.0` | Live ad library scrape across Meta, TikTok, and Google Ads indexes. |
| **Discover Deep Fallback** | `2.0` | Extended multi-page deep extraction when a brand has sparse recent ads. |
| **AI Creative Insight** | `0.5` | Deep LLM hook breakdown, angle classification, and script transcription. |
| **Pattern Pack Extraction** | `0.5` | Clustering winning angles across a brand's top 10 ads into a reusable blueprint. |
| **AI Assistant Query** | `0.25` | Asking questions to the interactive creative advisor in Discover/Intelligence. |
| **Audience Simulation** | `1.0` | Running multi-persona synthetic audience rehearsal on a creative brief. |
| **Generate Image Asset** | `2.0` | Higgsfield AI text-to-image or remix visual generation. |
| **Generate Video Asset** | `5.0` | Higgsfield AI motion-video render. |

---

## 3. Daily Limits and Auto-Reset

To safeguard against runaway loops, accounts have daily limits:
- **Daily Trial Limit**: Up to 20 discovery requests / 25 credits per day during the trial.
- **Pro / Scale Plans**: Higher daily ceilings (up to 500+ credits/day) with unlimited total pool.
- **Daily Reset Time**: All daily consumption counters automatically reset at **00:00:00 UTC** every night.

> [!TIP]
> If an extraction job fails due to an upstream ad-network timeout or transient connection issue, **credits are automatically refunded** to your balance. Helix never charges you for an incomplete run.

---

## Next Steps: Core Concepts

Now that you understand the basic workflow, explore our Core Concepts to understand how Helix works under the hood:

👉 [What Discover Actually Does (and Its Limits)](/docs/user-guide/concept-how-discover-works)
