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

const DEFAULT_SEARCH_HISTORY = [
  {
    query: "Sneako",
    total: 0,
    items: [],
    category_label: "Content Creator & Streamer",
    timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
    entity_profile: {
      entity_name: "Sneako (Nicolas Kenn De Balinthazy)",
      entity_type: "creator_streamer",
      category_label: "Content Creator & Streamer",
      primary_platforms: ["Kick", "Rumble", "YouTube", "X (Twitter)"],
      summary: "High-profile online creator, livestreamer, and commentator known for IRL streams, commentary, ideological debates, and multi-platform broadcasting.",
      marketing_archetype: "Controversy-Driven Organic Clipping & Multi-Platform Streaming"
    }
  },
  {
    query: "Naturia",
    total: 12,
    items: [
      {
        id: "naturia-1",
        headline: "Naturia-Formula desparasitaria para la salud perruna",
        body: "EL MASTICABLE PARA LA ALERGIA NO ES EL PROBLEMA Tu perro no tiene alergias Tu perro tiene parásitos multiplicándose detrás de un escudo de biofilm en su intestino...",
        cta: "Comprar Naturia Gotas Limpiadoras",
        platform: "meta",
        format: "image",
        days_active: 28,
        scores: { hook: 88, clarity: 92, retention: 84, composite: 88 }
      }
    ],
    category_label: "Holistic Pet Health & DTC",
    timestamp: new Date(Date.now() - 25 * 60000).toISOString()
  },
  {
    query: "Real Madrid",
    total: 18,
    items: [
      {
        id: "rm-1",
        headline: "¿Aún no tienes la App Oficial del Real Madrid? 📱🤍",
        body: "Vive los partidos estés donde estés. 📻 Radio en directo, resúmenes, calendario y ventajas exclusivas en la tienda. ¡No te pierdas nada y descárgala gratis ya! 👇",
        cta: "Установити зараз",
        platform: "meta",
        format: "video",
        days_active: 28,
        scores: { hook: 94, clarity: 96, retention: 91, composite: 94 }
      }
    ],
    category_label: "Sports Club & Mobile Entertainment",
    timestamp: new Date(Date.now() - 45 * 60000).toISOString()
  },
  {
    query: "Gymshark",
    total: 24,
    items: [],
    category_label: "Fitness DTC & Athletic Wear",
    timestamp: new Date(Date.now() - 90 * 60000).toISOString()
  },
  {
    query: "Nike",
    total: 35,
    items: [],
    category_label: "Global Athletic Footwear & Apparel",
    timestamp: new Date(Date.now() - 150 * 60000).toISOString()
  }
]

export function SearchProvider({ children }) {
  const [latestSearch, setLatestSearch] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_LATEST_KEY)
      if (!raw) return DEFAULT_SEARCH_HISTORY[0]
      const parsed = JSON.parse(raw)
      if (parsed?.query && /softo?cde/i.test(parsed.query)) {
        localStorage.removeItem(STORAGE_LATEST_KEY)
        return DEFAULT_SEARCH_HISTORY[0]
      }
      return parsed
    } catch {
      return DEFAULT_SEARCH_HISTORY[0]
    }
  })

  const [searchHistory, setSearchHistory] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_HISTORY_KEY)
      if (!raw) return DEFAULT_SEARCH_HISTORY
      const parsed = JSON.parse(raw)
      const cleaned = (Array.isArray(parsed) ? parsed : []).filter(
        (item) => item?.query && !/softo?cde/i.test(item.query)
      )
      if (cleaned.length === 0) return DEFAULT_SEARCH_HISTORY
      return cleaned
    } catch {
      return DEFAULT_SEARCH_HISTORY
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
      entity_profile: searchData.entity_profile || searchData.entityProfile || null,
      category_label: searchData.category_label || searchData.entity_profile?.category_label || "Ad Intelligence",
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

  const clearActiveCreative = useCallback(() => {
    setActiveCreative(null)
    try {
      localStorage.removeItem(STORAGE_ACTIVE_CREATIVE_KEY)
    } catch (e) {
      console.warn("Failed to clear active creative in localStorage", e)
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
