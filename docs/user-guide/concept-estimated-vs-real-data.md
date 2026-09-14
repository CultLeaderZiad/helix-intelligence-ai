# Core Concepts: Estimated vs. Real Data

Trust is the foundation of competitive intelligence. Many legacy ad spy tools invent fake spend figures and fabricate click-through rates. **Helix has a strict policy: we never fabricate data.**

Every metric in Helix is explicitly classified and visually labeled as either **Verified Direct Data** or **Modeled Estimate**.

---

## 1. The Labeling System

Throughout the application and API, you will see explicit indicators:

| UI Badge / API Field | Meaning | Underlying Data Source |
| :--- | :--- | :--- |
| **No Badge / Direct** | 100% verified factual data from the ad library. | Pulled directly from Meta, TikTok, or Google ad records. |
| `(est)` / `is_impression_estimate: true` | Modeled calculation based on observed reach and durability. | Estimated using public audience buckets, regional reach, and engagement ratios. |
| `source_type: "ad"` | Verified paid commercial advertisement. | Active campaign from verified ad library profile. |
| `source_type: "organic_content_proxy"` | High-performing organic brand asset indexed as an ad creative proxy. | Public brand account posting. |

---

## 2. What Is 100% Real & Verified?

The following data points are factual records extracted directly from official transparency libraries:
- **Exact Verbatim Copy**: Headlines, body copy, descriptions, and CTA button text.
- **Media Assets**: The actual MP4 video files, audio tracks, and JPG/PNG creatives rendered by the advertiser.
- **First Seen & Last Seen Dates**: Exact timestamps when the ad was first indexed and last verified running.
- **Days Active (Durability)**: The calculated duration between first seen and today.
- **Landing Page URLs**: The exact redirect domain and destination landing page linked to the ad.
- **Publisher Platforms**: The specific placements (Facebook Feed, Instagram Reels, TikTok For You, Google Search/YouTube).

---

## 3. What Is an Estimate (and How It Is Modeled)?

Ad networks do not give competitors access to an advertiser's private billing receipt. Therefore, the following metrics are modeled estimates:

### Impressions Estimate (`impressions_est`)
- **How we model it**: We observe public regional reach bands, audience size classifications, engagement counts (likes, shares, comments), and the length of time the creative has remained active.
- **Why we label it**: Marked with an amber `(est)` badge in the UI and `is_impression_estimate: true` in the API. We do not pretend it is an internal ad manager pixel readout.

### Spend Bands (`spend_band`)
- Modeled as brackets (e.g. `$1k–$5k`, `$10k–$50k`, `$100k+`) rather than misleading exact numbers (like `$14,289.43`).
- Bracket calculation correlates durability, format, and multi-region deployment.

---

## 4. Our Engineering Promise

1. **No Fake Numbers**: If we cannot credibly estimate a metric, we show `—` (Not Available) rather than inventing a placeholder.
2. **Transparent Schemas**: In both the web console and the REST API, every estimated metric carries a corresponding boolean flag (`is_impression_estimate`).
3. **Auditable Lineage**: You can inspect the destination landing page and ad library identifier for every creative to verify its existence yourself.

👉 [Competitor Monitors & Alerting](/docs/user-guide/concept-competitor-monitors)
