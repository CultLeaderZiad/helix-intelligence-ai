# User Guide: Frequently Asked Questions (FAQ)

Honest answers to the most common questions and confusion points encountered while using Helix.

---

### Why did my search return no results?

There are three primary reasons a search might return zero records:

1. **The brand has no active paid ads right now**:
   - Ad transparency libraries (like Meta Ad Library) only catalog creatives that have been actively running within recent weeks. If a competitor paused their campaigns last month, the ad library marks them inactive and removes them from public queries.
2. **The entity name does not match the advertiser's registered page**:
   - For example, searching for a popular streamer or influencer might not return their personal brand if their ad campaigns are billed under a parent company, media holding company, or agency name. Try searching for their official product line (e.g., searching for their supplement or apparel brand rather than their personal alias).
3. **Transient upstream library rate limiting**:
   - If an ad network throttles public requests, Helix attempts deep fallback searches. If the network continues timing out, the search terminates and **your credits are automatically refunded**.

---

### What is the difference between estimated and reported data?

- **Reported Data** is 100% factual, public record: the verbatim headlines, ad body copy, video MP4 files, thumbnail images, first-seen timestamps, and days active.
- **Estimated Data** applies to metrics like Impressions (`impressions_est`) and Spend Bands. Ad networks never disclose private advertiser bank receipts. Helix models these numbers using public reach brackets, durability, and engagement signals. Estimated metrics are always explicitly tagged with an amber `(est)` badge so you always know what is directly reported versus modeled.

---

### What happens when my 7-day trial ends?

- During the 7-day trial, you receive 100 credits and up to 20 daily searches.
- When the 7 days elapse, your account enters **Read-Only Mode**:
  - All previously discovered creatives, saved swipe files, and generated briefs remain saved and accessible.
  - New discovery searches, media generations, and monitor scrapes will be paused until you choose a paid plan (Starter, Pro, or Scale).
  - You will never be automatically billed or charged without entering your payment details.

---

### Why did a search for a content creator return shoe or product ads?

Ad libraries index paid advertising campaigns, not organic social media posts or TikTok feeds. If a creator or public figure does not run paid ads for their own company, a generic keyword search may return unrelated advertisers who happened to mention similar keywords or who ran sponsored affiliate ads. 

To audit a specific entity:
- Search by the creator's exact **product line** or **brand name**.
- Or use the **Organic Proxy** filter if looking for indexed public video assets.

---

### Are credits refunded if a job fails?

**Yes, 100%.** If an ad-network timeout, service interruption, or network disconnect occurs while processing your request, the backend billing engine immediately refunds the deducted credits to your workspace balance. Helix never charges for unfinished work.

---

### How do I translate foreign language ads into English?

Helix automatically detects foreign language copy (Spanish, Chinese, Arabic, French, German, Dutch, etc.).
- When viewing a creative in the **Intelligence** drawer or **Intelligence** page, use the language selector to immediately render an English translation of the headline, body text, and call to action.

---

### Still have questions?

Reach out directly to our team via the [Support & Feedback](/support) portal in your workspace.
