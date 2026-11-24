import { useCallback, useEffect, useState } from "react"
import { Bell, Copy, Send, Trash2, Webhook } from "lucide-react"
import { accountService } from "@/services"
import { useLanguage } from "@/context/LanguageContext"

export const ALERT_COPY = {
  en: {
    title: "Alerts",
    body: "Send monitor and account notifications to Telegram or to your own webhook. Every in-app notification is copied to your active channels.",
    usage: (sent, cap) => `${sent} of ${cap} alerts sent today`,
    addWebhook: "Add webhook",
    webhookPlaceholder: "https://your-server.example.com/helix",
    linkTelegram: "Link Telegram",
    telegramOff: "Telegram alerts are not set up on this server yet.",
    openTelegram: "Open Telegram and press Start",
    secretOnce: "Signing secret (shown once). Verify X-Helix-Signature with it:",
    copy: "Copy",
    on: "On",
    off: "Off",
    remove: "Remove",
    empty: "No alert channels yet.",
    failed: "Could not load alert channels.",
    statuses: { active: "Active", pending: "Waiting for /start", disabled: "Turned off after failures" },
  },
  ar: {
    title: "التنبيهات",
    body: "أرسل إشعارات المراقبة والحساب إلى تيليجرام أو إلى رابط webhook خاص بك. كل إشعار داخل التطبيق يُنسخ إلى قنواتك المفعّلة.",
    usage: (sent, cap) => `أُرسل ${sent} من ${cap} تنبيه اليوم`,
    addWebhook: "إضافة webhook",
    webhookPlaceholder: "https://your-server.example.com/helix",
    linkTelegram: "ربط تيليجرام",
    telegramOff: "تنبيهات تيليجرام غير مفعّلة على هذا الخادم بعد.",
    openTelegram: "افتح تيليجرام واضغط Start",
    secretOnce: "مفتاح التوقيع (يظهر مرة واحدة). تحقق به من X-Helix-Signature:",
    copy: "نسخ",
    on: "مفعّل",
    off: "متوقف",
    remove: "حذف",
    empty: "لا توجد قنوات تنبيه بعد.",
    failed: "تعذّر تحميل قنوات التنبيه.",
    statuses: { active: "مفعّل", pending: "بانتظار /start", disabled: "أُوقف بعد أخطاء متكررة" },
  },
}

export function AlertChannelsSection() {
  const { lang } = useLanguage()
  const c = lang === "ar" ? ALERT_COPY.ar : ALERT_COPY.en
  const [state, setState] = useState(null)
  const [error, setError] = useState("")
  const [url, setUrl] = useState("")
  const [secret, setSecret] = useState("")
  const [telegramLink, setTelegramLink] = useState("")
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setState(await accountService.listAlertChannels())
      setError("")
    } catch {
      setError(c.failed)
    }
  }, [c.failed])

  useEffect(() => { load() }, [load])

  async function run(action) {
    setBusy(true)
    setError("")
    try {
      await action()
      await load()
    } catch (err) {
      setError(err?.detail?.message || err?.message || c.failed)
    } finally {
      setBusy(false)
    }
  }

  const items = state?.items || []
  const limits = state?.limits
  const isOn = (ch) => ch.enabled && ch.status === "active"

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5" aria-labelledby="alerts-title">
      <div className="flex items-start gap-3">
        <Bell className="mt-0.5 h-5 w-5 text-teal-400" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <h2 id="alerts-title" className="font-semibold text-white">{c.title}</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">{c.body}</p>
          {limits ? <p className="mt-1 text-xs text-slate-500">{c.usage(state.sent_today, limits.per_day)}</p> : null}
        </div>
      </div>

      {error ? <p role="alert" className="mt-3 text-sm text-rose-300">{error}</p> : null}

      <ul className="mt-4 flex flex-col gap-2">
        {state && items.length === 0 ? <li className="text-sm text-slate-500">{c.empty}</li> : null}
        {items.map((ch) => (
          <li key={ch.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-sm text-slate-100" dir="auto">{ch.label}</p>
              <p className="text-xs text-slate-500">
                {c.statuses[ch.status] || ch.status}
                {ch.last_error ? ` · ${ch.last_error}` : ""}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {ch.status !== "pending" ? (
                <button type="button" disabled={busy} onClick={() => run(() => accountService.setAlertChannelEnabled(ch.id, !isOn(ch)))}
                  className="rounded-md border border-slate-700 px-2.5 py-1 text-xs text-slate-200 hover:border-teal-500">
                  {isOn(ch) ? c.on : c.off}
                </button>
              ) : null}
              <button type="button" disabled={busy} aria-label={c.remove} onClick={() => run(() => accountService.removeAlertChannel(ch.id))}
                className="rounded-md border border-slate-700 p-1.5 text-slate-300 hover:border-rose-500 hover:text-rose-300">
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          </li>
        ))}
      </ul>

      <form
        className="mt-4 flex flex-col gap-2 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault()
          run(async () => {
            const out = await accountService.addAlertWebhook(url.trim())
            setSecret(out.signing_secret)
            setUrl("")
          })
        }}
      >
        <input type="url" required value={url} onChange={(e) => setUrl(e.target.value)} placeholder={c.webhookPlaceholder} dir="ltr"
          className="min-h-10 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100" />
        <button type="submit" disabled={busy} className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-slate-700 px-4 text-sm font-semibold text-slate-100 hover:border-teal-500">
          <Webhook className="h-4 w-4" aria-hidden="true" /> {c.addWebhook}
        </button>
      </form>

      {secret ? (
        <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
          <p>{c.secretOnce}</p>
          <div className="mt-1 flex items-center gap-2">
            <code className="break-all" dir="ltr">{secret}</code>
            <button type="button" onClick={() => navigator.clipboard?.writeText(secret)} className="inline-flex items-center gap-1 underline">
              <Copy className="h-3 w-3" aria-hidden="true" /> {c.copy}
            </button>
          </div>
        </div>
      ) : null}

      <div className="mt-4">
        {state && !state.telegram_available ? (
          <p className="text-sm text-slate-500">{c.telegramOff}</p>
        ) : (
          <button
            type="button"
            disabled={busy || !state}
            onClick={() => run(async () => {
              const out = await accountService.linkTelegram()
              setTelegramLink(out.link)
            })}
            className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-slate-700 px-4 text-sm font-semibold text-slate-100 hover:border-teal-500"
          >
            <Send className="h-4 w-4" aria-hidden="true" /> {c.linkTelegram}
          </button>
        )}
        {telegramLink ? (
          <a href={telegramLink} target="_blank" rel="noreferrer" className="ms-3 text-sm text-teal-300 underline">{c.openTelegram}</a>
        ) : null}
      </div>
    </section>
  )
}

export default AlertChannelsSection
