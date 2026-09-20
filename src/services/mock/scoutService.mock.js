/**
 * Scout Mock Service with Sample-labeled Leads
 * Only active when VITE_DATA_SOURCE === 'mock'
 */

let mockJob = null
let mockLeads = [
  {
    id: "lead_sample_01",
    job_id: "job_scout_sample",
    platform: "instagram",
    handle: "@sample_dermatology",
    name: "[Sample] Riyadh Dermatology & Aesthetics",
    email: "contact@sampleclinic.sa",
    phone: "+966 11 000 0000",
    website: "https://sampleclinic.sa",
    followers: 48500,
    lead_score: 82,
    scrape_status: "ok",
    account_type: "business",
    priority_level: "high",
    bio: "[Sample] Premier medical aesthetics & laser clinic in Riyadh. Inquiries: contact@sampleclinic.sa",
    sources: { email_source: "bio", confidence: 95, phone_source: "website_crawl", priority: "high", account_type: "business", primary_niche: "Aesthetics & Healthcare" },
    atlas: {
      profile_analysis: {
        account_type: "business",
        primary_niche: "Aesthetics & Healthcare",
        secondary_niches: ["Beauty", "Dermatology"],
        influence_level: "micro",
        engagement_metrics: {
          follower_count: 48500,
          avg_engagement_rate: 0.038,
          engagement_quality: "medium"
        }
      },
      lead_scoring: {
        relevance_score: 82,
        priority_level: "high",
        category_match: "Matched 3/3 target context keywords: aesthetics, clinic, MENA",
        reasoning: "Score 82/100 [Category: 36/40, Engagement/Contact: high, Influence: micro]. Priority: HIGH."
      },
      enrichment_data: {
        email: "contact@sampleclinic.sa",
        email_source: "bio",
        phone: "+966 11 000 0000",
        website: "https://sampleclinic.sa",
        key_topics: ["Aesthetics & Healthcare", "Beauty", "Dermatology"],
        content_sentiment: "positive"
      },
      outreach: {
        email_subject: "Operational AI partnership for Riyadh Dermatology",
        email_body: "Hi team,\n\nI reviewed your recent clinical showcases on Instagram (@sample_dermatology) and noticed your patient volume growth across Riyadh. We assist premier aesthetic clinics in automating patient booking triage.\n\nWould you be open to a 5-minute conversation on streamlining inquiries?\n\nBest regards,\nHelix Intelligence",
        dm_body: "Hey there! Impressed by your aesthetic treatment cases in Riyadh. Would love to connect regarding operational efficiency for your clinic team.",
        personalization_points: ["Referenced aesthetic treatment focus", "Noted Riyadh clinic location", "Addressed patient booking triage"]
      },
      meta: {
        platform: "instagram",
        handle: "sample_dermatology",
        profile_url: "https://instagram.com/sample_dermatology",
        scrape_status: "ok",
        error: null
      }
    },
    created_at: new Date().toISOString(),
  },
  {
    id: "lead_sample_02",
    job_id: "job_scout_sample",
    platform: "github",
    handle: "cultleaderziad",
    name: "[Sample] Ziad Sabry",
    email: null,
    phone: null,
    website: "https://github.com/cultleaderziad",
    followers: 420,
    lead_score: 48,
    scrape_status: "ok",
    account_type: "personal",
    priority_level: "low",
    bio: "[Sample] Fullstack & AI systems engineer · Open-source contributor",
    sources: { email_source: null, priority: "low", account_type: "personal", primary_niche: "Software / AI" },
    atlas: {
      profile_analysis: {
        account_type: "personal",
        primary_niche: "Software / AI",
        secondary_niches: ["Open Source"],
        influence_level: "nano",
        engagement_metrics: {
          follower_count: 420,
          avg_engagement_rate: null,
          engagement_quality: "unknown"
        }
      },
      lead_scoring: {
        relevance_score: 48,
        priority_level: "low",
        category_match: "Technical developer profile",
        reasoning: "Score 48/100 [Category: 20/40, Engagement/Contact: unknown, Influence: nano]. Priority: LOW."
      },
      enrichment_data: {
        email: null,
        email_source: null,
        phone: null,
        website: "https://github.com/cultleaderziad",
        key_topics: ["Software / AI", "Open Source"],
        content_sentiment: "neutral"
      },
      outreach: {
        email_subject: "",
        email_body: "",
        dm_body: "",
        personalization_points: []
      },
      meta: {
        platform: "github",
        handle: "cultleaderziad",
        profile_url: "https://github.com/cultleaderziad",
        scrape_status: "ok",
        error: null
      }
    },
    created_at: new Date().toISOString(),
  }
]

export const scoutMock = {
  async submitJob(params) {
    const jobId = `job_scout_sample_${Math.random().toString(36).substring(2, 7)}`
    mockJob = {
      job_id: jobId,
      status: "running",
      stage: "scrape",
      stage_label: "stage 2/4 scraping platforms",
      stage_index: 2,
      stages_total: 4,
      logs: [
        `> engine: helix_scout_atlas/v2 (Sample mock mode) · ok`,
        `> platforms: ${params.platforms?.join(", ") || "instagram, github"}`,
        `> sample:sample_dermatology · ok`,
      ],
      leads_count: 0,
      elapsed_ms: 1200,
      credits_used: 2.5,
      error_msg: null,
      created_at: new Date().toISOString(),
      completed_at: null,
    }
    return { ...mockJob }
  },

  async getJob(jobId) {
    if (!mockJob) {
      mockJob = {
        job_id: jobId || "job_scout_sample",
        status: "succeeded",
        stage: "complete",
        stage_label: "stage 4/4 complete",
        stage_index: 4,
        stages_total: 4,
        logs: [
          "> sample:sample_dermatology · ok",
          "> github:cultleaderziad · ok",
          "> atlas · scored and enriched",
        ],
        leads_count: mockLeads.length,
        elapsed_ms: 3200,
        credits_used: 2.5,
        error_msg: null,
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      }
    }
    return { ...mockJob }
  },

  async getLeads(jobId) {
    return {
      job_id: jobId,
      total: mockLeads.length,
      items: [...mockLeads],
    }
  },

  async getSettings() {
    return {
      hunter_configured: false,
      linkedin_configured: false,
      proxy_configured: true,
      engine: "helix_scout_atlas (kiryano/Scout MIT)",
    }
  },

  async updateSettings(data) {
    return { success: true, ...data }
  },

  async exportCsv(jobId) {
    const header = "id,handle,platform,type,score,priority,email,phone,website,status\n"
    const rows = mockLeads
      .map((l) => `${l.id},${l.handle},${l.platform},${l.account_type},${l.lead_score},${l.priority_level},${l.email || ""},${l.phone || ""},${l.website || ""},${l.scrape_status}`)
      .join("\n")
    const blob = new Blob([header + rows], { type: "text/csv" })
    return blob
  },

  async getOrgJobs() {
    return {
      items: [
        {
          job_id: "job_scout_sample",
          status: "succeeded",
          total_handles: 2,
          leads_count: 2,
          created_at: new Date().toISOString(),
        },
      ],
    }
  },
}

export default scoutMock
