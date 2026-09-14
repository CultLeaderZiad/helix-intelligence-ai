# Core Concepts: The Creative Scoring System

Helix evaluates every discovered ad using a calibrated, multimodal evaluation pipeline. This page breaks down how each score is calculated and how to use it.

---

## The Four Signal Scores

Rather than guessing which ads convert, Helix computes four distinct signals (0–100) for every creative:

### 1. Hook Score
> **In-App Definition:** *"How strongly the opening grabs attention in the first seconds."*

- **What it analyzes**: The first 1 to 3 seconds of video or the primary focal visual of a static ad.
- **Evaluation factors**: Pattern interrupt, unexpected movement, text overlay contrast, audio/voice entry speed, and emotional tension.
- **Interpretation**:
  - `80–100 (Tier A)`: Strong stop-scrolling power. Overcomes feed fatigue.
  - `60–79 (Tier B)`: Average opening hook. Competent but conventional.
  - `<60 (Tier C)`: Weak entry. Slow logo reveals or talking head introductions that lose viewers before the value proposition.

---

### 2. Clarity Score
> **In-App Definition:** *"How obvious the offer and message are at a glance."*

- **What it analyzes**: Cognitive load, headline readability, value proposition clarity, and call to action.
- **Evaluation factors**: Can a viewer state what problem this product solves within 4 seconds of viewing?
- **Interpretation**:
  - `80–100 (Tier A)`: Crystal clear message, direct benefit headline, friction-free CTA.
  - `60–79 (Tier B)`: Understandable, but requires reading fine print or waiting for a mid-video reveal.
  - `<60 (Tier C)`: Confusing claims, vague abstractions, or cluttered visual hierarchy.

---

### 3. Retention Score
> **In-App Definition:** *"How likely people are to keep watching instead of scrolling away."*

- **What it analyzes**: Narrative pacing, scene duration, visual transitions, and progressive information disclosure.
- **Evaluation factors**: Are cuts occurring every 1.5–2.5 seconds? Does each section create curiosity for the next sentence?
- **Interpretation**:
  - `80–100 (Tier A)`: High-energy pacing, active B-roll, dynamic text sync that keeps retention high.
  - `60–79 (Tier B)`: Steady pacing; some static segments.
  - `<60 (Tier C)`: Monotonous delivery or prolonged static screens.

---

### 4. Composite Score
> **In-App Definition:** *"One combined 0–100 signal from the three scores above (not reported by Meta or ad platform)."*

- **Formula**: A weighted index combining `Hook (40%)`, `Clarity (35%)`, and `Retention (25%)`.
- **Purpose**: Gives you a single sortable benchmark to rank hundreds of competitor creatives instantly.
- **Platform Transparency**: Neither Meta, TikTok, nor Google reports a composite quality score for competitor ads in their ad libraries. This is a proprietary computational metric derived by Helix.

---

## Durability vs. Score: Finding Hidden Winners

A high score is valuable, but the ultimate validation is **Durability** (*Days Active*):
- An ad with an `85` Composite Score that has been live for **35 days** is a proven, battle-tested money-maker.
- If you find an ad with a `68` Composite Score that has been active for **60 days**, study its underlying offer and economics — durability proves that real customers are buying.

👉 [Estimated vs. Real Data Standards](/docs/user-guide/concept-estimated-vs-real-data)
