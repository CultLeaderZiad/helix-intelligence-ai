import React, { useState, useEffect, useRef } from "react"
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
  X,
  Tag,
  Clock,
  BookOpen,
  Calendar,
  Bold,
  List,
  Heading,
  Link as LinkIcon
} from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Field"
import { cn } from "@/lib/utils"

const CATEGORIES = [
  "General API",
  "AI Engine",
  "Platform",
  "Ad Intelligence",
  "Scrapers",
  "Feature Release"
]

const QUICK_EMOJIS = ["🚀", "⚡", "🔔", "🛠️", "💡", "🛡️", "📊", "🎨", "🎵"]

function formatPublishDate(dateStr) {
  if (!dateStr) return "Recently"
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return String(dateStr)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, "0")
    const day = String(d.getDate()).padStart(2, "0")
    return `${year}-${month}-${day}`
  } catch {
    return String(dateStr)
  }
}

/**
 * Preview renderer for the Kie.ai style update card
 */
function CardPreview({ item }) {
  const publishDate = formatPublishDate(item.starts_at || new Date())
  const category = item.category || "General API"

  return (
    <div className="rounded-xl border border-border/80 bg-surface/90 p-5 shadow-lg space-y-3 text-left">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs font-mono text-text-muted">
          <Clock className="h-3.5 w-3.5 text-text-faint" />
          <span>{publishDate}</span>
        </div>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 font-mono text-[10px] uppercase">
          <Tag className="h-2.5 w-2.5" />
          {category}
        </span>
      </div>

      <h3 className="text-base font-bold text-text">
        {item.title || "Announcement Title"}
      </h3>

      <div className="text-xs text-text-muted leading-relaxed space-y-1 whitespace-pre-line font-sans">
        {item.body || "Announcement description and release notes will be rendered here with formatted bullet points and links..."}
      </div>

      {item.link_url && (
        <div className="pt-2 border-t border-border/50">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-surface-elevated border border-border text-[11px] font-mono text-accent">
            <BookOpen className="h-3 w-3" />
            <span>Documentation Reference: {item.link_url}</span>
            <ExternalLink className="h-2.5 w-2.5 ml-1 text-text-faint" />
          </span>
        </div>
      )}
    </div>
  )
}

