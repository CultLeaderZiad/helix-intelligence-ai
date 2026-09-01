import { createContext, useContext, useState, useEffect, useCallback } from "react"

const STORAGE_LATEST_KEY = "helix_latest_search"
const STORAGE_HISTORY_KEY = "helix_search_history"
const STORAGE_ACTIVE_CREATIVE_KEY = "helix_active_creative"

const SearchContext = createContext({
  latestSearch: null,
  searchHistory: [],
  activeCreative: null,
  saveCompletedSearch: () => {},
  selectActiveCreative: () => {},
  clearActiveCreative: () => {},
  clearSearchHistory: () => {},
})

export function SearchProvider({ children }) {
  const [latestSearch, setLatestSearch] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_LATEST_KEY)
      if (!raw) return null
      const parsed = JSON.parse(raw)
      if (parsed?.query && /softo?cde/i.test(parsed.query)) {
        localStorage.removeItem(STORAGE_LATEST_KEY)
        return null
      }
      return parsed
    } catch {
      return null
    }
  })

  const [searchHistory, setSearchHistory] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_HISTORY_KEY)
      if (!raw) return []
      const parsed = JSON.parse(raw)
      const cleaned = (Array.isArray(parsed) ? parsed : []).filter(
        (item) => item?.query && !/softo?cde/i.test(item.query)
      )
      return cleaned
    } catch {
      return []
    }
  })

  const [activeCreative, setActiveCreative] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_ACTIVE_CREATIVE_KEY)
      if (!raw) return null
      const parsed = JSON.parse(raw)
      if (parsed?.headline && /softo?cde/i.test(parsed.headline)) {
        localStorage.removeItem(STORAGE_ACTIVE_CREATIVE_KEY)
        return null
      }
      return parsed
    } catch {
      return null
    }
  })

  const saveCompletedSearch = useCallback((searchData) => {
    if (!searchData || !searchData.query) return
    const entry = {
      query: searchData.query,
      jobId: searchData.jobId || searchData.job_id,
      total: searchData.total || searchData.items?.length || 0,
      items: searchData.items || [],
      tookMs: searchData.tookMs || searchData.took_ms || 0,
      timestamp: new Date().toISOString(),
    }
    setLatestSearch(entry)
    try {
      localStorage.setItem(STORAGE_LATEST_KEY, JSON.stringify(entry))
    } catch (e) {
      console.warn("Failed to persist latest search to localStorage", e)
    }

    setSearchHistory((prev) => {
      const filtered = prev.filter((p) => p.query.toLowerCase() !== entry.query.toLowerCase())
      const updated = [entry, ...filtered].slice(0, 15) // Keep last 15 searches
      try {
        localStorage.setItem(STORAGE_HISTORY_KEY, JSON.stringify(updated))
      } catch (e) {
        console.warn("Failed to persist search history", e)
      }
      return updated
    })
  }, [])

  const selectActiveCreative = useCallback((creative) => {
    setActiveCreative(creative)
    try {
      if (creative) {
        localStorage.setItem(STORAGE_ACTIVE_CREATIVE_KEY, JSON.stringify(creative))
      } else {
        localStorage.removeItem(STORAGE_ACTIVE_CREATIVE_KEY)
      }
    } catch (e) {
      console.warn("Failed to update active creative in localStorage", e)
    }
  }, [])

  const selectSearchSession = useCallback((searchEntry) => {
    if (!searchEntry) return
    setLatestSearch(searchEntry)
    try {
      localStorage.setItem(STORAGE_LATEST_KEY, JSON.stringify(searchEntry))
    } catch (e) {
      console.warn("Failed to update latest search session", e)
    }
  }, [])

  const clearSearchHistory = useCallback(() => {
    setSearchHistory([])
    setLatestSearch(null)
    localStorage.removeItem(STORAGE_HISTORY_KEY)
    localStorage.removeItem(STORAGE_LATEST_KEY)
  }, [])

  return (
    <SearchContext.Provider
      value={{
        latestSearch,
        searchHistory,
        activeCreative,
        saveCompletedSearch,
        selectActiveCreative,
        selectSearchSession,
        clearActiveCreative,
        clearSearchHistory,
      }}
    >
      {children}
    </SearchContext.Provider>
  )
}

export function useSearchContext() {
  return useContext(SearchContext)
}
