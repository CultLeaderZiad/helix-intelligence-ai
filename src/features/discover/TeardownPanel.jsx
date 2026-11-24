import { useEffect, useState } from "react"
import { Sparkles } from "lucide-react"
import { creativeService } from "@/services"
import { useLanguage } from "@/context/LanguageContext"

export const TEARDOWN_COPY = {
  en: {
    analyse: "Analyse this ad",
    analysing: "Analysing…",
    label: "AI analysis of the ad's public text. Audience is a guess. Not performance data.",
    fields: { hook: "Hook", angle: "Angle", offer: "Offer", cta: "CTA", format: "Format", target_audience_guess: "Audience (guess)" },
    notShown: "Not shown in the ad",
    failed: "The analysis could not be completed. Nothing was saved; try again later.",
  },
  ar: {
    analyse: "حلّل هذا الإعلان",
    analysing: "جارٍ التحليل…",
    label: "تحليل بالذكاء الاصطناعي لنص الإعلان العام. الجمهور تخمين. ليست بيانات أداء.",
    fields: { hook: "الخطّاف", angle: "الزاوية", offer: "العرض", cta: "الدعوة لاتخاذ إجراء", format: "الصيغة", target_audience_guess: "الجمهور (تخمين)" },
    notShown: "غير ظاهر في الإعلان",
    failed: "تعذّر إكمال التحليل. لم يُحفظ شيء؛ حاول لاحقاً.",
  },
}

export function TeardownPanel({ creativeId }) {
  const { lang } = useLanguage()
  const c = lang === "ar" ? TEARDOWN_COPY.ar : TEARDOWN_COPY.en
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    let active = true
    setResult(null)
    setError("")
    // A cached analysis is free to show; a 404 just means "not analysed yet".
    creativeService.getTeardown(creativeId).then((r) => { if (active) setResult(r) }).catch(() => {})
    return () => { active = false }
  }, [creativeId])

  async function analyse() {
    setBusy(true)
    setError("")
    try {
      setResult(await creativeService.createTeardown(creativeId))
    } catch (err) {
      setError(err?.detail?.message || c.failed)
    } finally {
      setBusy(false)
    }
  }

  if (!result) {
    return (
      <div className="flex flex-col gap-1">
        <button type="button" onClick={analyse} disabled={busy}
          className="inline-flex items-center justify-center gap-2 rounded border border-border px-3 py-1.5 text-xs font-medium text-text hover:bg-surface-2 disabled:opacity-60">
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" /> {busy ? c.analysing : c.analyse}
        </button>
        {error ? <p role="alert" className="text-xs text-rose-300">{error}</p> : null}
      </div>
    )
  }

  return (
    <section className="rounded border border-border p-3" aria-label={c.analyse}>
      <dl className="grid grid-cols-1 gap-1.5 text-xs">
        {Object.entries(c.fields).map(([key, label]) => (
          <div key={key} className="flex gap-2">
            <dt className="w-28 shrink-0 text-text-muted">{label}</dt>
            <dd className="text-text" dir="auto">{result[key] || <span className="text-text-faint">{c.notShown}</span>}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-[11px] text-text-faint">{c.label}</p>
    </section>
  )
}

export default TeardownPanel
