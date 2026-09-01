import React, { useState, useEffect } from "react"
import { MessageSquarePlus, Bug, Sparkles, Send, X, CheckCircle2, AlertCircle } from "lucide-react"
import { supportService } from "../services"

export function SupportFeedbackModal({ isOpen, onClose, initialContext = {} }) {
  const [ticketType, setTicketType] = useState("feedback") // 'feedback' | 'bug' | 'other'
  const [subject, setSubject] = useState("")
  const [message, setMessage] = useState("")
  const [tag, setTag] = useState(initialContext.tag || "general")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submittedTicket, setSubmittedTicket] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (isOpen) {
      setSubmittedTicket(null)
      setError(null)
      setSubject("")
      setMessage("")
      if (initialContext.tag) setTag(initialContext.tag)
      if (initialContext.isBug) setTicketType("bug")
    }
  }, [isOpen, initialContext])

  if (!isOpen) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!subject.trim() || !message.trim()) return

    setIsSubmitting(true)
    setError(null)

    try {
      const res = await supportService.createTicket({
        type: ticketType,
        subject: subject.trim(),
        message: message.trim(),
        tag: tag || initialContext.tag || "general",
        context_data: {
          ...initialContext,
          url: window.location.pathname,
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString()
        }
      })
      setSubmittedTicket(res)
    } catch (err) {
      setError(err?.message || "Failed to submit request. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl ${ticketType === "bug" ? "bg-rose-500/10 text-rose-400" : "bg-teal-500/10 text-teal-400"}`}>
              {ticketType === "bug" ? <Bug className="w-5 h-5" /> : <MessageSquarePlus className="w-5 h-5" />}
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">
                {ticketType === "bug" ? "Report an Issue" : "Submit Feedback or Request"}
              </h2>
              <p className="text-xs text-slate-400">
                {initialContext.page ? `Context: ${initialContext.page} screen` : "We read every ticket and reply directly."}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {submittedTicket ? (
          <div className="p-8 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-teal-500/20 text-teal-400 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-white">Ticket Submitted!</h3>
            <p className="text-sm text-slate-300">
              Your ticket <span className="text-teal-400 font-semibold">#{submittedTicket.id.slice(0, 8)}</span> has been received. Our team has been notified and you will receive in-app notifications as soon as we reply.
            </p>
            <div className="pt-4">
              <button
                onClick={onClose}
                className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-sm transition"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            {/* Type selector */}
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: "feedback", label: "Suggestion", icon: Sparkles },
                { id: "bug", label: "Bug Report", icon: Bug },
                { id: "other", label: "Support", icon: MessageSquarePlus }
              ].map((t) => {
                const Icon = t.icon
                const isSelected = ticketType === t.id
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setTicketType(t.id)}
                    className={`p-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                      isSelected
                        ? "bg-slate-800 border-teal-500 text-teal-400 ring-1 ring-teal-500/30"
                        : "bg-slate-900 border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800/60"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {t.label}
                  </button>
                )
              })}
            </div>

            {/* Subject */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Subject</label>
              <input
                type="text"
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder={ticketType === "bug" ? "e.g. Scraper returned zero results on brand X" : "e.g. Can we add CSV export?"}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-teal-500/60 transition"
              />
            </div>

            {/* Message */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Description & Details</label>
              <textarea
                required
                rows={4}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Please describe what happened or what improvement you'd like to see..."
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-teal-500/60 transition resize-none"
              />
            </div>

            {/* Feature Tag */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Related Feature</label>
              <select
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-300 text-xs focus:outline-none focus:border-teal-500/60"
              >
                <option value="discover">Discover / Scraper</option>
                <option value="intelligence">Intelligence & Teardowns</option>
                <option value="create">Create Studio & Higgsfield</option>
                <option value="performance">Performance & Scoring</option>
                <option value="billing">Billing & Credits</option>
                <option value="general">General / Other</option>
              </select>
            </div>

            {/* Footer */}
            <div className="flex justify-end items-center gap-3 pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !subject.trim() || !message.trim()}
                className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-slate-950 font-semibold text-xs flex items-center gap-2 transition"
              >
                {isSubmitting ? "Sending..." : <><Send className="w-3.5 h-3.5" /> Submit Ticket</>}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default SupportFeedbackModal
