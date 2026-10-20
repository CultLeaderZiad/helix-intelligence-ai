import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react"
import { useAuth } from "./AuthContext"

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
  saveCompletedSearch: () => {},
  selectActiveCreative: () => {},
  selectSearchSession: () => {},
  clearActiveCreative: () => {},
  clearSearchHistory: () => {},
  saveDraft: () => {},
  deleteDraft: () => {},
})

export function SearchProvider({ children }) {
  const { user } = useAuth()
  const orgId = user?.organization_id || user?.org_id || null
  const userId = user?.id ? (orgId ? `${user.id}:${orgId}` : user.id) : null
  const prevUserIdRef = useRef(userId)

  const [latestSearch, setLatestSearch] = useState(null)
  const [searchHistory, setSearchHistory] = useState([])
  const [activeCreative, setActiveCreative] = useState(null)
  const [drafts, setDrafts] = useState([])

  useEffect(() => {
    const clearPrivateCache = () => {
      purgeUserSearchCache(prevUserIdRef.current)
      prevUserIdRef.current = null
      setLatestSearch(null)
      setSearchHistory([])
      setActiveCreative(null)
      setDrafts([])
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
  }, [userId])

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
      if (userId) {
        try {
          localStorage.setItem(`${STORAGE_HISTORY_KEY}_${userId}`, JSON.stringify(updated))
        } catch (e) {
          console.warn("Failed to persist search history", e)
        }
      }
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

  const saveDraft = useCallback((draft) => {
    if (!draft) return
    const id = draft.id || `draft_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`
    const entry = {
      id,
      title: draft.title || draft.query || "Untitled Draft",
      query: draft.query || "",
      requirements: draft.requirements || draft.notes || "",
      filters: draft.filters || {},
      category_label: draft.category_label || "Research Draft",
      source_id: draft.source_id || null,
      timestamp: new Date().toISOString(),
    }
    setDrafts((prev) => {
      const filtered = prev.filter((d) => d.id !== id)
      const updated = [entry, ...filtered].slice(0, 30) // Keep up to 30 drafts
      if (userId) {
        try {
          localStorage.setItem(`${STORAGE_DRAFTS_KEY}_${userId}`, JSON.stringify(updated))
        } catch (e) {
          console.warn("Failed to persist drafts to localStorage", e)
        }
      }
      return updated
    })
    return entry
  }, [userId])

  const deleteDraft = useCallback((draftId) => {
    setDrafts((prev) => {
      const updated = prev.filter((d) => d.id !== draftId)
      if (userId) {
        try {
          localStorage.setItem(`${STORAGE_DRAFTS_KEY}_${userId}`, JSON.stringify(updated))
        } catch (e) {
          console.warn("Failed to update drafts in localStorage", e)
        }
      }
      return updated
    })
  }, [userId])

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
      }}
    >
      {children}
    </SearchContext.Provider>
  )
}

export function useSearchContext() {
  return useContext(SearchContext)
}
