/**
 * Maps Scout Mock Service — Sample Fixtures explicitly labeled
 * (Attribution: Mahanaicoach/google-maps-scraper-kit & gosom)
 */

let mockMapsJob = null

const SAMPLE_MAPS_LEADS = [
  {
    id: "sample_map_01",
    job_id: "job_maps_sample_1",
    title: "[Sample] Al Habib Medical Center - Olaya",
    phone: "+966 11 283 3333",
    email: "contact@drsulaimanalhabib.com",
    emails_found: ["contact@drsulaimanalhabib.com", "info@drsulaimanalhabib.com"],
    website: "https://drsulaimanalhabib.com",
    category: "Medical Clinic / Specialty Dentistry",
    address: "King Fahd Rd, Al Olaya, Riyadh 12214",
    city: "Riyadh, SA",
    rating: 4.8,
    reviews_count: 420,
    instagram: "https://instagram.com/drsulaimanalhabib",
    facebook: "https://facebook.com/drsulaimanalhabib",
    linkedin: "https://linkedin.com/company/dr-sulaiman-al-habib-medical-group",
    twitter: "https://x.com/drsulaimanalhab",
    socials: {
      instagram: "https://instagram.com/drsulaimanalhabib",
      linkedin: "https://linkedin.com/company/dr-sulaiman-al-habib-medical-group",
    },
    created_at: new Date().toISOString(),
  },
  {
    id: "sample_map_02",
    job_id: "job_maps_sample_1",
    title: "[Sample] Riyadh Smile Dental Center",
    phone: "+966 11 419 8888",
    email: "appointments@riyadhsmile.com",
    emails_found: ["appointments@riyadhsmile.com"],
    website: "https://riyadhsmile.com",
    category: "Dental Clinic",
    address: "Tahlia St, Al Olaya, Riyadh 12331",
    city: "Riyadh, SA",
    rating: 4.6,
    reviews_count: 184,
    instagram: "https://instagram.com/riyadhsmile",
    facebook: null,
    linkedin: null,
    twitter: null,
    socials: {
      instagram: "https://instagram.com/riyadhsmile",
    },
    created_at: new Date().toISOString(),
  },
  {
    id: "sample_map_03",
    job_id: "job_maps_sample_1",
    title: "[Sample] Elite Specialist Hospital & Clinics",
    phone: "+966 11 461 6777",
    email: "info@elitehospital.com.sa",
    emails_found: ["info@elitehospital.com.sa"],
    website: "https://elitehospital.com.sa",
    category: "Hospital & Surgery",
    address: "Makkah Al Mukarramah Branch Rd, Riyadh 12311",
    city: "Riyadh, SA",
    rating: 4.4,
    reviews_count: 310,
    instagram: null,
    facebook: "https://facebook.com/elitehospitalsa",
    linkedin: "https://linkedin.com/company/elitehospital",
    twitter: null,
    socials: {
      facebook: "https://facebook.com/elitehospitalsa",
    },
    created_at: new Date().toISOString(),
  },
]

export const mapsScoutMock = {
  async submitJob(params) {
    const jobId = `job_maps_${Math.random().toString(36).substring(2, 8)}`
    mockMapsJob = {
      job_id: jobId,
      keyword: params.keyword || "dentists",
      city: params.city || "Riyadh, SA",
      depth: params.depth || 5,
      status: "running",
      stage: "geocode",
      stage_label: `Geocoding location for '${params.city}'`,
      stage_index: 1,
      stages_total: 4,
      logs: [
        `> engine: helix_maps_scout/v1 (gosom/kit adapter) · ok`,
        `> target: '${params.keyword}' in '${params.city}' (depth=${params.depth})`,
        `> geocode: lat=24.7136, lon=46.6753 · resolved`,
      ],
      results_count: 0,
      elapsed_ms: 0,
      credits_used: 3.5,
      error_msg: null,
      created_at: new Date().toISOString(),
      completed_at: null,
    }
    return { ...mockMapsJob }
  },

  async getJob(jobId) {
    if (!mockMapsJob || mockMapsJob.job_id !== jobId) {
      return {
        job_id: jobId,
        status: "succeeded",
        stage: "complete",
        stage_label: "Maps Scout complete · 3 leads indexed",
        stage_index: 4,
        stages_total: 4,
        logs: [
          "> engine: helix_maps_scout/v1 · ok",
          "> sample job loaded",
          "> 3 sample business leads persisted",
        ],
        results_count: 3,
        elapsed_ms: 1800,
        credits_used: 3.5,
        created_at: new Date().toISOString(),
      }
    }
    // Advance progress
    if (mockMapsJob.stage_index < 4) {
      mockMapsJob.stage_index += 1
      if (mockMapsJob.stage_index === 2) {
        mockMapsJob.stage = "search"
        mockMapsJob.stage_label = `Scraping Google Maps directory for '${mockMapsJob.keyword}'`
        mockMapsJob.logs.push(`> search: queried directory, found 3 candidate listings`)
      } else if (mockMapsJob.stage_index === 3) {
        mockMapsJob.stage = "enrich"
        mockMapsJob.stage_label = "Extracting verified emails and social profiles from websites"
        mockMapsJob.logs.push(`> enrich: website HTTP contacts crawled · 3 emails found`)
      } else if (mockMapsJob.stage_index >= 4) {
        mockMapsJob.status = "succeeded"
        mockMapsJob.stage = "complete"
        mockMapsJob.stage_label = "Maps Scout complete · 3 leads indexed"
        mockMapsJob.results_count = 3
        mockMapsJob.logs.push(`> complete: 3 sample businesses indexed`)
      }
    }
    return { ...mockMapsJob }
  },

  async getLeads(jobId) {
    return {
      job_id: jobId,
      total: SAMPLE_MAPS_LEADS.length,
      items: SAMPLE_MAPS_LEADS,
    }
  },

  async getOrgJobs() {
    return {
      items: [
        {
          job_id: "job_maps_sample_1",
          status: "succeeded",
          keyword: "dentists",
          city: "Riyadh, SA",
          stage: "complete",
          stage_label: "Maps Scout complete",
          results_count: 3,
          credits_used: 3.5,
          created_at: new Date().toISOString(),
        }
      ]
    }
  },

  async exportCsv(jobId) {
    const csvContent = "Business Name,Phone,Email,Website,Category,Address,City,Rating,Reviews\n" +
      SAMPLE_MAPS_LEADS.map(l => `"${l.title}","${l.phone}","${l.email}","${l.website}","${l.category}","${l.address}","${l.city}",${l.rating},${l.reviews_count}`).join("\n")
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `sample_helix_maps_leads_${jobId.substring(0, 8)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    return { status: "ok" }
  },
}

export default mapsScoutMock
