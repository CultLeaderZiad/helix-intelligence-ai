import React from "react"
import { Link2, Network, ShoppingBag, FileSpreadsheet } from "lucide-react"

/**
 * SeedInput — stage 4.2 inputs. URLs / sitemap / Shopify / domain CSV.
 * Server rejects localhost, RFC1918, non-http(s) schemes with clear errors.
 */
export function SeedInput({ value, onChange, disabled }) {
  const set = (patch) => onChange({ ...value, ...patch })
  const field =
    "w-full rounded border border-border bg-[#09090b] px-2.5 py-1.5 font-mono text-xs text-white placeholder:text-text-faint focus:border-accent/60 focus:outline-none"
  const label = "flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-text-faint font-semibold"

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <span className={label}><Link2 className="h-3.5 w-3.5" /> seed urls (one per line)</span>
        <textarea
          rows={3}
          disabled={disabled}
          value={(value.urls || []).join("\n")}
          onChange={(e) => set({ urls: e.target.value.split("\n").map((s) => s.trim()).filter(Boolean) })}
          placeholder={"https://example-contractor.sa\nhttps://another-brand.ae"}
          className={field}
        />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        <div className="space-y-1.5">
          <span className={label}><Network className="h-3.5 w-3.5" /> sitemap url</span>
          <input
            disabled={disabled}
            value={value.sitemap_url || ""}
            onChange={(e) => set({ sitemap_url: e.target.value.trim() || null })}
            placeholder="https://example.com/sitemap.xml"
            className={field}
          />
        </div>
        <div className="space-y-1.5">
          <span className={label}><ShoppingBag className="h-3.5 w-3.5" /> shopify store</span>
          <input
            disabled={disabled}
            value={value.shopify_url || ""}
            onChange={(e) => set({ shopify_url: e.target.value.trim() || null })}
            placeholder="https://brand.myshopify.com"
            className={field}
          />
        </div>
        <div className="space-y-1.5">
          <span className={label}><FileSpreadsheet className="h-3.5 w-3.5" /> domain list (CSV/JSONL)</span>
          <textarea
            rows={2}
            disabled={disabled}
            value={value.domains_csv || ""}
            onChange={(e) => set({ domains_csv: e.target.value || null })}
            placeholder={"example.com\nother.sa"}
            className={field}
          />
        </div>
      </div>
    </div>
  )
}

export default SeedInput
