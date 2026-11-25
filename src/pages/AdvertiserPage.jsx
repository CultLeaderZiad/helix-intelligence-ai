import { useState } from "react"
import { useParams } from "react-router-dom"
import { ExternalLink } from "lucide-react"
import advertiserService from "@/services/api/advertiserService.api"
import { useAsync } from "@/hooks/useAsync"
import { useLanguage } from "@/context/LanguageContext"

export const ADVERTISER_COPY = {
  en: {
    title: "Advertiser",
    loading: "Loading…",
    failed: "This advertiser has no ads in your workspace yet, or it could not be loaded.",
    adsFound: "Ads found",
    longest: "Longest running",
    activeNow: "Active now (monitors)",
    launches30: "Launches, last 30 days (monitors)",
    unknown: "Unknown",
    days: (n) => `${n} days`,
    weekly: "Weekly launches and active ads (from your monitors)",
    noMonitor: "Monitor this advertiser to see launches and active ads over time.",
    winners: "Longest-running ads",
    order: "Ordered by days active (unknown last), then variants, then landing-page reuse. These are signals, not a score.",
    variants: "Variants",
    reuse: "Ads on this landing page",
    daysActive: "Days active",
    more: "Load more",
    week: "Week",
    launchesCol: "Launches",
    activeCol: "Active",
    adLibrary: "Open this advertiser in Meta Ad Library",
    adLibraryNote: "Opens Meta's own public page in a new tab. Nothing is fetched or stored by Helix.",
  },
  ar: {
    title: "المعلِن",
    loading: "جارٍ التحميل…",
    failed: "لا توجد إعلانات لهذا المعلِن في مساحة عملك بعد، أو تعذّر تحميلها.",
    adsFound: "الإعلانات المعثور عليها",
    longest: "الأطول تشغيلاً",
    activeNow: "نشط الآن (المراقبة)",
    launches30: "إعلانات جديدة آخر 30 يوماً (المراقبة)",
    unknown: "غير معروف",
    days: (n) => `${n} يوم`,
    weekly: "الإعلانات الجديدة والنشطة أسبوعياً (من المراقبة)",
    noMonitor: "راقب هذا المعلِن لترى الإعلانات الجديدة والنشطة عبر الوقت.",
    winners: "الإعلانات الأطول تشغيلاً",
    order: "مرتبة حسب أيام التشغيل (غير المعروف في الآخر)، ثم عدد النسخ، ثم إعادة استخدام صفحة الهبوط. هذه مؤشرات وليست درجة.",
    variants: "النسخ",
    reuse: "إعلانات على نفس صفحة الهبوط",
    daysActive: "أيام التشغيل",
    more: "تحميل المزيد",
    week: "الأسبوع",
    launchesCol: "جديد",
    activeCol: "نشط",
    adLibrary: "افتح هذا المعلِن في مكتبة إعلانات ميتا",
    adLibraryNote: "يفتح صفحة ميتا العامة في تبويب جديد. لا يجلب Helix أو يخزّن شيئاً.",
  },
}

/** Meta's public Ad Library search for an advertiser name. A plain link: no API, no data fetched. */
export function adLibraryUrl(name) {
  const q = String(name || "").trim()
  if (!q) return null
  return `https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&search_type=keyword_unordered&q=${encodeURIComponent(q)}`
}

function Stat({ label, value }) {
  return (
    <div className="rounded-lg border border-border bg-surface-2 p-3">
      <p className="text-xs text-text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-text">{value}</p>
    </div>
  )
}

