import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { Check, Send, Sparkles } from "lucide-react"
import agentService from "@/services/api/agentService.api"
import { useLanguage } from "@/context/LanguageContext"

export const AGENT_COPY = {
  en: {
    title: "Ask Helix",
    intro: "Ask about your saved ads, monitors, stored searches and competitors. Helix only reads your workspace; anything it suggests runs only after you approve it.",
    placeholder: "e.g. What is Acme doing this month?",
    send: "Ask",
    thinking: "Thinking…",
    usage: (u, c) => `${u} of ${c} questions used today`,
    genUsage: (u, c) => `${u} of ${c} generations used today`,
    sources: "Sources",
    approve: "Approve",
    approved: "Done",
    failed: "Helix could not answer. Nothing was counted; try again later.",
    label: "AI answer based on your workspace data. Check important facts.",
    genTitle: "Write ad drafts from a winning ad",
    genAd: "Ad id",
    genProduct: "Your product (what it is, who it is for, what is true about it)",
    genLang: "Language",
    genDialect: "Dialect",
    generate: "Write 5 drafts",
    generating: "Writing…",
    drafts: "AI-generated drafts. Review before use.",
    fields: { primary_text: "Primary text", headline: "Headline", cta: "CTA", ugc_script: "UGC script", image_prompt: "Image prompt" },
    dialects: { egyptian: "Egyptian", gulf: "Gulf", levantine: "Levantine", msa: "Modern Standard" },
  },
  ar: {
    title: "اسأل Helix",
    intro: "اسأل عن إعلاناتك المحفوظة والمراقبة وعمليات البحث المخزّنة والمنافسين. Helix يقرأ مساحة عملك فقط، وأي إجراء يقترحه لا يُنفَّذ إلا بعد موافقتك.",
    placeholder: "مثال: ماذا تفعل Acme هذا الشهر؟",
    send: "اسأل",
    thinking: "جارٍ التفكير…",
    usage: (u, c) => `استُخدم ${u} من ${c} سؤال اليوم`,
    genUsage: (u, c) => `استُخدم ${u} من ${c} توليد اليوم`,
    sources: "المصادر",
    approve: "موافقة",
    approved: "تم",
    failed: "تعذّر على Helix الإجابة. لم يُحتسب شيء؛ حاول لاحقاً.",
    label: "إجابة بالذكاء الاصطناعي مبنية على بيانات مساحة عملك. تحقّق من المعلومات المهمة.",
    genTitle: "اكتب مسودات إعلانات من إعلان ناجح",
    genAd: "رقم الإعلان",
    genProduct: "منتجك (ما هو، ولمن، وما الصحيح عنه)",
    genLang: "اللغة",
    genDialect: "اللهجة",
    generate: "اكتب 5 مسودات",
    generating: "جارٍ الكتابة…",
    drafts: "مسودات مولّدة بالذكاء الاصطناعي. راجعها قبل الاستخدام.",
    fields: { primary_text: "النص الأساسي", headline: "العنوان", cta: "الدعوة لاتخاذ إجراء", ugc_script: "سكريبت UGC", image_prompt: "وصف الصورة" },
    dialects: { egyptian: "مصري", gulf: "خليجي", levantine: "شامي", msa: "فصحى" },
  },
}

function errorText(err, fallback) {
  return err?.detail?.message || (typeof err?.detail === "string" ? err.detail : null) || fallback
}

