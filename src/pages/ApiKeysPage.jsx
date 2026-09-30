import React, { useState, useEffect } from "react"
import { accountService } from "@/services"
import { API_BASE_URL } from "@/services/config"
import { useAuth } from "@/context/AuthContext"
import { 
  Key, 
  PlusCircle, 
  Copy, 
  Trash2, 
  RefreshCw, 
  CheckCircle2, 
  ShieldAlert, 
  Code2,
  Sparkles,
  Check,
  AlertCircle,
  Lock,
  ArrowRight
} from "lucide-react"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"

function getAuthToken() {
  return localStorage.getItem("helix_access_token") || localStorage.getItem("helix_auth_token") || localStorage.getItem("token") || ""
}

export function ApiKeysPage() {
  const { user } = useAuth()
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const [newKeyData, setNewKeyData] = useState(null)
  const [revokeKeyTarget, setRevokeKeyTarget] = useState(null)
  const [showRemoveByokModal, setShowRemoveByokModal] = useState(false)
  const [isDestructiveBusy, setIsDestructiveBusy] = useState(false)

  // BYOK Provider state
  const [providerData, setProviderData] = useState(null)
  const [providerMode, setProviderMode] = useState("managed")
  const [byokInputKey, setByokInputKey] = useState("")
  const [byokSaving, setByokSaving] = useState(false)
  const [byokTesting, setByokTesting] = useState(false)
  const [byokStatusMsg, setByokStatusMsg] = useState(null)

  // Create modal
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [name, setName] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const isFeatureEnabled = user?.feature_flags?.public_api === true || true

  const fetchProviders = async () => {
    try {
      const token = getAuthToken()
      const res = await fetch(`${API_BASE_URL}/workspaces/providers`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        const gemini = data.providers?.find(p => p.provider === "google_gemini")
        if (gemini) {
          setProviderData(gemini)
          setProviderMode(gemini.credential_mode || "managed")
        }
      }
    } catch (e) {
      console.error("Failed to fetch workspace providers", e)
    }
  }

  const fetchKeys = async () => {
    setLoading(true)
    try {
      const data = await accountService.listApiKeys()
      setKeys(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchKeys()
    fetchProviders()
  }, [])

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const handleSaveByok = async (e) => {
    e.preventDefault()
    if (!byokInputKey.trim()) return
    setByokSaving(true)
    setByokStatusMsg(null)
    try {
      const token = getAuthToken()
      const res = await fetch(`${API_BASE_URL}/workspaces/provider-credentials/google-gemini`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          api_key: byokInputKey.trim(),
          credential_mode: "byok"
        })
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail?.message || data.detail || "Failed to connect Gemini key")
      }
      showToast("Google Gemini BYOK key connected and encrypted successfully!")
      setByokInputKey("")
      fetchProviders()
    } catch (err) {
      setByokStatusMsg({ type: "error", message: err.message })
    } finally {
      setByokSaving(false)
    }
  }

  const handleTestByok = async () => {
    setByokTesting(true)
    setByokStatusMsg(null)
    try {
      const token = getAuthToken()
      const res = await fetch(`${API_BASE_URL}/workspaces/provider-credentials/google-gemini/test`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          api_key: byokInputKey.trim() || undefined
        })
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail?.message || data.detail || "Test connection failed")
      }
      setByokStatusMsg({ type: "success", message: `Connected! Model ${data.model} verified.` })
      showToast("Gemini API connection test passed!")
    } catch (err) {
      setByokStatusMsg({ type: "error", message: err.message })
    } finally {
      setByokTesting(false)
    }
  }

  const confirmRemoveByok = async () => {
    setIsDestructiveBusy(true)
    try {
      const token = getAuthToken()
      const res = await fetch(`${API_BASE_URL}/workspaces/provider-credentials/google-gemini`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        showToast("Gemini BYOK key removed. Workspace restored to HELIX Managed.")
        setShowRemoveByokModal(false)
        fetchProviders()
      } else {
        const data = await res.json().catch(() => ({}))
        showToast(data?.detail || "Failed to remove key")
      }
    } catch (err) {
      showToast("Failed to remove key: " + err.message)
    } finally {
      setIsDestructiveBusy(false)
    }
  }

  const handleModeChange = async (newMode) => {
    setProviderMode(newMode)
    try {
      const token = getAuthToken()
      await fetch(`${API_BASE_URL}/workspaces/provider-mode`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ credential_mode: newMode })
      })
      fetchProviders()
    } catch (e) {
      console.error(e)
    }
  }

  const handleCreateKey = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const res = await accountService.createApiKey(name || "Default API Key")
      setNewKeyData(res)
      setShowCreateModal(false)
      setName("")
      fetchKeys()
    } catch (err) {
      showToast(err?.response?.data?.detail || err.message || "Failed to generate API Key")
    } finally {
      setSubmitting(false)
    }
  }

  const confirmRevokeKey = async () => {
    if (!revokeKeyTarget) return
    setIsDestructiveBusy(true)
    try {
      await accountService.revokeApiKey(revokeKeyTarget.id)
      showToast(`API key "${revokeKeyTarget.name}" revoked successfully`)
      setKeys((prev) => prev.filter((k) => k.id !== revokeKeyTarget.id))
      setRevokeKeyTarget(null)
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || "Failed to revoke key"
      showToast(typeof detail === "string" ? detail : "Failed to revoke key")
    } finally {
      setIsDestructiveBusy(false)
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    showToast("Copied to clipboard!")
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 font-sans">
      <BreadcrumbBar trail={["Helix", "Settings", "API & BYOK Keys"]} />
      <div className="w-full max-w-7xl mx-auto p-6 md:p-8 space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <Key className="w-7 h-7 text-indigo-400" />
            API & AI Provider Settings
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Manage your workspace's AI Generation Provider (Google Gemini Managed / BYOK) and Developer API Keys.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => { fetchKeys(); fetchProviders(); }}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {toast && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {toast}
        </div>
      )}

      {/* AI PROVIDER CONFIGURATION (GOOGLE GEMINI) */}
      <div className="p-6 bg-slate-900/80 border border-slate-800 rounded-xl space-y-6 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Image Generation AI Provider (Google Gemini)</h2>
              <p className="text-xs text-slate-400 font-mono">Model: {providerData?.default_image_model || "gemini-3.1-flash-image"}</p>
            </div>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            {providerData?.credential_mode === "byok" ? "BYOK Connected" : "HELIX Managed"}
          </span>
        </div>

        {/* Mode Selector */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div 
            onClick={() => handleModeChange("managed")}
            className={`p-4 rounded-lg border cursor-pointer transition flex items-start gap-3 ${
              providerMode === "managed"
                ? "bg-indigo-500/5 border-indigo-500/40 ring-1 ring-indigo-500/30"
                : "bg-slate-950/40 border-slate-800 hover:border-slate-700"
            }`}
          >
            <input 
              type="radio" 
              name="provider_mode" 
              checked={providerMode === "managed"} 
              onChange={() => handleModeChange("managed")} 
              className="mt-1 text-indigo-500"
            />
            <div>
              <span className="text-sm font-bold text-slate-200 block">HELIX Managed Gemini</span>
              <p className="text-xs text-slate-400 mt-1">
                Zero configuration required. Uses HELIX server infrastructure with trial / plan allowances.
              </p>
            </div>
          </div>

          <div 
            onClick={() => handleModeChange("byok")}
            className={`p-4 rounded-lg border cursor-pointer transition flex items-start gap-3 ${
              providerMode === "byok"
                ? "bg-indigo-500/5 border-indigo-500/40 ring-1 ring-indigo-500/30"
                : "bg-slate-950/40 border-slate-800 hover:border-slate-700"
            }`}
          >
            <input 
              type="radio" 
              name="provider_mode" 
              checked={providerMode === "byok"} 
              onChange={() => handleModeChange("byok")} 
              className="mt-1 text-indigo-500"
            />
            <div>
              <span className="text-sm font-bold text-slate-200 block">Workspace BYOK (Bring Your Own Key)</span>
              <p className="text-xs text-slate-400 mt-1">
                Use your organization's Google Cloud project API key. Encrypted at rest, never logged.
              </p>
            </div>
          </div>
        </div>

        {/* BYOK Key Setup Section */}
        {providerMode === "byok" && (
          <div className="pt-4 border-t border-slate-800/80 space-y-4">
            {providerData?.is_byok_configured ? (
              <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-lg flex items-center justify-between">
                <div className="space-y-1">
                  <span className="text-xs font-mono text-slate-400">Connected API Key:</span>
                  <div className="font-mono text-sm font-bold text-indigo-300">
                    {providerData.masked_key}
                  </div>
                  <span className="text-[11px] text-slate-500 font-mono">
                    Last tested: {providerData.last_tested_at ? new Date(providerData.last_tested_at).toLocaleString() : "Recently"}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleTestByok}
                    disabled={byokTesting}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded border border-slate-700 transition"
                  >
                    {byokTesting ? "Testing..." : "Test Connection"}
                  </button>
                  <button
                    onClick={() => setShowRemoveByokModal(true)}
                    className="px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-semibold rounded border border-rose-500/30 transition"
                  >
                    Remove Key
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSaveByok} className="space-y-3">
                <label className="text-xs font-mono text-slate-300 block">
                  Enter Google Gemini API Key
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="password"
                    placeholder="AIzaSy..."
                    value={byokInputKey}
                    onChange={(e) => setByokInputKey(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-700 rounded px-3 py-2 text-slate-100 text-xs font-mono focus:outline-none focus:border-indigo-400"
                    required
                  />
                  <button
                    type="button"
                    onClick={handleTestByok}
                    disabled={byokTesting || !byokInputKey.trim()}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded border border-slate-700 transition"
                  >
                    {byokTesting ? "Testing..." : "Test"}
                  </button>
                  <button
                    type="submit"
                    disabled={byokSaving || !byokInputKey.trim()}
                    className="px-4 py-2 bg-accent hover:bg-accent-dim text-black font-semibold text-xs rounded border border-accent hover:border-accent-dim transition"
                  >
                    {byokSaving ? "Connecting..." : "Save & Connect"}
                  </button>
                </div>
                <p className="text-[11px] text-slate-500 font-mono">
                  Get your key from Google AI Studio (aistudio.google.com). Encrypted server-side via AES.
                </p>
              </form>
            )}

            {byokStatusMsg && (
              <div className={`p-3 rounded text-xs flex items-center gap-2 ${
                byokStatusMsg.type === "success" 
                  ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400" 
                  : "bg-rose-500/10 border border-rose-500/30 text-rose-300"
              }`}>
                {byokStatusMsg.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                {byokStatusMsg.message}
              </div>
            )}
          </div>
        )}
      </div>

      {/* DEVELOPER API KEYS SECTION */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Code2 className="w-5 h-5 text-indigo-400" />
            Developer API Keys
          </h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-accent hover:bg-accent-dim text-black text-xs font-semibold rounded border border-accent hover:border-accent-dim transition"
          >
            <PlusCircle className="w-4 h-4" />
            Generate New Key
          </button>
        </div>

        {/* Secret Key Banner (Shown Once On Creation) */}
        {newKeyData && (
          <div className="p-5 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-3">
            <div className="flex items-center justify-between text-amber-300 font-bold text-sm">
              <span className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-400" />
                API Key Generated — Copy it now!
              </span>
              <button onClick={() => setNewKeyData(null)} className="text-xs text-slate-400 hover:text-slate-200">
                Dismiss
              </button>
            </div>
            <p className="text-xs text-slate-300">
              For security, this secret key will never be shown again. Store it securely in your environment variables.
            </p>
            <div className="flex items-center gap-2 bg-slate-950 p-2.5 rounded border border-amber-500/20 font-mono text-xs text-amber-200">
              <span className="flex-1 truncate">{newKeyData.api_key}</span>
              <button
                onClick={() => copyToClipboard(newKeyData.api_key)}
                className="px-2.5 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded flex items-center gap-1.5 text-xs transition"
              >
                <Copy className="w-3.5 h-3.5" />
                Copy
              </button>
            </div>
          </div>
        )}

        {/* Keys Table */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 text-xs font-mono border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Key Name</th>
                <th className="py-3.5 px-4">Prefix</th>
                <th className="py-3.5 px-4">Created</th>
                <th className="py-3.5 px-4">Last Used</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {loading ? (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-slate-500">
                    Loading API keys...
                  </td>
                </tr>
              ) : keys.length === 0 ? (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-slate-500">
                    No active API keys found. Click "Generate New Key" to create one.
                  </td>
                </tr>
              ) : (
                keys.map((k) => (
                  <tr key={k.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 font-sans font-semibold text-slate-200">{k.name}</td>
                    <td className="py-3.5 px-4 text-indigo-300">{k.prefix}</td>
                    <td className="py-3.5 px-4 text-slate-400">{new Date(k.created_at).toLocaleDateString()}</td>
                    <td className="py-3.5 px-4 text-slate-500">
                      {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => setRevokeKeyTarget(k)}
                        className="text-rose-400 hover:text-rose-300 p-1 transition"
                        title="Revoke API key"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Key className="w-5 h-5 text-indigo-400" />
              Generate Developer API Key
            </h3>
            <form onSubmit={handleCreateKey} className="space-y-3">
              <div>
                <label className="text-xs font-mono text-slate-400">Key Name / Identifier</label>
                <input
                  type="text"
                  placeholder="e.g. Production CI/CD Worker"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-slate-100 text-sm focus:outline-none focus:border-indigo-400"
                  required
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 bg-accent hover:bg-accent-dim text-black font-semibold text-xs rounded border border-accent hover:border-accent-dim transition"
                >
                  {submitting ? "Generating..." : "Generate Key"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirm Revoke Key Dialog */}
      <ConfirmDialog
        isOpen={Boolean(revokeKeyTarget)}
        title="Revoke Developer API Key"
        description={`Are you sure you want to revoke key "${revokeKeyTarget?.name}"? Any active backend services, cron jobs, or workers using this key will immediately lose access.`}
        confirmText="Revoke API Key"
        variant="danger"
        isBusy={isDestructiveBusy}
        onConfirm={confirmRevokeKey}
        onCancel={() => setRevokeKeyTarget(null)}
      />

      {/* Confirm Remove BYOK Dialog */}
      <ConfirmDialog
        isOpen={showRemoveByokModal}
        title="Remove Workspace BYOK Key"
        description="Are you sure you want to remove your workspace BYOK Google Gemini key? AI operations and generation will immediately switch back to HELIX Managed credits."
        confirmText="Remove Key"
        variant="danger"
        isBusy={isDestructiveBusy}
        onConfirm={confirmRemoveByok}
        onCancel={() => setShowRemoveByokModal(false)}
      />

      </div>
    </div>
  )
}

export default ApiKeysPage
