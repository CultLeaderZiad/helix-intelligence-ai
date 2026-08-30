import React, { useState, useEffect } from "react"
import { updatesService } from "@/services"
import {
  Bell,
  Plus,
  Trash2,
  Edit2,
  CheckCircle2,
  AlertTriangle,
  Info,
  AlertOctagon,
  Eye,
  RefreshCw,
  ExternalLink,
  X
} from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Field"
import { cn } from "@/lib/utils"

export function UpdatesPage() {
  const [updates, setUpdates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  // Form State
  const [formData, setFormData] = useState({
    title: "",
    body: "",
    level: "info",
    is_published: false,
    show_as_banner: false,
    banner_dismissible: true,
    show_on_public: true,
    link_url: "",
  })

  const fetchUpdates = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await updatesService.getAdminUpdates()
      setUpdates(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message || "Failed to load updates")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUpdates()
  }, [])

  const openCreateModal = () => {
    setEditingId(null)
    setFormData({
      title: "",
      body: "",
      level: "info",
      is_published: true,
      show_as_banner: true,
      banner_dismissible: true,
      show_on_public: true,
      link_url: "",
    })
    setModalOpen(true)
  }

  const openEditModal = (item) => {
    setEditingId(item.id)
    setFormData({
      title: item.title || "",
      body: item.body || "",
      level: item.level || "info",
      is_published: Boolean(item.is_published),
      show_as_banner: Boolean(item.show_as_banner),
      banner_dismissible: Boolean(item.banner_dismissible),
      show_on_public: Boolean(item.show_on_public),
      link_url: item.link_url || "",
    })
    setModalOpen(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.title.trim()) return

    setSubmitting(true)
    try {
      if (editingId) {
        await updatesService.updateAdminUpdate(editingId, formData)
      } else {
        await updatesService.createAdminUpdate(formData)
      }
      setModalOpen(false)
      fetchUpdates()
    } catch (err) {
      alert(err.message || "Failed to save update")
    } finally {
      setSubmitting(false)
    }
  }

  const handleToggle = async (item, field) => {
    try {
      const updated = { [field]: !item[field] }
      await updatesService.updateAdminUpdate(item.id, updated)
      setUpdates((prev) =>
        prev.map((u) => (u.id === item.id ? { ...u, [field]: !u[field] } : u))
      )
    } catch (err) {
      alert(`Failed to update ${field}: ${err.message}`)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this update?")) return
    try {
      await updatesService.deleteAdminUpdate(id)
      setUpdates((prev) => prev.filter((u) => u.id !== id))
    } catch (err) {
      alert(`Failed to delete update: ${err.message}`)
    }
  }

  const LEVEL_CONFIG = {
    info: { icon: Info, color: "text-blue-400 border-blue-500/30 bg-blue-500/10" },
    warning: { icon: AlertTriangle, color: "text-amber-400 border-amber-500/30 bg-amber-500/10" },
    success: { icon: CheckCircle2, color: "text-accent border-accent/30 bg-accent/10" },
    critical: { icon: AlertOctagon, color: "text-red-400 border-red-500/30 bg-red-500/10" },
  }

  return (
    <div className="flex-1 overflow-y-auto bg-bg p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-5">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-text flex items-center gap-2">
              <Bell className="h-5 w-5 text-accent" />
              Public Updates & Banners
            </h1>
            <p className="text-[13px] text-text-muted mt-1">
              Broadcast system notices, maintenance windows, and feature releases across the app.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchUpdates}
              disabled={loading}
              className="gap-1.5"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={openCreateModal}
              className="gap-1.5 bg-accent text-bg hover:bg-accent/90"
            >
              <Plus className="h-4 w-4" />
              New Update
            </Button>
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-[13px] text-red-400">
            {error}
          </div>
        )}

        {/* Updates Table */}
        <div className="rounded-lg border border-border bg-surface overflow-hidden">
          <div className="border-b border-border px-4 py-3 bg-surface-elevated flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-wider text-text-muted">
              All Announcements ({updates.length})
            </span>
            <span className="font-mono text-[11px] text-text-faint">
              Rule: Highest priority = Most recent published with Banner ON
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-border bg-surface text-text-muted font-mono uppercase">
                <tr>
                  <th className="px-4 py-3">Notice</th>
                  <th className="px-4 py-3">Level</th>
                  <th className="px-4 py-3 text-center">Published</th>
                  <th className="px-4 py-3 text-center">Banner Mode</th>
                  <th className="px-4 py-3 text-center">Dismissible</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {updates.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-text-muted">
                      {loading ? "Loading updates..." : "No updates found. Create your first announcement above."}
                    </td>
                  </tr>
                ) : (
                  updates.map((item) => {
                    const levelMeta = LEVEL_CONFIG[item.level] || LEVEL_CONFIG.info
                    const Icon = levelMeta.icon

                    return (
                      <tr key={item.id} className="hover:bg-surface-elevated/50 transition-colors">
                        <td className="px-4 py-3.5 max-w-xs">
                          <div className="font-medium text-text text-[13px] truncate">
                            {item.title}
                          </div>
                          {item.body && (
                            <div className="text-text-muted truncate text-[11px] mt-0.5">
                              {item.body}
                            </div>
                          )}
                          {item.link_url && (
                            <a
                              href={item.link_url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-[10px] font-mono text-accent hover:underline mt-1"
                            >
                              Link <ExternalLink className="h-2.5 w-2.5" />
                            </a>
                          )}
                        </td>
                        <td className="px-4 py-3.5">
                          <span
                            className={cn(
                              "inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] font-mono uppercase",
                              levelMeta.color
                            )}
                          >
                            <Icon className="h-3 w-3" />
                            {item.level}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-center">
                          <button
                            type="button"
                            onClick={() => handleToggle(item, "is_published")}
                            className={cn(
                              "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out",
                              item.is_published ? "bg-accent" : "bg-border-strong"
                            )}
                          >
                            <span
                              className={cn(
                                "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-surface shadow-lg ring-0 transition duration-200 ease-in-out",
                                item.is_published ? "translate-x-4 bg-bg" : "translate-x-0"
                              )}
                            />
                          </button>
                        </td>
                        <td className="px-4 py-3.5 text-center">
                          <button
                            type="button"
                            onClick={() => handleToggle(item, "show_as_banner")}
                            className={cn(
                              "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out",
                              item.show_as_banner ? "bg-accent" : "bg-border-strong"
                            )}
                          >
                            <span
                              className={cn(
                                "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-surface shadow-lg ring-0 transition duration-200 ease-in-out",
                                item.show_as_banner ? "translate-x-4 bg-bg" : "translate-x-0"
                              )}
                            />
                          </button>
                        </td>
                        <td className="px-4 py-3.5 text-center">
                          <span className="font-mono text-[11px] text-text-muted">
                            {item.banner_dismissible ? "Yes" : "Sticky"}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 font-mono text-[11px] text-text-faint">
                          {new Date(item.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => openEditModal(item)}
                              className="h-7 w-7 text-text-muted hover:text-text"
                            >
                              <Edit2 className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDelete(item.id)}
                              className="h-7 w-7 text-text-muted hover:text-red-400"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal / Drawer for Create & Edit */}
        {modalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="relative w-full max-w-lg rounded-xl border border-border bg-surface p-6 shadow-2xl space-y-5">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <h3 className="text-base font-semibold text-text">
                  {editingId ? "Edit Announcement" : "Create Announcement / Banner"}
                </h3>
                <button
                  onClick={() => setModalOpen(false)}
                  className="text-text-muted hover:text-text"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">
                    Title *
                  </label>
                  <Input
                    required
                    placeholder="e.g. Higgsfield Video Ad Engine Live"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">
                    Body (Optional)
                  </label>
                  <textarea
                    rows={2}
                    className="w-full rounded-md border border-border bg-bg px-3 py-2 text-xs text-text focus:outline-none focus:ring-1 focus:ring-accent"
                    placeholder="Brief description or change details..."
                    value={formData.body}
                    onChange={(e) => setFormData({ ...formData, body: e.target.value })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">
                      Tone / Level
                    </label>
                    <select
                      className="w-full rounded-md border border-border bg-bg px-3 py-2 text-xs text-text focus:outline-none focus:ring-1 focus:ring-accent"
                      value={formData.level}
                      onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                    >
                      <option value="info">Info (Neutral)</option>
                      <option value="warning">Warning (Amber)</option>
                      <option value="success">Success (Lime)</option>
                      <option value="critical">Critical (Red)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">
                      Action URL (Optional)
                    </label>
                    <Input
                      placeholder="https://... or /updates"
                      value={formData.link_url}
                      onChange={(e) => setFormData({ ...formData, link_url: e.target.value })}
                    />
                  </div>
                </div>

                <div className="space-y-2 rounded-lg border border-border bg-surface-elevated/40 p-3 text-xs">
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="font-medium text-text">Publish Announcement</span>
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded accent-accent"
                      checked={formData.is_published}
                      onChange={(e) => setFormData({ ...formData, is_published: e.target.checked })}
                    />
                  </label>

                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="font-medium text-text">Display as Public Banner</span>
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded accent-accent"
                      checked={formData.show_as_banner}
                      onChange={(e) => setFormData({ ...formData, show_as_banner: e.target.checked })}
                    />
                  </label>

                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="font-medium text-text">Allow User to Dismiss</span>
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded accent-accent"
                      checked={formData.banner_dismissible}
                      onChange={(e) => setFormData({ ...formData, banner_dismissible: e.target.checked })}
                    />
                  </label>
                </div>

                {/* Live Preview */}
                <div>
                  <label className="block text-[11px] font-mono uppercase tracking-wider text-text-faint mb-1.5">
                    Live Banner Preview
                  </label>
                  <div className="rounded-lg border border-border bg-bg p-3">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-mono text-[9px] uppercase px-1.5 py-0.5 rounded border border-border bg-surface text-text-muted">
                        {formData.level}
                      </span>
                      <span className="font-semibold text-text">
                        {formData.title || "Announcement Title"}
                      </span>
                      {formData.body && (
                        <span className="text-text-muted text-[11px]">
                          — {formData.body}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setModalOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    size="sm"
                    disabled={submitting}
                    className="bg-accent text-bg hover:bg-accent/90"
                  >
                    {submitting ? "Saving..." : editingId ? "Update" : "Create"}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default UpdatesPage
