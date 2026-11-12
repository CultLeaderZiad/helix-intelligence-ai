import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { CheckCircle2, ExternalLink, Plus, RefreshCw, Tag } from "lucide-react"
import { adminService } from "@/services"
import { useLanguage } from "@/context/LanguageContext"
import { adminMessage } from "@/i18n/adminMessages"

const EMPTY_CARD = {
  listed: false,
  order: 0,
  highlight: false,
  cta: "trial",
  badge: { en: "", ar: "" },
  tagline: { en: "", ar: "" },
  period: { en: "", ar: "" },
  features: { en: [], ar: [] },
}

/** A plan's pricing card with every field present, so the form is always controlled. */
export function normalizeCard(card) {
  const c = card || {}
  const pair = (v) => ({ en: v?.en ?? "", ar: v?.ar ?? "" })
  return {
    ...EMPTY_CARD,
    ...c,
    badge: pair(c.badge),
    tagline: pair(c.tagline),
    period: pair(c.period),
    features: { en: [...(c.features?.en ?? [])], ar: [...(c.features?.ar ?? [])] },
  }
}

/** Admin form values -> API limits. Blank means "use the global default" (null). */
export function limitsFromForm(form) {
  const num = (v) => (v === "" || v === null || v === undefined ? null : Math.max(0, Math.floor(Number(v)) || 0))
  const cadences = ["daily", "weekly"].filter((c) => form.cadences?.[c])
  return {
    searches_per_day: num(form.searches),
    monitors: num(form.monitors),
    records_per_month: num(form.records),
    monitor_cadences: cadences.length === 0 || cadences.length === 2 ? null : cadences,
  }
}

/** API limits -> admin form values. */
export function limitsToForm(limits) {
  const l = limits || {}
  const allowed = l.monitor_cadences
  return {
    searches: l.searches_per_day ?? "",
    monitors: l.monitors ?? "",
    records: l.records_per_month ?? "",
    cadences: { daily: !allowed || allowed.includes("daily"), weekly: !allowed || allowed.includes("weekly") },
  }
}

/** One feature per line; blank lines dropped. */
export function linesToList(text) {
  return String(text || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
}

function TextPair({ label, value, onChange, t }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {["en", "ar"].map((lng) => (
        <label key={lng} className="block">
          <span className="font-mono text-[11px] text-slate-400">
            {t(label)} · {lng.toUpperCase()}
          </span>
          <input
            type="text"
            dir={lng === "ar" ? "rtl" : "ltr"}
            value={value[lng]}
            maxLength={160}
            onChange={(e) => onChange({ ...value, [lng]: e.target.value })}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
          />
        </label>
      ))}
    </div>
  )
}

