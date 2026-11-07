import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react"
import { useAuth } from "./AuthContext"
import { discoverService } from "@/services"

const STORAGE_LATEST_KEY = "helix_latest_search"
const STORAGE_HISTORY_KEY = "helix_search_history"
const STORAGE_ACTIVE_CREATIVE_KEY = "helix_active_creative"
const STORAGE_DRAFTS_KEY = "helix_saved_drafts"
const STORAGE_KEYS = [
  STORAGE_LATEST_KEY,
  STORAGE_HISTORY_KEY,
  STORAGE_ACTIVE_CREATIVE_KEY,
  STORAGE_DRAFTS_KEY,
]

function purgeUserSearchCache(userId) {
  if (!userId || typeof window === "undefined") return
  try {
    for (const key of STORAGE_KEYS) {
      window.localStorage.removeItem(`${key}_${userId}`)
    }
  } catch {
    // Storage can be unavailable in restricted browser contexts.
  }
}

const SearchContext = createContext({
  latestSearch: null,
  searchHistory: [],
  activeCreative: null,
  drafts: [],
  saveCompletedSearch: (_search) => {},
  selectActiveCreative: (_creative) => {},
  selectSearchSession: (_search) => {},
  clearActiveCreative: () => {},
  clearSearchHistory: () => {},
  saveDraft: async (_draft) => null,
  deleteDraft: async (_draftId) => {},
  refreshFromServer: async () => {},
  openSearchSession: async (_search) => false,
  serverSynced: false,
})

/** Map a server draft row onto the shape the drafts modal renders. */
function fromServerDraft(row) {
  return {
    id: row.id,
    title: row.title || row.query,
    query: row.query,
    requirements: row.notes || "",
    filters: row.filters || {},
    timestamp: row.created_at || new Date().toISOString(),
    server: true,
  }
}

/** Map a server job row onto a history entry (results are fetched on demand). */
function fromServerJob(job) {
  return {
    query: job.query,
    jobId: job.job_id,
    job_id: job.job_id,
    status: job.status,
    total: job.records_found || 0,
    items: [],
    timestamp: job.created_at || null,
    category_label: job.entity_profile?.category_label || null,
    server: true,
  }
}

/**
 * Server history is the source of truth; a local entry for the same query
 * wins only when it still holds results in memory. Newest first, 15 max.
 */
function mergeHistory(local, server) {
  const byQuery = new Map()
  for (const entry of [...server, ...local]) {
    if (!entry?.query) continue
    const key = entry.query.toLowerCase()
    const existing = byQuery.get(key)
    if (!existing) {
      byQuery.set(key, entry)
      continue
    }
    const newer = new Date(entry.timestamp || 0) > new Date(existing.timestamp || 0) ? entry : existing
    const withItems = entry.items?.length ? entry : existing.items?.length ? existing : null
    byQuery.set(key, withItems && withItems !== newer ? { ...newer, items: withItems.items, total: withItems.total } : newer)
  }
  return [...byQuery.values()]
    .sort((a, b) => new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime())
    .slice(0, 15)
}

