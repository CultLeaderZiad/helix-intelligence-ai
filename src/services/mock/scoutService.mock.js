/**
 * Scout Mock Service with Realistic Sample Leads
 * (Matching Helix Intelligence exact tokens & mock data)
 */

let mockJob = null
let mockLeads = [
  {
    id: "lead_01",
    job_id: "job_scout_8f2a",
    platform: "instagram",
    handle: "@helixagency",
    name: "Helix Agency",
    email: "hello@helixx.xo.je",
    phone: "+966 50 123 4567",
    website: "helixx.xo.je",
    followers: 12400,
    lead_score: 78,
    bio: "MENA AI ops · WhatsApp receptionist · book a build",
    sources: { email_source: "bio", confidence: 90, phone_source: "bio_link" },
    created_at: new Date().toISOString(),
  },
  {
    id: "lead_02",
    job_id: "job_scout_8f2a",
    platform: "github",
    handle: "cultleaderziad",
    name: "Ziad Sabry",
    email: null,
    phone: null,
    website: "https://github.com/cultleaderziad",
    followers: 320,
    lead_score: 42,
    bio: "Fullstack & AI systems engineer · Open-source contributor",
    sources: { email_source: null },
    created_at: new Date().toISOString(),
  },
  {
    id: "lead_03",
    job_id: "job_scout_8f2a",
    platform: "linktree",
    handle: "acme_clinic_sa",
    name: "Acme Clinic",
    email: "info@acme.sa",
    phone: "+966 11 456 7890",
    website: "https://acme.sa",
    followers: 5800,
    lead_score: 65,
    bio: "Leading aesthetics and wellness clinic in Riyadh · Booking via WhatsApp",
    sources: { email_source: "bio", confidence: 85, phone_source: "whatsapp" },
    created_at: new Date().toISOString(),
  },
]

export const scoutMock = {
  async submitJob(params) {
    const jobId = `job_scout_${Math.random().toString(36).substring(2, 7)}`
    mockJob = {
      job_id: jobId,
      status: "running",
      stage: "scrape",
      stage_label: "stage 2/4 scraping platforms",
      stage_index: 2,
      stages_total: 4,
      logs: [
        `> engine: helix_scout/v1 (MIT adapted) · ok`,
        `> platforms: ${params.platforms?.join(", ") || "github, linktree"}`,
        `> github:cultleaderziad · ok`,
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
        job_id: jobId || "job_scout_8f2a",
        status: "succeeded",
        stage: "complete",
        stage_label: "stage 4/4 complete",
        stage_index: 4,
        stages_total: 4,
        logs: [
          "> github:cultleaderziad · ok",
          "> instagram:helixagency · ok",
          "> linktree · enrich email · verified 72%",
        ],
        leads_count: mockLeads.length,
        elapsed_ms: 4200,
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

  async getOrgJobs() {
    return {
      items: [
        {
          job_id: "job_scout_8f2a",
          status: "succeeded",
          stage: "complete",
          stage_label: "Complete",
          handles_count: 3,
          leads_count: 3,
          credits_used: 2.5,
          created_at: new Date(Date.now() - 3600000).toISOString(),
        },
      ],
    }
  },

  async exportCsv(jobId) {
    const csvContent = [
      "Handle,Platform,Name,Email,Phone,Website,Followers,Score,Bio",
      ...mockLeads.map(
        (l) =>
          `"${l.handle}","${l.platform}","${l.name || ""}","${l.email || ""}","${l.phone || ""}","${l.website || ""}",${l.followers},${l.lead_score},"${(l.bio || "").replace(/"/g, '""')}"`
      ),
    ].join("\n")

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.setAttribute("download", `helix_scout_leads_${jobId || "export"}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    return { status: "ok" }
  },

  async getSettings() {
    return {
      hunter_configured: false,
      linkedin_configured: false,
      smtp_configured: false,
      proxy_status: "Managed Residential Pool (active)",
      free_proxy_allowed: false,
    }
  },

  async updateSettings(settings) {
    return { status: "ok", message: "Settings saved" }
  },
}

export default scoutMock