function PlanEditor({ plan, lang, onClose, onSaved }) {
  const t = (msg, values) => adminMessage(lang, msg, values)
  const [name, setName] = useState(plan.name)
  const [price, setPrice] = useState(plan.price_monthly ?? 0)
  const [card, setCard] = useState(() => normalizeCard(plan.pricing))
  const [featuresText, setFeaturesText] = useState(() => ({
    en: normalizeCard(plan.pricing).features.en.join("\n"),
    ar: normalizeCard(plan.pricing).features.ar.join("\n"),
  }))
  const [limits, setLimits] = useState(() => limitsToForm(plan.limits))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function save(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await adminService.updatePlan(plan.id, {
        name: name.trim() || plan.name,
        price_monthly: Number(price) || 0,
        limits: limitsFromForm(limits),
        pricing: {
          ...card,
          order: Math.max(0, Math.min(99, Number(card.order) || 0)),
          features: { en: linesToList(featuresText.en), ar: linesToList(featuresText.ar) },
        },
      })
      onSaved(t("Pricing saved for {name}.", { name: name.trim() || plan.name }))
    } catch (err) {
      console.error("Failed to save pricing", err)
      setError(t("Could not save pricing. Only full admins can edit plans."))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/80 p-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="pricing-editor-title"
        className="my-8 w-full max-w-2xl space-y-4 rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl"
      >
        <h3 id="pricing-editor-title" className="flex items-center gap-2 text-lg font-bold text-slate-100">
          <Tag className="h-5 w-5 text-lime-300" aria-hidden="true" />
          {t("Edit pricing: {name}", { name: plan.name })}
        </h3>
        {error ? (
          <div role="alert" className="rounded border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-300">
            {error}
          </div>
        ) : null}
        <form onSubmit={save} className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block sm:col-span-2">
              <span className="font-mono text-[11px] text-slate-400">{t("Plan name")}</span>
              <input
                type="text"
                value={name}
                required
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
              />
            </label>
            <label className="block">
              <span className="font-mono text-[11px] text-slate-400">{t("Monthly price (USD, 0 = custom)")}</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
              />
            </label>
          </div>

          <fieldset className="rounded border border-slate-800 bg-slate-950/40 p-3">
            <legend className="px-1 font-mono text-[11px] text-slate-400">{t("Enforced limits (blank = default)")}</legend>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-200">
              <label className="flex items-center gap-2">
                {t("Searches a day")}
                <input
                  type="number"
                  min="0"
                  max="1000"
                  value={limits.searches}
                  onChange={(e) => setLimits({ ...limits, searches: e.target.value })}
                  className="w-20 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100"
                />
              </label>
              <label className="flex items-center gap-2">
                {t("Active monitors")}
                <input
                  type="number"
                  min="0"
                  max="500"
                  value={limits.monitors}
                  onChange={(e) => setLimits({ ...limits, monitors: e.target.value })}
                  className="w-20 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100"
                />
              </label>
              <label className="flex items-center gap-2">
                {t("Data records a month")}
                <input
                  type="number"
                  min="0"
                  max="100000"
                  value={limits.records}
                  onChange={(e) => setLimits({ ...limits, records: e.target.value })}
                  className="w-24 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100"
                />
              </label>
              {["daily", "weekly"].map((cad) => (
                <label key={cad} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={limits.cadences[cad]}
                    onChange={(e) => setLimits({ ...limits, cadences: { ...limits.cadences, [cad]: e.target.checked } })}
                  />
                  {t(cad === "daily" ? "Daily monitors" : "Weekly monitors")}
                </label>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-slate-500">
              {t("Applied on the server to every workspace on this plan. Searches also cap provider calls at twice this number.")}
            </p>
          </fieldset>

          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-200">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={card.listed} onChange={(e) => setCard({ ...card, listed: e.target.checked })} />
              {t("Show on the pricing page")}
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={card.highlight} onChange={(e) => setCard({ ...card, highlight: e.target.checked })} />
              {t("Highlight as popular")}
            </label>
            <label className="flex items-center gap-2">
              {t("Order")}
              <input
                type="number"
                min="0"
                max="99"
                value={card.order}
                onChange={(e) => setCard({ ...card, order: e.target.value })}
                className="w-16 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100"
              />
            </label>
            <label className="flex items-center gap-2">
              {t("Button")}
              <select
                value={card.cta}
                onChange={(e) => setCard({ ...card, cta: e.target.value })}
                className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100"
              >
                <option value="trial">{t("Start free trial")}</option>
                <option value="contact">{t("Contact us")}</option>
              </select>
            </label>
          </div>

          <TextPair label="Badge" value={card.badge} onChange={(badge) => setCard({ ...card, badge })} t={t} />
          <TextPair label="Tagline" value={card.tagline} onChange={(tagline) => setCard({ ...card, tagline })} t={t} />
          <TextPair label="Price period" value={card.period} onChange={(period) => setCard({ ...card, period })} t={t} />

          <div className="grid gap-2 sm:grid-cols-2">
            {["en", "ar"].map((lng) => (
              <label key={lng} className="block">
                <span className="font-mono text-[11px] text-slate-400">
                  {t("Features, one per line")} · {lng.toUpperCase()}
                </span>
                <textarea
                  rows={6}
                  dir={lng === "ar" ? "rtl" : "ltr"}
                  value={featuresText[lng]}
                  onChange={(e) => setFeaturesText({ ...featuresText, [lng]: e.target.value })}
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
                />
              </label>
            ))}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="rounded bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700">
              {t("Cancel")}
            </button>
            <button
              type="submit"
              disabled={busy}
              className="rounded bg-lime-300 px-4 py-1.5 text-xs font-bold text-slate-950 hover:bg-lime-200"
            >
              {busy ? t("Saving...") : t("Save pricing")}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/** Admin: every plan's public pricing card. Only full admins can save (enforced by the API). */
export function PricingAdminPage() {
  const { lang, isRtl } = useLanguage()
  const t = (msg, values) => adminMessage(lang, msg, values)
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [editing, setEditing] = useState(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await adminService.listPlans()
      setPlans(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error("Failed to load plans", err)
      setError(t("Failed to load plans."))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  function saved(msg) {
    setEditing(null)
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
    load()
  }

  async function createPlan() {
    setError(null)
    try {
      const plan = await adminService.createPlan({
        name: t("New plan"),
        type: "custom",
        price_monthly: 0,
        feature_flags: { discover: true, swipe_files: true, monitors: true },
        pricing: { ...EMPTY_CARD },
      })
      await load()
      setEditing(plan)
    } catch (err) {
      console.error("Failed to create plan", err)
      setError(t("Could not create a plan. Only full admins can edit plans."))
    }
  }

  return (
    <div dir={isRtl ? "rtl" : "ltr"} className="mx-auto w-full max-w-6xl space-y-6 p-6 font-sans md:p-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-3 text-2xl font-bold text-slate-100">
            <Tag className="h-7 w-7 text-lime-300" aria-hidden="true" />
            {t("Pricing")}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {t("Edit what each plan shows on the public pricing page. The free 7-day trial card is always shown first.")}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/pricing"
            target="_blank"
            className="flex items-center gap-2 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
          >
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            {t("View pricing page")}
          </Link>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="flex items-center gap-2 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} aria-hidden="true" />
            {t("Refresh")}
          </button>
          <button
            type="button"
            onClick={createPlan}
            className="flex items-center gap-2 rounded bg-lime-300 px-3 py-1.5 text-xs font-bold text-slate-950 hover:bg-lime-200"
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            {t("New plan")}
          </button>
        </div>
      </div>

      {toast ? (
        <div className="flex items-center gap-2 rounded border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-400">
          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
          {toast}
        </div>
      ) : null}
      {error ? (
        <div role="alert" className="rounded border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
          {error}
        </div>
      ) : null}

      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/80">
        <table className="w-full min-w-[640px] text-start text-sm text-slate-300">
          <thead className="border-b border-slate-800 bg-slate-950/60 font-mono text-xs uppercase tracking-wider text-slate-400">
            <tr>
              <th className="px-4 py-3 text-start">{t("Plan")}</th>
              <th className="px-4 py-3 text-start">{t("Monthly price")}</th>
              <th className="px-4 py-3 text-start">{t("On pricing page")}</th>
              <th className="px-4 py-3 text-start">{t("Limits")}</th>
              <th className="px-4 py-3 text-end">{t("Actions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-xs">
            {loading ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">{t("Loading plans...")}</td>
              </tr>
            ) : plans.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">{t("No plans yet.")}</td>
              </tr>
            ) : (
              plans.map((plan) => {
                const card = normalizeCard(plan.pricing)
                return (
                  <tr key={plan.id} className="hover:bg-slate-800/40">
                    <td className="px-4 py-3">
                      <div className="text-sm font-semibold text-slate-200">{plan.name}</div>
                      <div className="font-mono text-[11px] text-slate-500">{plan.id}</div>
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {plan.price_monthly > 0 ? `$${Number(plan.price_monthly).toFixed(2)}` : t("Custom")}
                    </td>
                    <td className="px-4 py-3">
                      {card.listed ? (
                        <span className="rounded border border-lime-300/30 bg-lime-300/10 px-2 py-0.5 text-lime-200">
                          {t("Listed")} · #{card.order}
                          {card.highlight ? ` · ${t("Popular")}` : ""}
                        </span>
                      ) : (
                        <span className="text-slate-500">{t("Hidden")}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-400">
                      {plan.limits?.searches_per_day ?? "—"} / {t("day")} · {plan.limits?.monitors ?? "—"} {t("monitors")}
                    </td>
                    <td className="px-4 py-3 text-end">
                      <button
                        type="button"
                        onClick={() => setEditing(plan)}
                        className="rounded border border-lime-300/30 bg-lime-300/10 px-2.5 py-1 text-lime-200 hover:bg-lime-300/20"
                      >
                        {t("Edit pricing")}
                      </button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {editing ? <PlanEditor plan={editing} lang={lang} onClose={() => setEditing(null)} onSaved={saved} /> : null}
    </div>
  )
}

export default PricingAdminPage
