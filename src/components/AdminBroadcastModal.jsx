import React, { useState } from "react"
import { Megaphone, Send, X, AlertCircle, CheckCircle2 } from "lucide-react"
import { adminService } from "../services"

export function AdminBroadcastModal({ isOpen, onClose }) {
  const [title, setTitle] = useState("")
  const [message, setMessage] = useState("")
  const [notifType, setNotifType] = useState("system")
  const [link, setLink] = useState("/updates")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  if (!isOpen) return null

  const handleBroadcast = async (e) => {
    e.preventDefault()
    if (!title.trim() || !message.trim()) return

    setIsSubmitting(true)
    setError(null)

    try {
      const res = await adminService.broadcastAnnouncement(
        title.trim(),
        message.trim(),
        notifType,
        link.trim() || null
      )
      setResult(res)
    } catch (err) {
      setError(err?.message || "Failed to send broadcast announcement")
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
            <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400">
              <Megaphone className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Broadcast In-App Announcement</h2>
              <p className="text-xs text-slate-400">Delivers an in-app notification to every active workspace.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {result ? (
          <div className="p-8 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-white">Broadcast Sent!</h3>
            <p className="text-sm text-slate-300">
              Successfully delivered announcement to <span className="text-teal-400 font-semibold">{result.recipients_count} users</span> across all organizations.
            </p>
            <div className="pt-4">
              <button
                onClick={onClose}
                className="px-5 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white font-semibold text-sm transition"
              >
                Close
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleBroadcast} className="p-6 space-y-4">
            {error && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Announcement Title</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. New Model Released: Higgsfield v2.5 Video Generation"
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Announcement Body</label>
              <textarea
                required
                rows={4}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Write the full update or message to your users..."
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Notification Type</label>
                <select
                  value={notifType}
                  onChange={(e) => setNotifType(e.target.value)}
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-300 text-xs focus:outline-none focus:border-indigo-500/60"
                >
                  <option value="system">System / Feature Update</option>
                  <option value="alert">Alert / Maintenance</option>
                  <option value="info">General Info</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Action Link</label>
                <input
                  type="text"
                  value={link}
                  onChange={(e) => setLink(e.target.value)}
                  placeholder="/updates"
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-300 text-xs focus:outline-none focus:border-indigo-500/60"
                />
              </div>
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
                disabled={isSubmitting || !title.trim() || !message.trim()}
                className="px-5 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 text-white font-semibold text-xs flex items-center gap-2 transition"
              >
                {isSubmitting ? "Sending..." : <><Send className="w-3.5 h-3.5" /> Send to All Users</>}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default AdminBroadcastModal
