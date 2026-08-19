import { useEffect, useState } from "react"

/**
 * Responsive decisions that change *behaviour* (not just layout) must be
 * driven by state, not CSS — e.g. the sidebar becomes an overlay drawer
 * rather than a rail, and the results table collapses to cards.
 */
export function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => {
    if (typeof window === "undefined") return false
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    const mql = window.matchMedia(query)
    const onChange = (e) => setMatches(e.matches)
    setMatches(mql.matches)
    mql.addEventListener("change", onChange)
    return () => mql.removeEventListener("change", onChange)
  }, [query])

  return matches
}

/** Tailwind-aligned breakpoints. */
export const useIsMobile = () => useMediaQuery("(max-width: 767px)")
export const useIsBelowLg = () => useMediaQuery("(max-width: 1023px)")
export const useIsBelowXl = () => useMediaQuery("(max-width: 1279px)")