export function AgentPage() {
  const { lang } = useLanguage()
  const c = lang === "ar" ? AGENT_COPY.ar : AGENT_COPY.en
  const [params] = useSearchParams()
  const [limits, setLimits] = useState(null)
  const [turns, setTurns] = useState([])
  const [question, setQuestion] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [done, setDone] = useState({})
  const [gen, setGen] = useState({ creativeId: params.get("ad") || "", product: "", language: lang === "ar" ? "ar" : "en", dialect: "egyptian" })
  const [drafts, setDrafts] = useState(null)
  const [genBusy, setGenBusy] = useState(false)
  const [genError, setGenError] = useState("")

  const refreshLimits = () => agentService.limits().then(setLimits).catch(() => setLimits(null))
  useEffect(() => { refreshLimits() }, [])

  async function ask(e) {
    e.preventDefault()
    const q = question.trim()
    if (!q) return
    setBusy(true)
    setError("")
    const history = turns.flatMap((t) => [{ role: "user", content: t.q }, { role: "assistant", content: t.a.answer }]).slice(-12)
    try {
      const a = await agentService.ask(q, history, lang)
      setTurns([...turns, { q, a }])
      setQuestion("")
    } catch (err) {
      setError(errorText(err, c.failed))
    } finally {
      setBusy(false)
      refreshLimits()
    }
  }

  async function approve(key, proposal) {
    try {
      await agentService.approve(proposal)
      setDone({ ...done, [key]: true })
    } catch (err) {
      setError(errorText(err, c.failed))
    }
  }

  async function generate(e) {
    e.preventDefault()
    setGenBusy(true)
    setGenError("")
    try {
      setDrafts(await agentService.generate(gen))
    } catch (err) {
      setGenError(errorText(err, c.failed))
    } finally {
      setGenBusy(false)
      refreshLimits()
    }
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-4 sm:p-6">
      <header>
        <h1 className="text-2xl font-semibold text-text">{c.title}</h1>
        <p className="mt-1 text-sm text-text-muted">{c.intro}</p>
        {limits ? (
          <p className="mt-1 text-xs text-text-faint">
            {c.usage(limits.messages_used, limits.messages_per_day)} · {c.genUsage(limits.generations_used, limits.generations_per_day)}
          </p>
        ) : null}
      </header>

      <section className="flex flex-col gap-4">
        {turns.map((t, i) => (
          <div key={i} className="flex flex-col gap-2">
            <p className="self-end rounded-lg bg-surface-2 px-3 py-2 text-sm text-text" dir="auto">{t.q}</p>
            <div className="rounded-lg border border-border p-3">
              <p className="whitespace-pre-wrap text-sm text-text" dir="auto">{t.a.answer}</p>
              {t.a.citations?.length ? (
                <p className="mt-2 text-xs text-text-muted">
                  {c.sources}: {t.a.citations.map((x) => `${x.type}:${x.id}`).join(", ")}
                </p>
              ) : null}
              {(t.a.proposals || []).map((p, j) => {
                const key = `${i}-${j}`
                return (
                  <div key={key} className="mt-2 flex items-center justify-between gap-2 rounded border border-border px-3 py-2 text-xs">
                    <span dir="auto">{p.summary}</span>
                    <button type="button" disabled={done[key]} onClick={() => approve(key, p)}
                      className="inline-flex items-center gap-1 rounded bg-accent px-2.5 py-1 font-semibold text-black disabled:opacity-60">
                      <Check className="h-3 w-3" aria-hidden="true" /> {done[key] ? c.approved : c.approve}
                    </button>
                  </div>
                )
              })}
              <p className="mt-2 text-[11px] text-text-faint">{c.label}</p>
            </div>
          </div>
        ))}
        {error ? <p role="alert" className="text-sm text-rose-300">{error}</p> : null}
        <form onSubmit={ask} className="flex gap-2">
          <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={c.placeholder} maxLength={2000} dir="auto"
            className="min-h-10 flex-1 rounded-lg border border-border bg-surface-2 px-3 text-sm text-text" />
          <button type="submit" disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-black disabled:opacity-60">
            <Send className="h-4 w-4" aria-hidden="true" /> {busy ? c.thinking : c.send}
          </button>
        </form>
      </section>

      <section className="rounded-lg border border-border p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-text"><Sparkles className="h-4 w-4" aria-hidden="true" /> {c.genTitle}</h2>
        <form onSubmit={generate} className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs text-text-muted">{c.genAd}
            <input required value={gen.creativeId} onChange={(e) => setGen({ ...gen, creativeId: e.target.value })} dir="ltr"
              className="rounded border border-border bg-surface-2 px-2 py-1.5 text-sm text-text" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-text-muted">{c.genLang}
            <select value={gen.language} onChange={(e) => setGen({ ...gen, language: e.target.value })}
              className="rounded border border-border bg-surface-2 px-2 py-1.5 text-sm text-text">
              <option value="ar">العربية</option>
              <option value="en">English</option>
            </select>
          </label>
          {gen.language === "ar" ? (
            <label className="flex flex-col gap-1 text-xs text-text-muted">{c.genDialect}
              <select value={gen.dialect} onChange={(e) => setGen({ ...gen, dialect: e.target.value })}
                className="rounded border border-border bg-surface-2 px-2 py-1.5 text-sm text-text">
                {Object.entries(c.dialects).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </label>
          ) : null}
          <label className="flex flex-col gap-1 text-xs text-text-muted sm:col-span-2">{c.genProduct}
            <textarea required minLength={10} maxLength={500} rows={3} value={gen.product} dir="auto"
              onChange={(e) => setGen({ ...gen, product: e.target.value })}
              className="rounded border border-border bg-surface-2 px-2 py-1.5 text-sm text-text" />
          </label>
          <button type="submit" disabled={genBusy} className="self-start rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-black disabled:opacity-60">
            {genBusy ? c.generating : c.generate}
          </button>
        </form>
        {genError ? <p role="alert" className="mt-2 text-sm text-rose-300">{genError}</p> : null}
        {drafts ? (
          <div className="mt-4 flex flex-col gap-3">
            <p className="text-xs text-amber-200">{c.drafts}</p>
            {drafts.variants.map((v, i) => (
              <dl key={i} className="rounded border border-border p-3 text-sm">
                {Object.entries(c.fields).map(([k, label]) => (
                  <div key={k} className="mt-1">
                    <dt className="text-xs text-text-muted">{label}</dt>
                    <dd className="whitespace-pre-wrap text-text" dir="auto">{v[k]}</dd>
                  </div>
                ))}
              </dl>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  )
}

export default AgentPage
