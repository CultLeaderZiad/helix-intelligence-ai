/**
 * Static Docs Data Loader
 * Statically bundles all markdown documents from /docs with zero runtime CMS or database overhead.
 */

// Eagerly load raw markdown strings from docs/ directory
const markdownFiles = import.meta.glob('/docs/**/*.md', { query: '?raw', eager: true })

function getRawContent(relativePath) {
  const resolved = markdownFiles[`/docs/${relativePath}`]
  return typeof resolved === 'string' ? resolved : (resolved?.default || '')
}

export const DOCS_REGISTRY = [
  // ==========================================
  // SECTION A: USER GUIDE (Non-technical)
  // ==========================================
  {
    section: 'user-guide',
    sectionLabel: 'User Guide',
    audience: 'Marketers, growth operators, and creative strategists',
    groups: [
      {
        groupTitle: 'Quick Start',
        items: [
          {
            slug: 'quickstart-account-and-trial',
            title: 'Account & 7-Day Trial',
            description: 'Create an account and learn what is included in the 7-day trial.',
            file: 'user-guide/quickstart-account-and-trial.md',
            readTime: '3 min',
          },
          {
            slug: 'quickstart-first-search',
            title: 'Your First Discover Search',
            description: 'Run targeted competitor queries and customize extraction filters.',
            file: 'user-guide/quickstart-first-search.md',
            readTime: '4 min',
          },
          {
            slug: 'quickstart-reading-intelligence',
            title: 'Reading the Intelligence Breakdown',
            description: 'Interpret Hook, Clarity, Retention, and Composite scores.',
            file: 'user-guide/quickstart-reading-intelligence.md',
            readTime: '4 min',
          },
          {
            slug: 'quickstart-remix-studio',
            title: 'Remix in Create Studio',
            description: 'Transform winning competitor patterns into original ad scripts.',
            file: 'user-guide/quickstart-remix-studio.md',
            readTime: '4 min',
          },
          {
            slug: 'quickstart-credits-and-limits',
            title: 'Credit Balances & Daily Limits',
            description: 'Understand credit consumption, daily quotas, and reset schedules.',
            file: 'user-guide/quickstart-credits-and-limits.md',
            readTime: '3 min',
          },
        ],
      },
      {
        groupTitle: 'Core Concepts',
        items: [
          {
            slug: 'concept-how-discover-works',
            title: 'How Discover Works & Real Limits',
            description: 'Ad library indexing, public transparency data, and real-world boundaries.',
            file: 'user-guide/concept-how-discover-works.md',
            readTime: '5 min',
          },
          {
            slug: 'concept-scoring-system',
            title: 'The Creative Scoring System',
            description: 'Exact breakdown of Hook, Clarity, Retention, and Composite algorithms.',
            file: 'user-guide/concept-scoring-system.md',
            readTime: '5 min',
          },
          {
            slug: 'concept-estimated-vs-real-data',
            title: 'Estimated vs. Real Data Standards',
            description: 'Our strict transparency pledge: how data_source and estimates are labeled.',
            file: 'user-guide/concept-estimated-vs-real-data.md',
            readTime: '4 min',
          },
          {
            slug: 'concept-competitor-monitors',
            title: 'Competitor Monitors & Alerts',
            description: 'Setting up automated periodic loops, angle shifts, and email digests.',
            file: 'user-guide/concept-competitor-monitors.md',
            readTime: '4 min',
          },
          {
            slug: 'concept-audience-simulation',
            title: 'Audience Simulation Rehearsal',
            description: 'What synthetic persona rehearsal is and why it is not a statistical predictor.',
            file: 'user-guide/concept-audience-simulation.md',
            readTime: '4 min',
          },
          {
            slug: 'lead-generation',
            title: 'Scout Lead Generation (Scrapling)',
            description: 'Public-web lead generation: ICP brief, seeds, engines, recipes, provenance, and export.',
            file: 'user-guide/lead-generation.md',
            readTime: '7 min',
          },

        ],
      },
      {
        groupTitle: 'Troubleshooting & FAQ',
        items: [
          {
            slug: 'faq',
            title: 'Frequently Asked Questions',
            description: 'Honest answers to common questions, empty searches, and trial expiration.',
            file: 'user-guide/faq.md',
            readTime: '5 min',
          },
        ],
      },
    ],
  },

  // ==========================================
  // SECTION B: API REFERENCE (Technical)
  // ==========================================
  {
    section: 'api-reference',
    sectionLabel: 'API Reference',
    audience: 'Engineers, API key users, and programmatic pipelines',
    groups: [
      {
        groupTitle: 'Getting Started',
        items: [
          {
            slug: 'authentication',
            title: 'Authentication & Headers',
            description: 'Generating secret keys, X-API-Key pattern, and error responses.',
            file: 'api-reference/authentication.md',
            readTime: '4 min',
          },
          {
            slug: 'credit-costs-and-limits',
            title: 'Credit Costs & Rate Limits',
            description: 'Official CREDIT_COSTS table synced with backend billing logic.',
            file: 'api-reference/credit-costs-and-limits.md',
            readTime: '4 min',
          },
        ],
      },
      {
        groupTitle: 'Core Endpoints',
        items: [
          {
            slug: 'endpoint-discover',
            title: 'Discover Endpoints',
            description: 'Trigger asynchronous ad scrapes, poll status, and get scored creatives.',
            file: 'api-reference/endpoint-discover.md',
            readTime: '5 min',
          },
          {
            slug: 'endpoint-creatives',
            title: 'Creatives Endpoints',
            description: 'Query indexed ad catalogs, manage swipe collections, and generate insights.',
            file: 'api-reference/endpoint-creatives.md',
            readTime: '5 min',
          },
          {
            slug: 'endpoint-media-generate',
            title: 'Media Generation Endpoints',
            description: 'Generate AI images and motion videos via Higgsfield pipelines.',
            file: 'api-reference/endpoint-media-generate.md',
            readTime: '4 min',
          },
          {
            slug: 'endpoint-monitors',
            title: 'Monitors Endpoints',
            description: 'Configure automated competitor watches and query detection event feeds.',
            file: 'api-reference/endpoint-monitors.md',
            readTime: '4 min',
          },
        ],
      },
    ],
  },
]

