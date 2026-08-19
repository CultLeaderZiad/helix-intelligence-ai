/**
 * Analysis insight fixtures.
 *
 * Modelled as the output of an async analysis worker: each insight
 * carries provenance (`evidence_creative_ids`), a confidence value and
 * a generation timestamp — never a bare string. The UI is therefore
 * obliged to show where a claim came from.
 */

export const insights = [
  {
    id: "ins_4a10",
    creative_id: "crv_9f2a01",
    kind: "hook_analysis",
    title: "Negation opener carries the hook",
    summary:
      "The opening clause removes a behaviour rather than adding a product. Across the sampled set, reduction-framed openers hold attention ~1.3x longer than feature-led openers in the first two seconds.",
    confidence: 0.82,
    evidence_creative_ids: ["crv_9f2a01", "crv_9f2a08", "crv_9f2a26"],
    generated_at: "2026-08-18T09:41:00Z",
    model_version: "helix-analysis-0.4",
  },
  {
    id: "ins_4a11",
    creative_id: "crv_9f2a01",
    kind: "risk",
    title: "Claim density may trigger review",
    summary:
      "Two implicit efficacy claims appear without qualifying language. Comparable creatives in this category saw elevated rejection rates on Meta.",
    confidence: 0.61,
    evidence_creative_ids: ["crv_9f2a01", "crv_9f2a09"],
    generated_at: "2026-08-18T09:41:00Z",
    model_version: "helix-analysis-0.4",
  },
  {
    id: "ins_4a12",
    creative_id: "crv_9f2a06",
    kind: "hook_analysis",
    title: "Verifiable test structure drives share rate",
    summary:
      "A stated method with a countable setup invites the viewer to predict the outcome. Blind-test framing is rare (3% prevalence) but shows the highest lift index in the current taxonomy.",
    confidence: 0.88,
    evidence_creative_ids: ["crv_9f2a06", "crv_9f2a19", "crv_9f2a07"],
    generated_at: "2026-08-18T10:02:00Z",
    model_version: "helix-analysis-0.4",
  },
  {
    id: "ins_4a13",
    creative_id: "crv_9f2a06",
    kind: "opportunity",
    title: "Format is under-exploited on Meta",
    summary:
      "This brand runs blind-test creative only on TikTok. No competitor in the pet category runs the format on Meta video, where the brand already has spend history.",
    confidence: 0.74,
    evidence_creative_ids: ["crv_9f2a06", "crv_9f2a13"],
    generated_at: "2026-08-18T10:02:00Z",
    model_version: "helix-analysis-0.4",
  },
  {
    id: "ins_4a14",
    creative_id: "crv_9f2a26",
    kind: "hook_analysis",
    title: "Self-penalising disclosure as credibility device",
    summary:
      "The claim costs the advertiser money, which removes the usual scepticism response. Engagement rate is 11.4% — the highest in the sampled set, on the lowest spend band.",
    confidence: 0.79,
    evidence_creative_ids: ["crv_9f2a26", "crv_9f2a28", "crv_9f2a23"],
    generated_at: "2026-08-18T11:15:00Z",
    model_version: "helix-analysis-0.4",
  },
  {
    id: "ins_4a15",
    creative_id: "crv_9f2a03",
    kind: "opportunity",
    title: "Quantified gap outperforms generic pain framing",
    summary:
      "Naming both the current and median figure gives the reader a self-diagnosis in one line. Clarity score of 9.4 is the highest recorded for a B2B static in this set.",
    confidence: 0.71,
    evidence_creative_ids: ["crv_9f2a03", "crv_9f2a16"],
    generated_at: "2026-08-18T08:30:00Z",
    model_version: "helix-analysis-0.4",
  },
]

export const insightsByCreativeId = insights.reduce((acc, i) => {
  if (!acc[i.creative_id]) acc[i.creative_id] = []
  acc[i.creative_id].push(i)
  return acc
}, {})
