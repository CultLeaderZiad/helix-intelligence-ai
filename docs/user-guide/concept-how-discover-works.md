# Core Concepts: How Discover Works & Real Limits

Discover is Helix's competitive ad intelligence engine. This guide explains where data comes from, what Helix actually does, and the technical boundaries of ad library data.

---

## 1. Where Does the Data Come From?

When you submit a query in Discover, Helix dispatches extraction workers to public ad transparency libraries, including:
- **Meta Ad Library** (Facebook, Instagram, Messenger, Audience Network)
- **TikTok Commercial Content Library**
- **Google Ads Transparency Center**

Helix indexes, normalizes, and enriches these creative assets so you can search them semantically rather than relying on manual page scrolling.

---

## 2. What Helix Actually Does

1. **Entity Resolution**: When you search for a brand (e.g. `Hims`), Helix identifies the brand's verified public ad profile IDs across networks.
2. **Catalog Ingestion**: Extracts active creatives, including video MP4 links, high-res static images, verbatim headlines, primary copy, and landing page URLs.
3. **Multimodal Analysis**: Transcribes video speech, OCRs on-screen text, evaluates opening visual cuts, and extracts psychological hooks.
4. **Performance Durability Tracking**: Tracks how long an ad has been continuously running by comparing historical and current first-seen/last-seen timestamps.

---

## 3. Honest Limits & Platform Boundaries

To set clear expectations, here are the real-world limits of public ad data:

### Not Every Platform Is Covered
- **Meta & TikTok** provide robust, real-time public libraries with good coverage of western and global DTC advertisers.
- **Twitter / X & LinkedIn** have restricted or non-standardized transparency libraries. Coverage on these networks is partial or proxy-based.
- **Private In-App Placements**: Dark ads shown only to narrow custom audience lists (e.g. customer email lists) may not appear immediately if not cataloged by the network's public repository.

### Spend Numbers Are Not Public
- Ad platforms **never** publish exact dollar figures spent on commercial ads (except for political/social issue campaigns).
- Any spend figures or impression ranges displayed in Helix are **modeled estimates** derived from duration, engagement signals, and audience tier proxies.
- We never pretend an estimate is a raw reported metric. See [Estimated vs. Real Data](/docs/user-guide/concept-estimated-vs-real-data).

### Network Latency & Freshness
- When an advertiser launches a brand-new ad, platforms typically take 4 to 24 hours to publish it to their transparency databases. Discover searches index ads that have completed platform indexing.

---

## Summary

Discover provides unprecedented visibility into competitor angles, durability, and messaging strategies, but it is bounded by public ad library infrastructure. When you use Helix, you are seeing real public ad records, labeled honestly.

👉 [Learn About the Scoring System](/docs/user-guide/concept-scoring-system)