export function AdvertiserPage() {
  const { brandId = "" } = useParams()
  const { lang } = useLanguage()
  const c = lang === "ar" ? ADVERTISER_COPY.ar : ADVERTISER_COPY.en
  const summary = useAsync(() => advertiserService.getSummary(brandId), [brandId])
  const first = useAsync(() => advertiserService.getAds(brandId, 1), [brandId])
  const [extra, setExtra] = useState([])
  const [page, setPage] = useState(1)
  const [moreError, setMoreError] = useState(false)
  const [nextHasMore, setNextHasMore] = useState(null)

  if (summary.loading) return <p className="p-6 text-sm text-text-muted">{c.loading}</p>
  if (summary.error || !summary.data) return <p role="alert" className="p-6 text-sm text-text-muted">{c.failed}</p>

  const s = summary.data
  const ads = [...(first.data?.items || []), ...extra]
  const hasMore = nextHasMore ?? first.data?.has_more
  const days = (n) => (n == null ? c.unknown : c.days(n))

  async function loadMore() {
    try {
      const next = await advertiserService.getAds(brandId, page + 1)
      setExtra([...extra, ...next.items])
      setNextHasMore(Boolean(next.has_more))
      setPage(page + 1)
      setMoreError(false)
    } catch {
      setMoreError(true)
    }
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-4 sm:p-6">
      <header>
        <p className="label-mono text-text-muted">{c.title}</p>
        <h1 className="text-2xl font-semibold text-text" dir="auto">{s.brand_name || brandId}</h1>
        {adLibraryUrl(s.brand_name) ? (
          <p className="mt-2 text-sm">
            <a href={adLibraryUrl(s.brand_name)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-text underline">
              {c.adLibrary} <ExternalLink className="h-4 w-4" aria-hidden="true" />
            </a>
            <span className="ms-2 text-xs text-text-muted">{c.adLibraryNote}</span>
          </p>
        ) : null}
      </header>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label={c.adsFound} value={s.ads_found} />
        <Stat label={c.longest} value={days(s.longest_running_days)} />
        <Stat label={c.activeNow} value={s.active_now ?? c.unknown} />
        <Stat label={c.launches30} value={s.launches_last_30d ?? c.unknown} />
      </div>

      <section>
        <h2 className="text-sm font-semibold text-text">{c.weekly}</h2>
        {s.weekly.length === 0 ? (
          <p className="mt-2 text-sm text-text-muted">{c.noMonitor}</p>
        ) : (
          <table className="mt-2 w-full text-xs">
            <thead><tr className="text-text-muted"><th className="text-start">{c.week}</th><th>{c.launchesCol}</th><th>{c.activeCol}</th></tr></thead>
            <tbody>
              {s.weekly.map((w) => (
                <tr key={w.week_start} className="border-t border-border">
                  <td dir="ltr" className="py-1">{w.week_start}</td>
                  <td className="text-center">{w.launches}</td>
                  <td className="text-center">{w.active}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2 className="text-sm font-semibold text-text">{c.winners}</h2>
        <p className="mt-1 text-xs text-text-muted">{c.order}</p>
        <ul className="mt-3 flex flex-col gap-2">
          {ads.map((ad) => (
            <li key={ad.id} className="rounded-lg border border-border p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-text" dir="auto">{ad.headline || ad.body || "—"}</p>
                  {ad.headline && ad.body ? <p className="mt-1 line-clamp-2 text-xs text-text-muted" dir="auto">{ad.body}</p> : null}
                </div>
                {ad.permalink ? (
                  <a href={ad.permalink} target="_blank" rel="noreferrer" className="shrink-0 text-text-muted hover:text-text" aria-label="Meta Ad Library">
                    <ExternalLink className="h-4 w-4" aria-hidden="true" />
                  </a>
                ) : null}
              </div>
              <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
                <div><dt className="inline">{c.daysActive}: </dt><dd className="inline text-text">{days(ad.signals.days_active)}</dd></div>
                <div><dt className="inline">{c.variants}: </dt><dd className="inline text-text">{ad.signals.variants}</dd></div>
                <div><dt className="inline">{c.reuse}: </dt><dd className="inline text-text">{ad.signals.landing_page_reuse ?? c.unknown}</dd></div>
              </dl>
            </li>
          ))}
        </ul>
        {moreError ? <p role="alert" className="mt-2 text-xs text-rose-300">{c.failed}</p> : null}
        {hasMore ? (
          <button type="button" onClick={loadMore} className="mt-3 rounded-lg border border-border px-4 py-2 text-sm text-text hover:bg-surface-2">{c.more}</button>
        ) : null}
      </section>
    </div>
  )
}

export default AdvertiserPage
