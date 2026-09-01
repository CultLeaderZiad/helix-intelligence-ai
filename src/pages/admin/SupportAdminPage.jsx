import React, { useState, useEffect } from "react"
import { MessageSquare, Shield, CheckCircle2, Clock, Bug, Sparkles, Send, Filter, RefreshCw, ChevronRight } from "lucide-react"
import { adminService, supportService } from "../../services"

export function SupportAdminPage() {
  const [tickets, setTickets] = useState([])
  const [selectedTicketId, setSelectedTicketId] = useState(null)
  const [ticketDetails, setTicketDetails] = useState(null)
  const [statusFilter, setStatusFilter] = useState("all")
  const [typeFilter, setTypeFilter] = useState("all")
  const [replyText, setReplyText] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const [isSending, setIsSending] = useState(false)

  const loadTickets = async () => {
    setIsLoading(true)
    try {
      const data = await adminService.listSupportTickets(statusFilter, typeFilter)
      setTickets(Array.isArray(data) ? data : [])
      if (data && data.length > 0 && !selectedTicketId) {
        loadDetails(data[0].id)
      }
    } catch (err) {
      console.error("Failed to load admin support tickets:", err)
    } finally {
      setIsLoading(false)
    }
  }

  const loadDetails = async (id) => {
    setSelectedTicketId(id)
    try {
      const details = await supportService.getTicket(id)
      setTicketDetails(details)
    } catch (err) {
      console.error("Failed to load ticket details:", err)
    }
  }

  useEffect(() => {
    loadTickets()
  }, [statusFilter, typeFilter])

  const handleReply = async (e) => {
    e.preventDefault()
    if (!replyText.trim() || !selectedTicketId) return

    setIsSending(true)
    try {
      const newReply = await adminService.replySupportTicket(selectedTicketId, replyText.trim())
      setTicketDetails((prev) => ({
        ...prev,
        status: prev.status === "open" ? "in_progress" : prev.status,
        replies: [...(prev.replies || []), newReply]
      }))
      setReplyText("")
      loadTickets()
    } catch (err) {
      alert(err?.message || "Failed to reply")
    } finally {
      setIsSending(false)
    }
  }

  const handleStatusChange = async (newStatus) => {
    if (!selectedTicketId) return
    try {
      await adminService.updateSupportTicketStatus(selectedTicketId, newStatus)
      setTicketDetails((prev) => ({ ...prev, status: newStatus }))
      loadTickets()
    } catch (err) {
      alert(err?.message || "Failed to update status")
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Admin Ops
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1">Support & Feedback Tickets</h1>
          <p className="text-sm text-slate-400">
            Review user-submitted bug reports, feature requests, and respond to conversation threads.
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-300 text-xs focus:outline-none focus:border-teal-500/50"
          >
            <option value="all">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-300 text-xs focus:outline-none focus:border-teal-500/50"
          >
            <option value="all">All Types</option>
            <option value="bug">Bug Reports</option>
            <option value="feedback">Feedback / Ideas</option>
            <option value="other">Support</option>
          </select>

          <button
            onClick={loadTickets}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Grid: Tickets List + Response Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Col: Tickets */}
        <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-2 py-1">
            Total Tickets ({tickets.length})
          </div>

          {isLoading ? (
            <div className="p-8 text-center text-slate-500 text-sm">Loading tickets...</div>
          ) : tickets.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-sm">No tickets matching filters</div>
          ) : (
            <div className="space-y-2">
              {tickets.map((t) => {
                const isSelected = selectedTicketId === t.id
                return (
                  <button
                    key={t.id}
                    onClick={() => loadDetails(t.id)}
                    className={`w-full p-3.5 rounded-xl border text-left transition-all ${
                      isSelected
                        ? "bg-slate-800/90 border-indigo-500/50 shadow-md ring-1 ring-indigo-500/20"
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
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                        t.status === "resolved"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : t.status === "in_progress"
                          ? "bg-indigo-500/10 text-indigo-400"
                          : "bg-amber-500/10 text-amber-400"
                      }`}>
                        {t.status.replace("_", " ")}
                      </span>
                    </div>

                    <div className="font-semibold text-sm text-slate-200 truncate">{t.subject}</div>
                    <div className="text-xs text-slate-400 truncate mt-0.5">From: {t.user_email}</div>
                    <div className="text-[10px] text-slate-500 mt-2">
                      {new Date(t.created_at).toLocaleDateString()} at {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Right Col: Admin Thread & Action Center */}
        <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden flex flex-col min-h-[550px]">
          {ticketDetails ? (
            <>
              {/* Header with status changer */}
              <div className="p-6 border-b border-slate-800 bg-slate-900/80 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="text-xs text-slate-400">
                    From: <span className="text-teal-400 font-semibold">{ticketDetails.user_email}</span>
                  </div>
                  <h2 className="text-lg font-bold text-white mt-1">{ticketDetails.subject}</h2>
                </div>

                {/* Status Toggle buttons */}
                <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
                  {["open", "in_progress", "resolved"].map((st) => (
                    <button
                      key={st}
                      onClick={() => handleStatusChange(st)}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                        ticketDetails.status === st
                          ? st === "resolved"
                            ? "bg-emerald-500 text-slate-950 shadow"
                            : st === "in_progress"
                            ? "bg-indigo-500 text-white shadow"
                            : "bg-amber-500 text-slate-950 shadow"
                          : "text-slate-400 hover:text-white"
                      }`}
                    >
                      {st.replace("_", " ")}
                    </button>
                  ))}
                </div>
              </div>

              {/* Messages Thread */}
              <div className="flex-1 p-6 space-y-4 overflow-y-auto max-h-[420px]">
                {/* User Original Message */}
                <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-semibold text-teal-400">{ticketDetails.user_email} (Creator)</span>
                    <span>{new Date(ticketDetails.created_at).toLocaleString()}</span>
                  </div>
                  <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {ticketDetails.message}
                  </p>
                  {ticketDetails.context_data && Object.keys(ticketDetails.context_data).length > 0 && (
                    <div className="pt-2 mt-2 border-t border-slate-800/60 text-[10px] text-slate-500">
                      Context: {JSON.stringify(ticketDetails.context_data)}
                    </div>
                  )}
                </div>

                {/* Replies */}
                {ticketDetails.replies && ticketDetails.replies.map((r) => (
                  <div
                    key={r.id}
                    className={`p-4 rounded-xl border space-y-2 ${
                      r.is_admin
                        ? "bg-indigo-950/20 border-indigo-500/30 ml-4"
                        : "bg-slate-800/40 border-slate-800 mr-4"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className={`font-semibold ${r.is_admin ? "text-indigo-400 flex items-center gap-1" : "text-teal-400"}`}>
                        {r.is_admin ? <><Shield className="w-3 h-3" /> Admin Staff ({r.user_email})</> : r.user_email}
                      </span>
                      <span className="text-slate-500">{new Date(r.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                      {r.message}
                    </p>
                  </div>
                ))}
              </div>

              {/* Admin Reply Composer */}
              <form onSubmit={handleReply} className="p-4 border-t border-slate-800 bg-slate-900/90 flex gap-2">
                <input
                  type="text"
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder={`Reply as Helix Admin to ${ticketDetails.user_email}...`}
                  className="flex-1 px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition"
                />
                <button
                  type="submit"
                  disabled={isSending || !replyText.trim()}
                  className="px-5 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 text-white font-semibold text-sm flex items-center gap-2 transition"
                >
                  {isSending ? "..." : <><Send className="w-4 h-4" /> Send Reply</>}
                </button>
              </form>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500 space-y-2">
              <MessageSquare className="w-10 h-10 text-slate-700" />
              <p className="text-sm">Select a ticket from the left to manage</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SupportAdminPage
