/**
 * W9-2 (D3): filters over Discover results that are already loaded in the
 * browser. Pure functions: nothing here calls the API, so they can never
 * start a Metapi query or spend records.
 *
 * Status: an ad with a stop date (`last_seen`, Meta's delivery stop time) is
 * "stopped"; one without is "active". Run length uses `days_active`; unknown
 * run lengths are hidden once a minimum is set.
 */

/** @typedef {{format: string, status: string, cta: string, domain: string, minDays: number}} LoadedFilters */

/** @type {Readonly<LoadedFilters>} */
export const EMPTY_LOADED_FILTERS = Object.freeze({
  format: "",
  status: "",
  cta: "",
  domain: "",
  minDays: 0,
})

export function adStatus(item) {
  return item?.last_seen ? "stopped" : "active"
}

function uniqueSorted(values) {
  return [...new Set(values.filter((v) => typeof v === "string" && v.trim()))].sort((a, b) => a.localeCompare(b))
}

/** The options each control offers, taken from the loaded items only. */
export function loadedFilterOptions(items = []) {
  const days = items.map((i) => i?.days_active).filter((d) => Number.isFinite(d))
  return {
    formats: uniqueSorted(items.map((i) => i?.format)),
    ctas: uniqueSorted(items.map((i) => i?.cta)),
    domains: uniqueSorted(items.map((i) => i?.landing_domain)),
    statuses: uniqueSorted(items.map(adStatus)),
    maxDays: days.length ? Math.max(...days) : 0,
  }
}

export function countLoadedFilters(f = EMPTY_LOADED_FILTERS) {
  return ["format", "status", "cta", "domain"].filter((k) => f[k]).length + (f.minDays > 0 ? 1 : 0)
}

export function applyLoadedFilters(items = [], f = EMPTY_LOADED_FILTERS) {
  if (!countLoadedFilters(f)) return items
  return items.filter((item) => {
    if (f.format && item?.format !== f.format) return false
    if (f.status && adStatus(item) !== f.status) return false
    if (f.cta && item?.cta !== f.cta) return false
    if (f.domain && item?.landing_domain !== f.domain) return false
    if (f.minDays > 0 && !(Number.isFinite(item?.days_active) && item.days_active >= f.minDays)) return false
    return true
  })
}