export function SearchProvider({ children }) {
  const { user } = useAuth()
  const orgId = user?.organization_id || user?.org_id || null
  const userId = user?.id ? (orgId ? `${user.id}:${orgId}` : user.id) : null
  const prevUserIdRef = useRef(userId)

  const [latestSearch, setLatestSearch] = useState(null)
  const [searchHistory, setSearchHistory] = useState([])
  const [activeCreative, setActiveCreative] = useState(null)
  const [drafts, setDrafts] = useState([])
  const [cacheScope, setCacheScope] = useState(null)
  const [serverSynced, setServerSynced] = useState(false)
  // Drafts and history are stored on the server only for workspaces granted
  // Discover (the API is behind that flag); otherwise they stay local.
  const canUseServer = user?.feature_flags?.discover === true

  useEffect(() => {
    const clearPrivateCache = () => {
      setCacheScope(null)
      purgeUserSearchCache(prevUserIdRef.current)
      prevUserIdRef.current = null
      setLatestSearch(null)
      setSearchHistory([])
      setActiveCreative(null)
      setDrafts([])
      setServerSynced(false)
    }
    window.addEventListener("helix:session-clearing", clearPrivateCache)
    return () => window.removeEventListener("helix:session-clearing", clearPrivateCache)
  }, [])

  // Synchronize state with current user session (F12, F43)
  useEffect(() => {
    // Purge any legacy un-namespaced test fixtures
    try {
      localStorage.removeItem(STORAGE_LATEST_KEY)
      localStorage.removeItem(STORAGE_HISTORY_KEY)
      localStorage.removeItem(STORAGE_ACTIVE_CREATIVE_KEY)
      localStorage.removeItem(STORAGE_DRAFTS_KEY)
    } catch {
      // ignore
    }

    if (!userId) {
      const previous = prevUserIdRef.current
      if (previous) {
        purgeUserSearchCache(previous)
      }
      setLatestSearch(null)
      setSearchHistory([])
      setActiveCreative(null)
      setDrafts([])
      prevUserIdRef.current = null
      setCacheScope(null)
      return
    }

    // User signed in or switched account: load user-isolated history
    try {
      const rawLatest = localStorage.getItem(`${STORAGE_LATEST_KEY}_${userId}`)
      setLatestSearch(rawLatest ? JSON.parse(rawLatest) : null)
    } catch {
      setLatestSearch(null)
    }

    try {
      const rawHistory = localStorage.getItem(`${STORAGE_HISTORY_KEY}_${userId}`)
      const parsedHistory = rawHistory ? JSON.parse(rawHistory) : []
      setSearchHistory(Array.isArray(parsedHistory) ? parsedHistory : [])
    } catch {
      setSearchHistory([])
    }

    try {
      const rawCreative = localStorage.getItem(`${STORAGE_ACTIVE_CREATIVE_KEY}_${userId}`)
      setActiveCreative(rawCreative ? JSON.parse(rawCreative) : null)
    } catch {
      setActiveCreative(null)
    }

    try {
      const rawDrafts = localStorage.getItem(`${STORAGE_DRAFTS_KEY}_${userId}`)
      const parsedDrafts = rawDrafts ? JSON.parse(rawDrafts) : []
      setDrafts(Array.isArray(parsedDrafts) ? parsedDrafts : [])
    } catch {
      setDrafts([])
    }

    prevUserIdRef.current = userId
    setCacheScope(userId)
  }, [userId])

  // Drafts deleted in this session; a refresh that started before the delete
  // finished must not bring them back.
  const deletedDraftIds = useRef(new Set())

  const refreshFromServer = useCallback(async () => {
    if (!userId || !canUseServer) return
    const scope = userId
    const [draftsResult, jobsResult] = await Promise.allSettled([
      discoverService.listDrafts(),
      discoverService.listRecentJobs({ page_size: 15 }),
    ])
    if (prevUserIdRef.current !== scope) return
    if (draftsResult.status === "fulfilled") {
      const rows = Array.isArray(draftsResult.value?.items) ? draftsResult.value.items : []
      // Keep drafts saved while offline (local ids) until they are re-saved.
      const live = rows.filter((row) => !deletedDraftIds.current.has(row.id)).map(fromServerDraft)
      setDrafts((prev) => [...live, ...prev.filter((d) => !d.server && String(d.id).startsWith("draft_"))])
    }
    if (jobsResult.status === "fulfilled") {
      const rows = Array.isArray(jobsResult.value?.items) ? jobsResult.value.items : []
      setSearchHistory((prev) => mergeHistory(prev, rows.filter((j) => j?.query).map(fromServerJob)))
    }
    setServerSynced(draftsResult.status === "fulfilled" || jobsResult.status === "fulfilled")
  }, [userId, canUseServer])

  useEffect(() => {
    if (!userId || cacheScope !== userId) return
    setServerSynced(false)
    void refreshFromServer()
  }, [userId, cacheScope, refreshFromServer])

  useEffect(() => {
    if (!userId || cacheScope !== userId) return
    try {
      localStorage.setItem(`${STORAGE_HISTORY_KEY}_${userId}`, JSON.stringify(searchHistory))
      localStorage.setItem(`${STORAGE_DRAFTS_KEY}_${userId}`, JSON.stringify(drafts))
    } catch {
      // Storage may be unavailable; committed in-memory state remains usable.
    }
  }, [userId, cacheScope, searchHistory, drafts])

  const saveCompletedSearch = useCallback((searchData) => {
    if (!searchData || !searchData.query) return
    const entry = {
      query: searchData.query,
      jobId: searchData.jobId || searchData.job_id || null,
      job_id: searchData.job_id || searchData.jobId || null,
      total: searchData.total || searchData.items?.length || 0,
      items: searchData.items || [],
      tookMs: searchData.tookMs || searchData.took_ms || 0,
      entity_profile: searchData.entity_profile || searchData.entityProfile || null,
      category_label: searchData.category_label || searchData.entity_profile?.category_label || "Ad Intelligence",
      timestamp: new Date().toISOString(),
    }
    setLatestSearch(entry)
    if (userId) {
      try {
        localStorage.setItem(`${STORAGE_LATEST_KEY}_${userId}`, JSON.stringify(entry))
      } catch (e) {
        console.warn("Failed to persist latest search to localStorage", e)
      }
    }

    setSearchHistory((prev) => {
      const filtered = prev.filter((p) => p.query.toLowerCase() !== entry.query.toLowerCase())
      const updated = [entry, ...filtered].slice(0, 15) // Keep last 15 searches
      return updated
    })
  }, [userId])

  const selectActiveCreative = useCallback((creative) => {
    setActiveCreative(creative)
    if (userId) {
      try {
        if (creative) {
          localStorage.setItem(`${STORAGE_ACTIVE_CREATIVE_KEY}_${userId}`, JSON.stringify(creative))
        } else {
          localStorage.removeItem(`${STORAGE_ACTIVE_CREATIVE_KEY}_${userId}`)
        }
      } catch (e) {
        console.warn("Failed to update active creative in localStorage", e)
      }
    }
  }, [userId])

  const clearActiveCreative = useCallback(() => {
    setActiveCreative(null)
    if (userId) {
      try {
        localStorage.removeItem(`${STORAGE_ACTIVE_CREATIVE_KEY}_${userId}`)
      } catch (e) {
        console.warn("Failed to clear active creative in localStorage", e)
      }
    }
  }, [userId])

  const selectSearchSession = useCallback((searchEntry) => {
    if (!searchEntry) return
    setLatestSearch(searchEntry)
    if (userId) {
      try {
        localStorage.setItem(`${STORAGE_LATEST_KEY}_${userId}`, JSON.stringify(searchEntry))
      } catch (e) {
        console.warn("Failed to update latest search session", e)
      }
    }
  }, [userId])

  const saveDraft = useCallback(async (draft) => {
    if (!draft) return null
    const query = (draft.query || draft.title || "").trim()
    if (!query) return null
    const title = (draft.title || query).trim()
    const notes = (draft.requirements || draft.notes || "").trim()
    const filters = draft.filters || {}
    if (canUseServer) {
      // Throws on failure so the caller can tell the user it was not saved.
      const saved = fromServerDraft(await discoverService.saveDraft({ title, query, notes, filters }))
      setDrafts((prev) => [saved, ...prev.filter((d) => d.id !== saved.id)])
      return saved
    }
    const entry = {
      id: draft.id || `draft_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      title,
      query,
      requirements: notes,
      filters,
      timestamp: new Date().toISOString(),
    }
    setDrafts((prev) => [entry, ...prev.filter((d) => d.id !== entry.id)].slice(0, 30))
    return entry
  }, [canUseServer])

  /**
   * Re-open a past search. Uses results already in memory, else reads the
   * stored results of that job from the server. Returns false when there is
   * nothing stored to show (a failed or empty search), so the caller can run
   * the search again instead.
   */
  const openSearchSession = useCallback(async (item) => {
    if (!item?.query) return false
    if (item.items?.length) {
      selectSearchSession(item)
      return true
    }
    const jobId = item.job_id || item.jobId
    if (!jobId || item.status === "failed") return false
    const res = await discoverService.getJobResults(jobId, { page: 1, page_size: 20 })
    const items = Array.isArray(res?.items) ? res.items : []
    if (!items.length) return false
    const entry = { ...item, items, total: res.total ?? items.length, tookMs: res.took_ms || 0 }
    selectSearchSession(entry)
    setSearchHistory((prev) => prev.map((h) => ((h.job_id || h.jobId) === jobId ? entry : h)))
    return true
  }, [selectSearchSession])

  const draftsRef = useRef(drafts)
  draftsRef.current = drafts

  const deleteDraft = useCallback(async (draftId) => {
    const removed = draftsRef.current.find((d) => d.id === draftId) || null
    setDrafts((prev) => prev.filter((d) => d.id !== draftId))
    if (!removed?.server) return
    deletedDraftIds.current.add(draftId)
    try {
      await discoverService.deleteDraft(draftId)
    } catch (error) {
      // Put it back: the server still has it.
      deletedDraftIds.current.delete(draftId)
      setDrafts((prev) => (prev.some((d) => d.id === draftId) ? prev : [removed, ...prev]))
      throw error
    }
  }, [])

  const clearSearchHistory = useCallback(() => {
    setSearchHistory([])
    setLatestSearch(null)
    if (userId) {
      try {
        localStorage.removeItem(`${STORAGE_HISTORY_KEY}_${userId}`)
        localStorage.removeItem(`${STORAGE_LATEST_KEY}_${userId}`)
      } catch {
        // storage can be blocked
      }
    }
  }, [userId])

  return (
    <SearchContext.Provider
      value={{
        latestSearch,
        searchHistory,
        activeCreative,
        drafts,
        saveCompletedSearch,
        selectActiveCreative,
        selectSearchSession,
        clearActiveCreative,
        clearSearchHistory,
        saveDraft,
        deleteDraft,
        refreshFromServer,
        openSearchSession,
        serverSynced,
      }}
    >
      {children}
    </SearchContext.Provider>
  )
}

export function useSearchContext() {
  return useContext(SearchContext)
}