export function UpdatesPage() {
  const [updates, setUpdates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [activeTab, setActiveTab] = useState("editor") // "editor" | "preview"
  const bodyTextareaRef = useRef(null)

  // Form State
  const [formData, setFormData] = useState({
    title: "",
    body: "",
    level: "info",
    category: "General API",
    is_published: true,
    show_as_banner: false,
    banner_dismissible: true,
    show_on_public: true,
    link_url: "",
    starts_at: new Date().toISOString().split("T")[0]
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
    setActiveTab("editor")
    setFormData({
      title: "",
      body: "",
      level: "info",
      category: "General API",
      is_published: true,
      show_as_banner: false,
      banner_dismissible: true,
      show_on_public: true,
      link_url: "",
      starts_at: new Date().toISOString().split("T")[0]
    })
    setModalOpen(true)
  }

  const openEditModal = (item) => {
    setEditingId(item.id)
    setActiveTab("editor")
    let parsedDate = new Date().toISOString().split("T")[0]
    if (item.starts_at) {
      try {
        parsedDate = new Date(item.starts_at).toISOString().split("T")[0]
      } catch {
        // fallback
      }
    } else if (item.created_at) {
      try {
        parsedDate = new Date(item.created_at).toISOString().split("T")[0]
      } catch {
        // fallback
      }
    }

    setFormData({
      title: item.title || "",
      body: item.body || "",
      level: item.level || "info",
      category: item.category || "General API",
      is_published: Boolean(item.is_published),
      show_as_banner: Boolean(item.show_as_banner),
      banner_dismissible: Boolean(item.banner_dismissible),
      show_on_public: Boolean(item.show_on_public),
      link_url: item.link_url || "",
      starts_at: parsedDate
    })
    setModalOpen(true)
  }

  const insertTextAtCursor = (prefix, suffix = "") => {
    const textarea = bodyTextareaRef.current
    if (!textarea) return

    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const currentVal = formData.body || ""
    const selected = currentVal.substring(start, end)
    const replacement = `${prefix}${selected}${suffix}`

    const updated = currentVal.substring(0, start) + replacement + currentVal.substring(end)
    setFormData({ ...formData, body: updated })

    setTimeout(() => {
      textarea.focus()
      textarea.setSelectionRange(start + prefix.length, start + prefix.length + selected.length)
    }, 0)
  }

  const handleAddEmoji = (emoji) => {
    setFormData((prev) => ({
      ...prev,
      title: prev.title ? `${emoji} ${prev.title}` : `${emoji} `
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.title.trim()) return

    setSubmitting(true)
    try {
      const payload = {
        ...formData,
        starts_at: formData.starts_at ? new Date(formData.starts_at).toISOString() : new Date().toISOString()
      }

      if (editingId) {
        await updatesService.updateAdminUpdate(editingId, payload)
      } else {
        await updatesService.createAdminUpdate(payload)
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
    <div className="w-full max-w-7xl mx-auto p-4 md:p-8 space-y-6 font-sans">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-5">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-text flex items-center gap-2">
              <Bell className="h-5 w-5 text-accent" />
              Public Updates & Changelog Manager
            </h1>
            <p className="text-[13px] text-text-muted mt-1">
              Publish feature announcements, changelogs, and banners to the public Updates page and user notification bell.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="/updates"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-surface text-xs font-mono text-text-muted hover:text-text hover:border-border-strong transition-colors"
            >
              <span>View Public Page</span>
              <ExternalLink className="h-3 w-3 text-accent" />
            </a>
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
        <div className="rounded-lg border border-border bg-surface overflow-hidden shadow-sm">
          <div className="border-b border-border px-4 py-3 bg-surface-elevated flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-wider text-text-muted">
              All Announcements ({updates.length})
            </span>
            <span className="font-mono text-[11px] text-text-faint">
              Published posts appear on /updates and the notification bell
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-border bg-surface text-text-muted font-mono uppercase">
                <tr>
                  <th className="px-4 py-3">Announcement</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Tone</th>
                  <th className="px-4 py-3 text-center">Published</th>
                  <th className="px-4 py-3 text-center">Banner Mode</th>
                  <th className="px-4 py-3">Publish Date</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {updates.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-text-muted">
                      {loading ? "Loading updates..." : "No updates found. Click 'New Update' above to create your first announcement."}
                    </td>
                  </tr>
                ) : (
                  updates.map((item) => {
                    const levelMeta = LEVEL_CONFIG[item.level] || LEVEL_CONFIG.info
                    const Icon = levelMeta.icon
                    const publishDate = formatPublishDate(item.starts_at || item.created_at)

                    return (
                      <tr key={item.id} className="hover:bg-surface-elevated/50 transition-colors">
                        <td className="px-4 py-3.5 max-w-sm">
                          <div className="font-medium text-text text-[13px] truncate">
                            {item.title}
                          </div>
                          {item.body && (
                            <div className="text-text-muted truncate text-[11px] mt-0.5 line-clamp-1">
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
                              Docs/Ref: {item.link_url} <ExternalLink className="h-2.5 w-2.5" />
                            </a>
                          )}
                        </td>
                        <td className="px-4 py-3.5 font-mono text-[11px] text-text-muted">
                          <span className="px-2 py-0.5 rounded border border-border bg-surface-elevated text-cyan-400">
                            {item.category || "General API"}
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          <span
                            className={cn(
                              "inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-mono uppercase",
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
                            title={item.is_published ? "Published (click to unpublish)" : "Draft (click to publish)"}
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
                            title={item.show_as_banner ? "Active Banner (click to hide)" : "Banner Off"}
                          >
                            <span
                              className={cn(
                                "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-surface shadow-lg ring-0 transition duration-200 ease-in-out",
                                item.show_as_banner ? "translate-x-4 bg-bg" : "translate-x-0"
                              )}
                            />
                          </button>
                        </td>
                        <td className="px-4 py-3.5 font-mono text-[11px] text-text-muted">
                          {publishDate}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => openEditModal(item)}
                              className="h-7 w-7 text-text-muted hover:text-text"
                              title="Edit update"
                            >
                              <Edit2 className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDelete(item.id)}
                              className="h-7 w-7 text-text-muted hover:text-red-400"
                              title="Delete update"
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

        {/* Modal for Create & Edit with KIE-Style Live Preview */}
        {modalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
            <div className="relative w-full max-w-2xl rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-5 my-8">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div>
                  <h3 className="text-base font-semibold text-text">
                    {editingId ? "Edit Update & Changelog" : "Post Platform Update"}
                  </h3>
                  <p className="text-xs text-text-muted mt-0.5">
                    Configure headline, rich release notes, clickable doc links, and publish date.
                  </p>
                </div>
                <button
                  onClick={() => setModalOpen(false)}
                  className="text-text-muted hover:text-text p-1"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Tab Switcher: Editor vs Live Preview */}
              <div className="flex items-center gap-2 border-b border-border pb-2">
                <button
                  type="button"
                  onClick={() => setActiveTab("editor")}
                  className={cn(
                    "px-3 py-1 text-xs font-mono rounded-lg transition-colors",
                    activeTab === "editor"
                      ? "bg-accent text-bg font-semibold"
                      : "text-text-muted hover:text-text"
                  )}
                >
                  Editor
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("preview")}
                  className={cn(
                    "px-3 py-1 text-xs font-mono rounded-lg transition-colors flex items-center gap-1.5",
                    activeTab === "preview"
                      ? "bg-accent text-bg font-semibold"
                      : "text-text-muted hover:text-text"
                  )}
                >
                  <Eye className="h-3.5 w-3.5" />
                  Kie.ai Card Preview
                </button>
              </div>

              {activeTab === "preview" ? (
                <div className="space-y-4 py-2">
                  <div className="text-xs font-mono uppercase tracking-wider text-text-muted">
                    Public Post Card Appearance:
                  </div>
                  <CardPreview item={formData} />
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* Title with Emoji Helpers */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-xs font-mono uppercase tracking-wider text-text-muted">
                        Post Title *
                      </label>
                      <div className="flex items-center gap-1">
                        <span className="text-[10px] font-mono text-text-faint">Quick Emojis:</span>
                        {QUICK_EMOJIS.map((emoji) => (
                          <button
                            key={emoji}
                            type="button"
                            onClick={() => handleAddEmoji(emoji)}
                            className="text-xs hover:scale-125 transition-transform px-0.5"
                            title={`Add ${emoji}`}
                          >
                            {emoji}
                          </button>
                        ))}
                      </div>
                    </div>
                    <Input
                      required
                      placeholder="e.g. 🚀 AI Image Generation Engine & Multi-Platform Profiles Live"
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    />
                  </div>

                  {/* Category, Tone & Date Row */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">
                        Category Tag
                      </label>
                      <select
                        className="w-full rounded-md border border-border bg-bg px-3 py-2 text-xs text-text focus:outline-none focus:ring-1 focus:ring-accent"
                        value={formData.category}
                        onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                      >
                        {CATEGORIES.map((cat) => (
                          <option key={cat} value={cat}>
                            {cat}
                          </option>
                        ))}
                      </select>
                    </div>

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
                        <option value="success">Success (Lime)</option>
                        <option value="warning">Warning (Amber)</option>
                        <option value="critical">Critical (Red)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">
                        Date of Publish
                      </label>
                      <input
                        type="date"
                        className="w-full rounded-md border border-border bg-bg px-3 py-1.5 text-xs text-text focus:outline-none focus:ring-1 focus:ring-accent font-mono"
                        value={formData.starts_at}
                        onChange={(e) => setFormData({ ...formData, starts_at: e.target.value })}
                      />
                    </div>
                  </div>

                  {/* Documentation / Action URL */}
                  <div>
                    <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-1">
                      Docs or Referral Link (Optional)
                    </label>
                    <Input
                      placeholder="e.g. /docs/api-reference/authentication or https://docs.helix.io"
                      value={formData.link_url}
                      onChange={(e) => setFormData({ ...formData, link_url: e.target.value })}
                    />
                  </div>

                  {/* Body Content with Formatting Toolbar */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="block text-xs font-mono uppercase tracking-wider text-text-muted">
                        Body / Release Notes (Markdown & Clickable Links)
                      </label>
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => insertTextAtCursor("**", "**")}
                          className="px-2 py-0.5 rounded border border-border bg-surface text-[11px] font-mono text-text-muted hover:text-text"
                          title="Bold"
                        >
                          Bold
                        </button>
                        <button
                          type="button"
                          onClick={() => insertTextAtCursor("• ")}
                          className="px-2 py-0.5 rounded border border-border bg-surface text-[11px] font-mono text-text-muted hover:text-text"
                          title="Bullet point"
                        >
                          Bullet
                        </button>
                        <button
                          type="button"
                          onClick={() => insertTextAtCursor("### ")}
                          className="px-2 py-0.5 rounded border border-border bg-surface text-[11px] font-mono text-text-muted hover:text-text"
                          title="Heading"
                        >
                          Heading
                        </button>
                        <button
                          type="button"
                          onClick={() => insertTextAtCursor("[Documentation Link](https://helix.io/docs)")}
                          className="px-2 py-0.5 rounded border border-border bg-surface text-[11px] font-mono text-accent hover:underline"
                          title="Insert Link"
                        >
                          + Link
                        </button>
                      </div>
                    </div>
                    <textarea
                      ref={bodyTextareaRef}
                      rows={6}
                      className="w-full rounded-md border border-border bg-bg px-3 py-2 text-xs text-text focus:outline-none focus:ring-1 focus:ring-accent font-sans leading-relaxed"
                      placeholder={`Hi everyone 👋\n\n🎵 Highlights & Capabilities\n• Feature 1 — Clean commercial image generation with zero watermarks.\n• Feature 2 — Direct profile links for X, Instagram, Kick, Rumble, YouTube, TikTok.\n\n🔗 Documentation & Guides\nCheck our API docs: [Helix Documentation](/docs)`}
                      value={formData.body}
                      onChange={(e) => setFormData({ ...formData, body: e.target.value })}
                    />
                  </div>

                  {/* Visibility Toggles */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 rounded-lg border border-border bg-surface-elevated/40 p-3 text-xs">
                    <label className="flex items-center justify-between cursor-pointer p-1">
                      <span className="font-medium text-text">Publish to /updates</span>
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded accent-accent"
                        checked={formData.is_published}
                        onChange={(e) => setFormData({ ...formData, is_published: e.target.checked })}
                      />
                    </label>

                    <label className="flex items-center justify-between cursor-pointer p-1">
                      <span className="font-medium text-text">Show as Top Banner</span>
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded accent-accent"
                        checked={formData.show_as_banner}
                        onChange={(e) => setFormData({ ...formData, show_as_banner: e.target.checked })}
                      />
                    </label>
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
                      {submitting ? "Saving..." : editingId ? "Save & Re-update" : "Publish Update"}
                    </Button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default UpdatesPage
