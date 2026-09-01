import React, { useState, useEffect } from "react"
import { MessageSquare, Plus, CheckCircle2, Clock, AlertCircle, Send, ChevronRight, User, Shield, Sparkles, Bug } from "lucide-react"
import { supportService } from "../services"
import { useAuth } from "../context/AuthContext"
import { SupportFeedbackModal } from "../components/SupportFeedbackModal"

export function SupportPage() {
  const { user } = useAuth()
  const [tickets, setTickets] = useState([])
  const [selectedTicket, setSelectedTicket] = useState(null)
  const [ticketDetails, setTicketDetails] = useState(null)
  const [replyMessage, setReplyMessage] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const [isSendingReply, setIsSendingReply] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [error, setError] = useState(null)

  const loadTickets = async () => {
    setIsLoading(true)
    try {
      const data = await supportService.listTickets()
      setTickets(Array.isArray(data) ? data : [])
      if (data && data.length > 0 && !selectedTicket) {
        loadTicketDetails(data[0].id)
      }
    } catch (err) {
      setError(err?.message || "Failed to load support tickets")
    } finally {
      setIsLoading(false)
    }
  }

  const loadTicketDetails = async (id) => {
    setSelectedTicket(id)
    try {
      const details = await supportService.getTicket(id)
      setTicketDetails(details)
    } catch (err) {
      console.error("Error loading ticket thread:", err)
    }
  }

  useEffect(() => {
    loadTickets()
  }, [])

  const handleSendReply = async (e) => {
    e.preventDefault()
    if (!replyMessage.trim() || !selectedTicket) return

    setIsSendingReply(true)
    try {
      const newReply = await supportService.replyTicket(selectedTicket, replyMessage.trim())
      setTicketDetails((prev) => ({
        ...prev,
        replies: [...(prev.replies || []), newReply]
      }))
      setReplyMessage("")
    } catch (err) {
      alert(err?.message || "Failed to send reply")
    } finally {
      setIsSendingReply(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Support & Feedback</h1>
          <p className="text-sm text-slate-400 mt-1">
            Submit bug reports, feature suggestions, or chat directly with our product team.
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-sm flex items-center gap-2 transition self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" /> New Ticket
        </button>
      </div>

      {/* Main Grid: Ticket List + Conversation Thread */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Tickets List */}
        <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-2 py-1">
            Your Tickets ({tickets.length})
          </div>

          {isLoading ? (
            <div className="p-8 text-center text-slate-500 text-sm">Loading tickets...</div>
          ) : tickets.length === 0 ? (
            <div className="p-8 text-center space-y-3">
              <MessageSquare className="w-8 h-8 text-slate-600 mx-auto" />
              <div className="text-sm font-semibold text-slate-300">No support tickets yet</div>
              <p className="text-xs text-slate-500">Have an issue or idea? Open a ticket anytime.</p>
              <button
                onClick={() => setIsModalOpen(true)}
                className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition"
              >
                Create First Ticket
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {tickets.map((t) => {
                const isSelected = selectedTicket === t.id
                return (
                  <button
                    key={t.id}
                    onClick={() => loadTicketDetails(t.id)}
                    className={`w-full p-3.5 rounded-xl border text-left transition-all ${
                      isSelected
                        ? "bg-slate-800/90 border-teal-500/50 shadow-md ring-1 ring-teal-500/20"
                        : "bg-slate-900/40 border-slate-800/60 hover:bg-slate-800/50 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                        t.type === "bug"
                          ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                          : "bg-teal-500/10 text-teal-400 border border-teal-500/20"
                      }`}>
                        {t.type === "bug" ? <Bug className="w-2.5 h-2.5" /> : <Sparkles className="w-2.5 h-2.5" />}
                        {t.type}
                      </span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${
                        t.status === "resolved"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : t.status === "in_progress"
                          ? "bg-indigo-500/10 text-indigo-400"
                          : "bg-amber-500/10 text-amber-400"
                      }`}>
                        {t.status === "resolved" ? <CheckCircle2 className="w-2.5 h-2.5" /> : <Clock className="w-2.5 h-2.5" />}
                        {t.status.replace("_", " ")}
                      </span>
                    </div>

                    <div className="font-semibold text-sm text-slate-200 truncate">{t.subject}</div>
                    <div className="text-xs text-slate-400 line-clamp-1 mt-0.5">{t.message}</div>
                    <div className="text-[10px] text-slate-500 mt-2">
                      {new Date(t.created_at).toLocaleDateString()} at {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Right Column: Thread View */}
        <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden flex flex-col min-h-[520px]">
          {ticketDetails ? (
            <>
              {/* Thread Header */}
              <div className="p-6 border-b border-slate-800 bg-slate-900/80">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                        ticketDetails.type === "bug" ? "bg-rose-500/10 text-rose-400" : "bg-teal-500/10 text-teal-400"
                      }`}>
                        {ticketDetails.type}
                      </span>
                      <span className="text-xs text-slate-500">#{ticketDetails.id.slice(0, 8)}</span>
                    </div>
                    <h2 className="text-lg font-bold text-white mt-1">{ticketDetails.subject}</h2>
                  </div>

                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    ticketDetails.status === "resolved"
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                  }`}>
                    {ticketDetails.status.replace("_", " ")}
                  </span>
                </div>
              </div>

              {/* Message History */}
              <div className="flex-1 p-6 space-y-4 overflow-y-auto max-h-[420px]">
                {/* Original Ticket Description */}
                <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5 text-teal-400" /> You (Original Request)
                    </span>
                    <span>{new Date(ticketDetails.created_at).toLocaleString()}</span>
                  </div>
                  <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {ticketDetails.message}
                  </p>
                </div>

                {/* Replies Thread */}
                {ticketDetails.replies && ticketDetails.replies.map((reply) => (
                  <div
                    key={reply.id}
                    className={`p-4 rounded-xl border space-y-2 ${
                      reply.is_admin
                        ? "bg-indigo-950/20 border-indigo-500/30 ml-4 ring-1 ring-indigo-500/10"
                        : "bg-slate-800/40 border-slate-800 mr-4"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className={`font-semibold flex items-center gap-1.5 ${reply.is_admin ? "text-indigo-400" : "text-slate-300"}`}>
                        {reply.is_admin ? (
                          <>
                            <Shield className="w-3.5 h-3.5 text-indigo-400" /> Helix Support Team
                          </>
                        ) : (
                          <>
                            <User className="w-3.5 h-3.5 text-teal-400" /> You
                          </>
                        )}
                      </span>
                      <span className="text-slate-500">{new Date(reply.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                      {reply.message}
                    </p>
                  </div>
                ))}
              </div>

              {/* Reply Composer */}
              <form onSubmit={handleSendReply} className="p-4 border-t border-slate-800 bg-slate-900/90 flex gap-2">
                <input
                  type="text"
                  value={replyMessage}
                  onChange={(e) => setReplyMessage(e.target.value)}
                  placeholder="Type your reply..."
                  className="flex-1 px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-teal-500/60 transition"
                />
                <button
                  type="submit"
                  disabled={isSendingReply || !replyMessage.trim()}
                  className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-slate-950 font-semibold text-sm flex items-center gap-2 transition"
                >
                  {isSendingReply ? "..." : <><Send className="w-4 h-4" /> Send</>}
                </button>
              </form>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500 space-y-2">
              <MessageSquare className="w-10 h-10 text-slate-700" />
              <p className="text-sm">Select a ticket from the left to view the thread</p>
            </div>
          )}
        </div>
      </div>

      <SupportFeedbackModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          loadTickets()
        }}
        initialContext={{ page: "Support Dashboard", tag: "general" }}
      />
    </div>
  )
}

export default SupportPage