// Flattened list of all documents with full content
export const ALL_DOCS = DOCS_REGISTRY.flatMap((sec) =>
  sec.groups.flatMap((grp) =>
    grp.items.map((item) => ({
      ...item,
      section: sec.section,
      sectionLabel: sec.sectionLabel,
      groupTitle: grp.groupTitle,
      content: getRawContent(item.file),
    }))
  )
)

export function getDoc(section, slug) {
  return ALL_DOCS.find((d) => d.section === section && d.slug === slug)
}

export function getDefaultDocForSection(section) {
  return ALL_DOCS.find((d) => d.section === section)
}

export function getAdjacentDocs(section, slug) {
  const sectionDocs = ALL_DOCS.filter((d) => d.section === section)
  const idx = sectionDocs.findIndex((d) => d.slug === slug)
  if (idx === -1) return { prev: null, next: null }
  return {
    prev: idx > 0 ? sectionDocs[idx - 1] : null,
    next: idx < sectionDocs.length - 1 ? sectionDocs[idx + 1] : null,
  }
}

export function searchDocs(query) {
  if (!query || !query.trim()) return []
  const q = query.toLowerCase().trim()
  return ALL_DOCS.filter((d) => {
    return (
      d.title.toLowerCase().includes(q) ||
      d.description.toLowerCase().includes(q) ||
      d.content.toLowerCase().includes(q) ||
      d.groupTitle.toLowerCase().includes(q)
    )
  }).slice(0, 8)
}
