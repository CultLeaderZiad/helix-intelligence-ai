import React, { useEffect, useRef, useState } from "react"
import { AlertCircle, Bug, CheckCircle2, MessageSquarePlus, Send, Sparkles, X } from "lucide-react"
import { useLanguage } from "@/context/LanguageContext"
import { useDialogFocus } from "@/hooks/useDialogFocus"
import { w5Support } from "@/i18n/w5Support"
import { supportService } from "@/services"

const EMPTY_CONTEXT = Object.freeze({})

/** @typedef {{ id?: string | number }} SupportTicket */

/** @param {{ isOpen: boolean, onClose: () => void, onSuccess?: (ticket: SupportTicket) => void, initialContextRecord?: Record<string, unknown> & { tag?: string, isBug?: boolean, page?: string }, initialContext?: Record<string, unknown> & { tag?: string, isBug?: boolean, page?: string } }} props */
export function SupportFeedbackModal({ isOpen, onClose, onSuccess, initialContextRecord, initialContext = EMPTY_CONTEXT }) {
  const { lang, t } = useLanguage()
  const words = w5Support[lang] || w5Support.en
  const text = (key) => t(key, words[key] || w5Support.en[key] || key)
  const context = initialContextRecord ?? initialContext
  const [ticketType, setTicketType] = useState("feedback")
  const [subject, setSubject] = useState("")
  const [message, setMessage] = useState("")
  const [tag, setTag] = useState("general")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submittedTicket, setSubmittedTicket] = useState(null)
  const [error, setError] = useState(null)
  const dialogRef = useRef(null)

  useDialogFocus(dialogRef, isOpen, () => {
    if (!isSubmitting) onClose()
  })

  useEffect(() => {
    if (!isOpen) return
    setSubmittedTicket(null)
    setError(null)
    setSubject("")
    setMessage("")
    setTicketType(context.isBug ? "bug" : "feedback")
    setTag(context.tag || "general")
  }, [isOpen, context.isBug, context.tag])

  if (!isOpen) return null

  const handleClose = () => {
    if (!isSubmitting) onClose()
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (isSubmitting) return
    if (!subject.trim()) {
      setError(text("missingSubject"))
      return
    }
    if (!message.trim()) {
      setError(text("missingDetails"))
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      const ticket = await supportService.createTicket({
        type: ticketType,
        subject: subject.trim(),
        message: message.trim(),
        tag: tag || context.tag || "general",
        context_data: {
          ...context,
          url: window.location.pathname,
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString(),
        },
      })
      setSubmittedTicket(ticket || {})
      try {
        onSuccess?.(ticket)
      } catch (callbackError) {
        console.error("Support submission callback failed", callbackError)
      }
    } catch (submitError) {
      const detail = submitError?.response?.data?.detail || submitError?.message
      setError(typeof detail === "string" ? detail : text("submitFailed"))
    } finally {
      setIsSubmitting(false)
    }
  }

  const contextPage = typeof context.page === "string" ? context.page : ""
  const ticketId = submittedTicket?.id

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200" dir={lang === "ar" ? "rtl" : "ltr"}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="support-modal-title"
        className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl"
      >
        <div className="flex items-center justify-between gap-4 p-6 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl ${ticketType === "bug" ? "bg-rose-500/10 text-rose-400" : "bg-teal-500/10 text-teal-400"}`}>
              {ticketType === "bug" ? <Bug className="w-5 h-5" aria-hidden="true" /> : <MessageSquarePlus className="w-5 h-5" aria-hidden="true" />}
            </div>
            <div>
              <h2 id="support-modal-title" className="text-lg font-bold text-white">
                {ticketType === "bug" ? text("modalBugTitle") : text("modalTitle")}
              </h2>
              <p className="text-xs text-slate-400">
                {contextPage ? text("contextLabel").replace("{page}", contextPage) : text("modalIntro")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            disabled={isSubmitting}
            aria-label={text("close")}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition disabled:opacity-50"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {submittedTicket ? (
          <div className="p-8 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-teal-500/20 text-teal-400 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" aria-hidden="true" />
            </div>
            <h3 className="text-xl font-bold text-white">{text("ticketSubmitted")}</h3>
            <p className="text-sm text-slate-300">
              {text("ticketReceived")}{ticketId ? <> <span className="text-teal-400 font-semibold">#{String(ticketId).slice(0, 8)}</span></> : null}
            </p>
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-sm transition disabled:opacity-50"
            >
              {text("done")}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div role="alert" className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
                {error}
              </div>
            )}

            <div className="grid grid-cols-3 gap-2">
              {[
                { id: "feedback", label: "ticketTypeFeedback", icon: Sparkles },
                { id: "bug", label: "ticketTypeBug", icon: Bug },
                { id: "other", label: "ticketTypeOther", icon: MessageSquarePlus },
              ].map((item) => {
                const Icon = item.icon
                const selected = ticketType === item.id
                return (
                  <button
                    key={item.id}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => setTicketType(item.id)}
                    className={`p-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition ${selected ? "bg-slate-800 border-teal-500 text-teal-400 ring-1 ring-teal-500/30" : "bg-slate-900 border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800/60"}`}
                  >
                    <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                    {text(item.label)}
                  </button>
                )
              })}
            </div>

            <div>
              <label htmlFor="support-subject" className="block text-xs font-medium text-slate-300 mb-1.5">{text("subject")}</label>
              <input
                id="support-subject"
                type="text"
                required
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                placeholder={ticketType === "bug" ? text("bugSubjectPlaceholder") : text("subjectPlaceholder")}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-teal-500/60 transition"
              />
            </div>

            <div>
              <label htmlFor="support-details" className="block text-xs font-medium text-slate-300 mb-1.5">{text("details")}</label>
              <textarea
                id="support-details"
                required
                rows={4}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder={text("detailsPlaceholder")}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-teal-500/60 transition resize-none"
              />
            </div>

            <div>
              <label htmlFor="support-feature" className="block text-xs font-medium text-slate-400 mb-1.5">{text("relatedFeature")}</label>
              <select
                id="support-feature"
                value={tag}
                onChange={(event) => setTag(event.target.value)}
                className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-300 text-xs focus:outline-none focus:border-teal-500/60"
              >
                <option value="discover">{text("featureDiscover")}</option>
                <option value="intelligence">{text("featureIntelligence")}</option>
                <option value="create">{text("featureCreate")}</option>
                <option value="performance">{text("featurePerformance")}</option>
                <option value="billing">{text("featureBilling")}</option>
                <option value="general">{text("featureGeneral")}</option>
              </select>
            </div>

            <div className="flex justify-end items-center gap-3 pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={handleClose}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition disabled:opacity-50"
              >
                {text("cancel")}
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !subject.trim() || !message.trim()}
                className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-slate-950 font-semibold text-xs flex items-center gap-2 transition"
              >
                {isSubmitting ? text("submitting") : <><Send className="w-3.5 h-3.5" aria-hidden="true" /> {text("submitTicket")}</>}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
