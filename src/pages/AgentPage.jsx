import { useEffect, useMemo, useRef, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { AtSign, Check, History, Sparkles, X } from "lucide-react"
import agentService from "@/services/api/agentService.api"
import { useLanguage } from "@/context/LanguageContext"
import { PromptBox } from "@/components/ui/prompt-box/PromptBox"
import { ModelPicker } from "@/components/ui/prompt-box/ModelPicker"
import { ConversationHistory } from "@/features/agent/ConversationHistory"
import { HISTORY_COPY } from "@/features/agent/historyCopy"
import { DraftsFolder } from "@/features/library/DraftsFolder"

export const ASSISTANT_NAME = "Cyreax-Z.1"
const MAX_REFERENCES = 5
const MENTION_PATTERN = /(^|\s)@([^\s@]{0,40})$/

export const AGENT_COPY = {
  en: {
    title: "Ask Helix",
    intro: "Ask about your saved ads, monitors, stored searches and competitors. Type @ to point at a search, draft, board or monitor. Helix only reads your workspace; anything it suggests runs only after you approve it.",
    placeholder: "e.g. What is Acme doing this month?",
    placeholders: ["Ask about your ads, monitors or competitors", "Type @ to mention a search, draft or board", "Hold the arrow to think harder"],
    usage: (u, c) => `${u} of ${c} questions used today`,
    genUsage: (u, c) => `${u} of ${c} generations used today`,
    sources: "Sources",
    attached: "Based on",
    approve: "Approve",
    approved: "Done",
    failed: "Helix could not answer. Nothing was counted; try again later.",
    stopped: "Stopped.",
    ...HISTORY_COPY.en,
    analysing: "Analysing…",
    label: "AI answer based on your workspace data. Check important facts.",
    model: "Model",
    modelDescription: "Reads your workspace and the Helix knowledge base, and only suggests changes.",
    holdHint: "Hold to think harder",
    efforts: { quick: "Quick", think: "Think", deep: "Think deeply" },
    send: "Send, hold to think harder",
    stop: "Stop",
    mention: "Mention something from your workspace",
    mentionLoading: "Loading…",
    mentionNone: "Nothing matches. Run a search in Discover or save a draft first.",
    mentionTypes: { search: "Search", draft: "Draft", board: "Board", monitor: "Monitor", ad: "Ad" },
    removeReference: "Remove",
    missing: "Some mentioned items could not be read and were skipped.",
    shortcutsTitle: "Quick start",
    shortcuts: {
      search: { label: "Analyse my latest search", prompt: "Analyse the ads in this search: the hooks, angles and offers they use and what stands out. Use the knowledge base to say what I should do next." },
      monitor: { label: "What changed in my monitor?", prompt: "What changed recently in this monitor? Go through the new, removed and changed ads and say what they suggest." },
      board: { label: "Summarise my board", prompt: "Summarise this board: what these ads have in common, the strongest angles, and what is missing." },
      ideas: { label: "Ideas for my next ad", prompt: "Using these ads and the knowledge base, give me five angles to test in my next ad and why." },
    },
    shortcutNeeds: {
      search: "You have no finished search yet. Run one in Discover first.",
      monitor: "You have no monitor yet. Create one in Monitors first.",
      board: "You have no board yet. Save ads into a board first.",
    },
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
    intro: "اسأل عن إعلاناتك المحفوظة والمراقبة وعمليات البحث المخزّنة والمنافسين. اكتب @ للإشارة إلى بحث أو مسودة أو لوحة أو مراقبة. Helix يقرأ مساحة عملك فقط، وأي إجراء يقترحه لا يُنفَّذ إلا بعد موافقتك.",
    placeholder: "مثال: ماذا تفعل Acme هذا الشهر؟",
    placeholders: ["اسأل عن إعلاناتك أو مراقباتك أو منافسيك", "اكتب @ للإشارة إلى بحث أو مسودة أو لوحة", "اضغط مطولاً على السهم ليفكر أكثر"],
    usage: (u, c) => `استُخدم ${u} من ${c} سؤال اليوم`,
    genUsage: (u, c) => `استُخدم ${u} من ${c} توليد اليوم`,
    sources: "المصادر",
    attached: "بناءً على",
    approve: "موافقة",
    approved: "تم",
    failed: "تعذّر على Helix الإجابة. لم يُحتسب شيء؛ حاول لاحقاً.",
    stopped: "تم الإيقاف.",
    ...HISTORY_COPY.ar,
    analysing: "جارٍ التحليل…",
    label: "إجابة بالذكاء الاصطناعي مبنية على بيانات مساحة عملك. تحقّق من المعلومات المهمة.",
    model: "النموذج",
    modelDescription: "يقرأ مساحة عملك وقاعدة معرفة Helix، ويقترح التغييرات فقط.",
    holdHint: "اضغط مطولاً ليفكر أكثر",
    efforts: { quick: "سريع", think: "تفكير", deep: "تفكير عميق" },
    send: "إرسال، اضغط مطولاً ليفكر أكثر",
    stop: "إيقاف",
    mention: "أشِر إلى شيء من مساحة عملك",
    mentionLoading: "جارٍ التحميل…",
    mentionNone: "لا نتائج. شغّل بحثاً في Discover أو احفظ مسودة أولاً.",
    mentionTypes: { search: "بحث", draft: "مسودة", board: "لوحة", monitor: "مراقبة", ad: "إعلان" },
    removeReference: "إزالة",
    missing: "تعذّرت قراءة بعض العناصر المذكورة وتم تخطيها.",
    shortcutsTitle: "ابدأ بسرعة",
    shortcuts: {
      search: { label: "حلّل آخر بحث لي", prompt: "حلّل الإعلانات في هذا البحث: الخطافات والزوايا والعروض المستخدمة وما يلفت النظر. استخدم قاعدة المعرفة لتقول ماذا أفعل بعد ذلك." },
      monitor: { label: "ماذا تغيّر في مراقبتي؟", prompt: "ماذا تغيّر مؤخراً في هذه المراقبة؟ راجع الإعلانات الجديدة والمحذوفة والمعدّلة وقل ما تشير إليه." },
      board: { label: "لخّص لوحتي", prompt: "لخّص هذه اللوحة: ما الذي تشترك فيه هذه الإعلانات، وأقوى الزوايا، وما الناقص." },
      ideas: { label: "أفكار لإعلاني القادم", prompt: "باستخدام هذه الإعلانات وقاعدة المعرفة، أعطني خمس زوايا أجرّبها في إعلاني القادم ولماذا." },
    },
    shortcutNeeds: {
      search: "ليس لديك بحث مكتمل بعد. شغّل بحثاً في Discover أولاً.",
      monitor: "ليس لديك مراقبة بعد. أنشئ واحدة في المراقبة أولاً.",
      board: "ليس لديك لوحة بعد. احفظ إعلانات في لوحة أولاً.",
    },
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

// Which kind of mention each quick-start window needs, and the prompt it sends.
const SHORTCUTS = [
  { id: "search", needs: "search" },
  { id: "monitor", needs: "monitor" },
  { id: "board", needs: "board" },
  { id: "ideas", needs: "search" },
]

function errorText(err, fallback) {
  return err?.detail?.message || (typeof err?.detail === "string" ? err.detail : null) || err?.message || fallback
}

/** The mention under the caret ("@" then a few characters), or null. */
export function mentionAt(text, caret) {
  const before = String(text).slice(0, caret)
  const match = MENTION_PATTERN.exec(before)
  if (!match) return null
  const query = match[2]
  return { query, start: caret - query.length - 1, end: caret }
}

export function AgentPage() {
  const { lang } = useLanguage()
  const c = lang === "ar" ? AGENT_COPY.ar : AGENT_COPY.en
  const [params] = useSearchParams()
  const [limits, setLimits] = useState(null)
  const [turns, setTurns] = useState([])
  const [value, setValue] = useState("")
  const [references, setReferences] = useState([])
  const [pending, setPending] = useState(false)
  const [error, setError] = useState("")
  const [done, setDone] = useState({})
  const [menu, setMenu] = useState(null)
  const [gen, setGen] = useState({ creativeId: params.get("ad") || "", product: "", language: lang === "ar" ? "ar" : "en", dialect: "egyptian" })
  const [drafts, setDrafts] = useState(null)
  const [genBusy, setGenBusy] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [showHistory, setShowHistory] = useState(false)
  const [historyTick, setHistoryTick] = useState(0)
  const [genError, setGenError] = useState("")
  const inputRef = useRef(null)
  const abortRef = useRef(null)
  const mentionTimer = useRef(undefined)
  const mentionSeq = useRef(0)

  const refreshLimits = () => agentService.limits().then(setLimits).catch(() => setLimits(null))
  useEffect(() => { refreshLimits() }, [])
  useEffect(() => () => {
    window.clearTimeout(mentionTimer.current)
    abortRef.current?.abort()
  }, [])

  const efforts = useMemo(() => [
    { id: "quick", label: c.efforts.quick },
    { id: "think", label: c.efforts.think, color: "#F5A524" },
    { id: "deep", label: c.efforts.deep, color: "#F2552C" },
  ], [c])
  const models = useMemo(() => [
    { id: "cyreax-z1", name: ASSISTANT_NAME, icon: <Sparkles className="size-4" aria-hidden="true" />, description: c.modelDescription },
  ], [c])

  // --- @ mentions ---------------------------------------------------------
  function closeMenu() {
    window.clearTimeout(mentionTimer.current)
    mentionSeq.current += 1
    setMenu(null)
  }

  function updateMenu(element) {
    if (!element) return
    const found = mentionAt(element.value, element.selectionStart ?? element.value.length)
    if (!found) {
      closeMenu()
      return
    }
    setMenu((current) => ({ ...found, items: current?.items ?? [], active: 0, loading: true }))
    window.clearTimeout(mentionTimer.current)
    const seq = ++mentionSeq.current
    mentionTimer.current = window.setTimeout(async () => {
      try {
        const { items } = await agentService.mentions(found.query)
        if (seq === mentionSeq.current) setMenu({ ...found, items, active: 0, loading: false })
      } catch {
        if (seq === mentionSeq.current) setMenu({ ...found, items: [], active: 0, loading: false })
      }
    }, 180)
  }

  function pick(item) {
    if (!item || !menu) return
    setReferences((current) => (
      current.length >= MAX_REFERENCES || current.some((r) => r.type === item.type && r.id === item.id)
        ? current
        : [...current, { type: item.type, id: item.id, label: item.label }]
    ))
    setValue((text) => `${text.slice(0, menu.start)}${text.slice(menu.end)}`.replace(/\s{2,}/g, " "))
    closeMenu()
    inputRef.current?.focus()
  }

  function onInputKeyDown(event) {
    if (!menu) return
    if (event.key === "Escape") {
      event.preventDefault()
      closeMenu()
      return
    }
    if (!menu.items.length) return
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault()
      const step = event.key === "ArrowDown" ? 1 : -1
      setMenu({ ...menu, active: (menu.active + step + menu.items.length) % menu.items.length })
    } else if (event.key === "Enter" || event.key === "Tab") {
      event.preventDefault()
      pick(menu.items[menu.active])
    }
  }

  function startMention() {
    const element = inputRef.current
    if (!element) return
    setValue((text) => `${text}${text && !/\s$/.test(text) ? " " : ""}@`)
    element.focus()
    window.setTimeout(() => updateMenu(inputRef.current), 0)
  }

  // --- asking -------------------------------------------------------------
  async function send(question, effort, refs) {
    const text = question.trim()
    if (!text || pending) return
    setPending(true)
    setError("")
    closeMenu()
    const history = turns.flatMap((t) => (t.a ? [{ role: "user", content: t.q }, { role: "assistant", content: t.a.answer }] : [])).slice(-12)
    const id = Date.now() + Math.random()
    setTurns((current) => [...current, { id, q: text, refs, a: null }])
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const answer = await agentService.ask(text, history, lang, { references: refs, effort, signal: controller.signal, conversationId })
      setTurns((current) => current.map((t) => (t.id === id ? { ...t, a: answer } : t)))
      if (answer?.conversation_id) setConversationId(answer.conversation_id)
      setHistoryTick((n) => n + 1)
    } catch (err) {
      const stopped = err?.name === "AbortError"
      setTurns((current) => current.map((t) => (t.id === id ? { ...t, failed: stopped ? c.stopped : errorText(err, c.failed) } : t)))
    } finally {
      abortRef.current = null
      setPending(false)
      refreshLimits()
    }
  }

  function newChat() {
    abortRef.current?.abort()
    setTurns([])
    setConversationId(null)
    setError("")
    setDone({})
  }

  // Turn a saved conversation back into the page's question/answer pairs.
  function openConversation(conversation) {
    const rows = conversation?.messages ?? []
    const next = []
    for (let i = 0; i < rows.length; i += 1) {
      if (rows[i].role !== "user") continue
      const reply = rows[i + 1]?.role === "assistant" ? rows[i + 1] : null
      next.push({
        id: rows[i].id,
        q: rows[i].content,
        refs: [],
        a: reply ? { ...reply, answer: reply.content } : null,
        failed: reply ? undefined : c.failed,
      })
    }
    setTurns(next)
    setConversationId(conversation.id)
    setError("")
    setDone({})
  }

  function onSubmit(prompt, effort) {
    const refs = references
    setReferences([])
    send(prompt, effort.id, refs)
  }

  // A quick-start window: find the user's own latest thing of the right kind, attach it, and ask.
  async function runShortcut(shortcut) {
    if (pending) return
    setError("")
    try {
      const { items } = await agentService.mentions("")
      const found = items.find((item) => item.type === shortcut.needs)
      if (!found) {
        setError(c.shortcutNeeds[shortcut.needs])
        return
      }
      send(c.shortcuts[shortcut.id].prompt, "think", [{ type: found.type, id: found.id, label: found.label }])
    } catch (err) {
      setError(errorText(err, c.failed))
    }
  }

  async function approve(key, proposal) {
    try {
      await agentService.approve(proposal)
      setDone((current) => ({ ...current, [key]: true }))
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
    <div className={`mx-auto flex w-full min-w-0 max-w-4xl flex-col gap-6 p-4 sm:p-6 ${turns.length === 0 && !pending ? "min-h-[85dvh] justify-center pt-[14dvh]" : ""}`}>
      <section className="flex flex-col gap-4" aria-live="polite">
        {turns.map((t) => (
          <div key={t.id} className="flex flex-col gap-2">
            <p className="max-w-[85%] self-end rounded-lg bg-surface-2 px-3 py-2 text-sm text-text" dir="auto">{t.q}</p>
            {t.refs?.length ? (
              <p className="self-end text-xs text-text-muted">{c.attached}: {t.refs.map((r) => r.label).join(" · ")}</p>
            ) : null}
            <div className="rounded-lg border border-border p-3">
              {t.a ? (
                <>
                  <p className="whitespace-pre-wrap text-sm text-text" dir="auto">{t.a.answer}</p>
                  {t.a.citations?.length ? (
                    <p className="mt-2 text-xs text-text-muted">{c.sources}: {t.a.citations.map((x) => `${x.type}:${x.id}`).join(", ")}</p>
                  ) : null}
                  {t.a.references_missing?.length ? <p className="mt-2 text-xs text-amber-200">{c.missing}</p> : null}
                  {(t.a.proposals || []).map((p, j) => {
                    const key = `${t.id}-${j}`
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
                  <p className="mt-2 text-[11px] text-text-faint">{t.a.assistant || ASSISTANT_NAME} · {c.label}</p>
                </>
              ) : t.failed ? (
                <p role="alert" className="text-sm text-rose-300">{t.failed}</p>
              ) : (
                <p role="status" className="text-sm text-text-muted">{c.analysing}</p>
              )}
            </div>
          </div>
        ))}
      </section>

      {error ? <p role="alert" className="text-sm text-rose-300">{error}</p> : null}

      <div className="relative mx-auto w-full max-w-[820px]">
        {menu ? (
          <div role="listbox" aria-label={c.mention}
            className="absolute bottom-full left-0 z-20 mb-2 max-h-72 w-full overflow-y-auto rounded-2xl border border-white/10 bg-[#1c1c1c] p-1.5 shadow-[0_12px_40px_-12px_rgba(0,0,0,0.7)]">
            {menu.loading && menu.items.length === 0 ? <p className="px-3 py-3 text-xs text-white/50">{c.mentionLoading}</p> : null}
            {!menu.loading && menu.items.length === 0 ? <p className="px-3 py-3 text-xs text-white/50">{c.mentionNone}</p> : null}
            {menu.items.map((item, i) => (
              <div key={`${item.type}:${item.id}`} role="option" aria-selected={i === menu.active}
                onMouseDown={(event) => event.preventDefault()} onClick={() => pick(item)}
                onPointerMove={() => i !== menu.active && setMenu({ ...menu, active: i })}
                className={`flex cursor-pointer items-center gap-2 rounded-[10px] px-2.5 py-2 text-[13px] ${i === menu.active ? "bg-white/[0.07] text-white" : "text-white/70"}`}>
                <span className="shrink-0 rounded bg-white/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-white/60">{c.mentionTypes[item.type] || item.type}</span>
                <span className="min-w-0 flex-1 truncate" dir="auto">{item.label}</span>
                <span className="hidden max-w-[40%] shrink-0 truncate text-[11px] text-white/40 sm:block" dir="auto">{item.hint}</span>
              </div>
            ))}
          </div>
        ) : null}

        {references.length ? (
          <ul className="mb-2 flex flex-wrap gap-1.5" aria-label={c.attached}>
            {references.map((r) => (
              <li key={`${r.type}:${r.id}`} className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/[0.06] py-1 ps-2.5 pe-1.5 text-xs text-white/85">
                <span className="text-white/45">{c.mentionTypes[r.type] || r.type}</span>
                <span dir="auto" className="max-w-[12rem] truncate">{r.label}</span>
                <button type="button" aria-label={`${c.removeReference}: ${r.label}`} className="rounded-full p-0.5 hover:bg-white/10"
                  onClick={() => setReferences((current) => current.filter((x) => !(x.type === r.type && x.id === r.id)))}>
                  <X className="size-3" aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        ) : null}

        <PromptBox
          className="w-full py-2"
          value={value}
          onValueChange={setValue}
          onSubmit={onSubmit}
          status={pending ? "streaming" : "idle"}
          onStop={() => abortRef.current?.abort()}
          efforts={efforts}
          placeholder={c.placeholders}
          hint={c.holdHint}
          sendLabel={c.send}
          stopLabel={c.stop}
          inputRef={inputRef}
          inputProps={{
            maxLength: 2000,
            onKeyDown: onInputKeyDown,
            onKeyUp: (event) => { if (event.key !== "Enter" && event.key !== "Escape") updateMenu(event.currentTarget) },
            onClick: (event) => updateMenu(event.currentTarget),
            onChange: (event) => updateMenu(event.currentTarget),
          }}
          actions={(
            <>
              <ModelPicker models={models} value="cyreax-z1" searchable={false} label={c.model} />
              <button type="button" onClick={startMention} aria-label={c.mention} title={c.mention}
                className="grid size-8 place-items-center rounded-full text-white/60 outline-none transition hover:bg-white/[0.07] hover:text-white focus-visible:ring-2 focus-visible:ring-white/25">
                <AtSign className="size-4" aria-hidden="true" />
              </button>
            </>
          )}
        />
      </div>

      <DraftsFolder className="flex justify-end" />

      <details className="rounded-lg border border-border p-4" open={Boolean(params.get("ad"))}>
        <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-text">
          <Sparkles className="h-4 w-4" aria-hidden="true" /> {c.genTitle}
        </summary>
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
      </details>

      {turns.length === 0 && !pending ? (
        <section aria-label={c.shortcutsTitle} className="flex flex-col gap-2">
          <p className="text-xs text-text-muted">{c.shortcutsTitle}</p>
          <div className="flex flex-wrap gap-2">
            {SHORTCUTS.map((shortcut) => (
              <button key={shortcut.id} type="button" onClick={() => runShortcut(shortcut)}
                className="rounded-full border border-border bg-surface-2 px-3 py-1.5 text-xs text-text transition hover:border-white/30">
                {c.shortcuts[shortcut.id].label}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <header>
        <h1 className="text-2xl font-semibold text-text">{c.title}</h1>
        <p className="mt-1 text-sm text-text-muted">{c.intro}</p>
        <button type="button" onClick={() => setShowHistory((v) => !v)} aria-expanded={showHistory}
          className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-3 py-1.5 text-xs text-text hover:border-white/30 max-sm:min-h-10">
          <History className="h-3.5 w-3.5" aria-hidden="true" /> {c.history}
        </button>
        {limits ? (
          <p className="mt-1 text-xs text-text-faint">
            {c.usage(limits.messages_used, limits.messages_per_day)} · {c.genUsage(limits.generations_used, limits.generations_per_day)}
          </p>
        ) : null}
      </header>

      {showHistory ? (
        <ConversationHistory c={c} lang={lang} activeId={conversationId} refreshKey={historyTick} disabled={pending}
          onOpen={(conversation) => { openConversation(conversation); setShowHistory(false) }}
          onNew={() => { newChat(); setShowHistory(false) }} onRemoved={newChat} />
      ) : null}
    </div>
  )
}

export default AgentPage
