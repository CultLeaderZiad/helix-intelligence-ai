import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { ExternalLink } from "lucide-react"
import { Folder } from "@/components/ui/Folder"
import { useSearchContext } from "@/context/SearchContext"
import { useLanguage } from "@/context/LanguageContext"
import { creativeService } from "@/services"

export const FOLDER_COPY = {
  en: {
    open: "Drafts and links",
    drafts: "Drafts",
    links: "Links",
    noDrafts: "No saved drafts yet.",
    noLinks: "No saved links yet.",
    all: "Open Swipe Files",
    openDrafts: "Open Discover",
  },
  ar: {
    open: "المسودات والروابط",
    drafts: "المسودات",
    links: "الروابط",
    noDrafts: "لا توجد مسودات محفوظة بعد.",
    noLinks: "لا توجد روابط محفوظة بعد.",
    all: "افتح ملفات الإلهام",
    openDrafts: "افتح Discover",
  },
}

const MAX_SHOWN = 8

/** A saved reference link: the ad's own page when it has one, else the site a manual reference points to. */
export function linkFor(item) {
  const raw = String(item?.permalink || (item?.data_source === "manual_upload" ? item?.landing_domain : "") || "").trim()
  if (!raw) return null
  const url = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`
  try {
    return new URL(url).href
  } catch {
    return null
  }
}

export function pickLinks(items) {
  return (items || []).map((item) => ({ id: item.id, label: item.headline || item.brand_name || "—", href: linkFor(item) })).filter((x) => x.href)
}

/** Bottom-corner folder: click it to see the titles of your saved drafts and reference links. */
export function DraftsFolder() {
  const { lang } = useLanguage()
  const c = lang === "ar" ? FOLDER_COPY.ar : FOLDER_COPY.en
  const { drafts } = useSearchContext()
  const [links, setLinks] = useState([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let live = true
    creativeService.getSavedCreatives({ page: 1, page_size: 50 })
      .then((res) => { if (live) setLinks(pickLinks(res?.items)) })
      .catch(() => { if (live) setLinks([]) })  // no swipe-files access: the folder just shows drafts
    return () => { live = false }
  }, [])

  const shownDrafts = (drafts || []).slice(0, MAX_SHOWN)
  const shownLinks = links.slice(0, MAX_SHOWN)

  return (
    <div className="fixed bottom-3 end-3 z-30 flex flex-col items-end gap-2">
      {open ? (
        <div role="dialog" aria-label={c.open} className="max-h-[60dvh] w-72 max-w-[calc(100vw-1.5rem)] overflow-y-auto rounded-2xl border border-white/10 bg-[#1c1c1c] p-3 text-sm shadow-[0_12px_40px_-12px_rgba(0,0,0,0.7)]">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-white/50">{c.drafts}</h2>
          {shownDrafts.length === 0 ? <p className="mt-1 text-xs text-white/50">{c.noDrafts}</p> : (
            <ul className="mt-1 flex flex-col">
              {shownDrafts.map((d) => (
                <li key={d.id}><Link to="/discover" dir="auto" className="block truncate rounded px-2 py-1.5 text-white/85 hover:bg-white/[0.07]">{d.title || d.query}</Link></li>
              ))}
            </ul>
          )}
          <h2 className="mt-3 text-xs font-semibold uppercase tracking-wide text-white/50">{c.links}</h2>
          {shownLinks.length === 0 ? <p className="mt-1 text-xs text-white/50">{c.noLinks}</p> : (
            <ul className="mt-1 flex flex-col">
              {shownLinks.map((l) => (
                <li key={l.id}>
                  <a href={l.href} target="_blank" rel="noopener noreferrer" dir="auto" className="flex items-center justify-between gap-2 rounded px-2 py-1.5 text-white/85 hover:bg-white/[0.07]">
                    <span className="truncate">{l.label}</span><ExternalLink className="h-3.5 w-3.5 shrink-0 text-white/40" aria-hidden="true" />
                  </a>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-3 flex gap-3 border-t border-white/10 pt-2 text-xs">
            <Link to="/discover" className="text-white/70 underline">{c.openDrafts}</Link>
            <Link to="/swipe-files" className="text-white/70 underline">{c.all}</Link>
          </div>
        </div>
      ) : null}
      <button type="button" aria-label={c.open} aria-expanded={open} onClick={() => setOpen((v) => !v)} className="h-[110px] w-[120px] rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-white/30">
        <Folder size="xs" />
      </button>
    </div>
  )
}

export default DraftsFolder
