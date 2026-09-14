# Core Concepts: Competitor Monitors & Alerts

Instead of manually running repetitive searches every morning, **Monitors** automate recurring competitor audits and alert you the moment new angles or campaigns launch.

---

## 1. What a Monitor Does

A Monitor is a persistent background watcher configured with a query and target parameters:
- It runs on a scheduled cadence (**Daily** or **Weekly**).
- It queries ad libraries for new creatives launched by specified brands or within a niche.
- It detects significant shifts:
  - **New Angle Launches**: A competitor begins testing a completely new hook or product claim.
  - **Surviving Evergreen Alerts**: An ad surpasses 14+ days of continuous spend.
  - **Creative Fatigue**: A previously high-volume ad is shut down after days of declining engagement.

---

## 2. Setting Up a Monitor

1. Navigate to **Monitors** ([/monitors](/monitors)) in your workspace sidebar.
2. Click **Create Monitor**.
3. Provide:
   - **Query**: The competitor brand or niche search term (e.g. `Ag1 Athletic Greens`, `liquid IV hydration`).
   - **Cadence**: `Daily` (recommended for active direct response spaces) or `Weekly`.
   - **Notification Channels**:
     - **In-App Notification**: Live badge update and alert feed inside Helix.
     - **Email Digest**: Weekly or daily briefing sent to your account email.

---

## 3. Monitor Events & Webhook Feeds

Every run of a monitor generates an audit log of **Events**:
- `new_creative_detected`: Triggered when an ad appears for the first time.
- `evergreen_milestone`: Triggered when an ad reaches 14, 30, or 60 days active.
- `angle_cluster_shift`: Triggered when an advertiser pivots more than 30% of their ad volume to a new visual format (e.g., shifting from founder interviews to UGC unboxing).

If you are using Helix via the API, monitor events can also trigger webhooks straight into your Slack channels or internal databases. See [API Reference: Monitors](/docs/api-reference/endpoint-monitors).

👉 [Audience Simulation: Creative Rehearsal](/docs/user-guide/concept-audience-simulation)
