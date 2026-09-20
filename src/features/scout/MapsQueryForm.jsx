import React from "react"
import { Search, MapPin, Layers, Mail, Share2, ArrowRight, Loader2, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { cn } from "@/lib/utils"

const SUGGESTED_NICHES = ["Dentists", "Specialty Coffee", "Aesthetics Clinic", "Law Firms", "Gyms & Fitness"]
const SUGGESTED_CITIES = ["Riyadh, SA", "Jeddah, SA", "Dubai, UAE", "London, UK", "New York, NY"]

export function MapsQueryForm({
  keyword,
  setKeyword,
  city,
  setCity,
  depth,
  setDepth,
  extractEmails,
  setExtractEmails,
  pullSocials,
  setPullSocials,
  onSubmit,
  isBusy,
}) {
  const isValid = keyword.trim().length >= 2 && city.trim().length >= 2

  // Credit calculation
  const depthNum = Number(depth) || 5
  const estimatedCost = (3.0 + (0.2 * depthNum) + (extractEmails ? 1.0 : 0.0) + (pullSocials ? 1.0 : 0.0)).toFixed(1)

  return (
    <div className="rounded-[4px] border border-border bg-surface p-4 sm:p-5 space-y-4 font-mono text-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/50 pb-3">
        <div className="flex items-center gap-2">
          <span className="text-accent uppercase tracking-wider font-bold text-[11px]">
            MAPS QUERY · GOOGLE MAPS DIRECTORY
          </span>
          <span className="text-text-faint text-[10px]">
            (adapted from gosom/google-maps-scraper)
          </span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-text-muted">
          <span>Est. Credits:</span>
          <span className="text-accent font-bold">{estimatedCost}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
        {/* Keyword input */}
        <div className="md:col-span-6 space-y-1.5">
          <label className="text-[11px] uppercase tracking-wider text-text-muted flex items-center gap-1.5">
            <Search className="h-3 w-3 text-accent" />
            Niche / Business Keyword
          </label>
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            disabled={isBusy}
            placeholder="e.g. Dentists, Specialty Coffee, Orthodontics"
            className="w-full rounded-[4px] border border-border bg-[#09090b] px-3 py-2 text-white placeholder:text-text-faint focus:border-accent focus:outline-none transition-colors"
          />
          {/* Quick suggestions */}
          <div className="flex flex-wrap items-center gap-1 pt-1">
            <span className="text-[9px] text-text-faint">quick:</span>
            {SUGGESTED_NICHES.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setKeyword(n)}
                disabled={isBusy}
                className="text-[10px] px-1.5 py-0.5 rounded bg-[#18181f] text-text-muted hover:text-white hover:bg-[#252530] transition-colors"
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        {/* City input */}
        <div className="md:col-span-4 space-y-1.5">
          <label className="text-[11px] uppercase tracking-wider text-text-muted flex items-center gap-1.5">
            <MapPin className="h-3 w-3 text-accent" />
            City / Region
          </label>
          <input
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            disabled={isBusy}
            placeholder="e.g. Riyadh, SA or Austin, TX"
            className="w-full rounded-[4px] border border-border bg-[#09090b] px-3 py-2 text-white placeholder:text-text-faint focus:border-accent focus:outline-none transition-colors"
          />
          {/* Quick city suggestions */}
          <div className="flex flex-wrap items-center gap-1 pt-1">
            <span className="text-[9px] text-text-faint">city:</span>
            {SUGGESTED_CITIES.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setCity(c)}
                disabled={isBusy}
                className="text-[10px] px-1.5 py-0.5 rounded bg-[#18181f] text-text-muted hover:text-white hover:bg-[#252530] transition-colors"
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {/* Depth input */}
        <div className="md:col-span-2 space-y-1.5">
          <label className="text-[11px] uppercase tracking-wider text-text-muted flex items-center gap-1.5">
            <Layers className="h-3 w-3 text-accent" />
            Depth
          </label>
          <select
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            disabled={isBusy}
            className="w-full rounded-[4px] border border-border bg-[#09090b] px-3 py-2 text-white focus:border-accent focus:outline-none transition-colors cursor-pointer"
          >
            <option value={5}>5 leads</option>
            <option value={10}>10 leads</option>
            <option value={15}>15 leads</option>
            <option value={20}>20 leads</option>
          </select>
        </div>
      </div>

      {/* Toggles & Submit button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-border/50">
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer select-none text-text-muted hover:text-white transition-colors">
            <input
              type="checkbox"
              checked={extractEmails}
              onChange={(e) => setExtractEmails(e.target.checked)}
              disabled={isBusy}
              className="rounded-[2px] border-border text-accent focus:ring-0 focus:ring-offset-0 bg-[#09090b] h-3.5 w-3.5"
            />
            <span className="flex items-center gap-1 text-[11px]">
              <Mail className="h-3 w-3 text-accent" />
              Extract emails from websites
            </span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer select-none text-text-muted hover:text-white transition-colors">
            <input
              type="checkbox"
              checked={pullSocials}
              onChange={(e) => setPullSocials(e.target.checked)}
              disabled={isBusy}
              className="rounded-[2px] border-border text-accent focus:ring-0 focus:ring-offset-0 bg-[#09090b] h-3.5 w-3.5"
            />
            <span className="flex items-center gap-1 text-[11px]">
              <Share2 className="h-3 w-3 text-accent" />
              Pull social profiles (IG / FB / LI / X)
            </span>
          </label>
        </div>

        <Button
          type="button"
          variant="primary"
          size="sm"
          disabled={!isValid || isBusy}
          onClick={onSubmit}
          className={cn(
            "font-mono text-xs font-bold uppercase tracking-wider text-black transition-all",
            !isValid || isBusy ? "opacity-40 cursor-not-allowed" : "hover:bg-[#e4ff75] shadow-sm shadow-accent/20"
          )}
        >
          {isBusy ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
              SCRAPING MAPS...
            </>
          ) : (
            <>
              RUN MAPS SCOUT
              <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

export default MapsQueryForm
