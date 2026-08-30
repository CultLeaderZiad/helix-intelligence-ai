import React, { useState, useEffect } from "react"
import { accountService } from "@/services"
import { useAuth } from "@/context/AuthContext"
import { 
  Key, 
  PlusCircle, 
  Copy, 
  Trash2, 
  RefreshCw, 
  CheckCircle2, 
  ShieldAlert, 
  Code2 
} from "lucide-react"

export function ApiKeysPage() {
  const { user } = useAuth()
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const [newKeyData, setNewKeyData] = useState(null)

  // Create modal
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [name, setName] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const isFeatureEnabled = user?.feature_flags?.public_api === true

  const fetchKeys = async () => {
    if (!isFeatureEnabled) {
      setLoading(false)
      return
    }
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
  }, [isFeatureEnabled])

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
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
      alert(err.message || "Failed to generate API Key")
    } finally {
      setSubmitting(false)
    }
  }

  const handleRevokeKey = async (keyId) => {
    if (!confirm("Are you sure you want to revoke this API key? Applications using it will be disconnected.")) {
      return
    }
    try {
      await accountService.revokeApiKey(keyId)
      showToast("API key revoked successfully")
      setKeys((prev) => prev.filter((k) => k.id !== keyId))
    } catch (err) {
      alert(err.message || "Failed to revoke key")
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    showToast("Copied to clipboard!")
  }

  if (!isFeatureEnabled) {
    return (
      <div className="p-12 max-w-4xl mx-auto text-center space-y-4 font-sans">
        <Key className="w-12 h-12 text-slate-600 mx-auto" />
        <h2 className="text-xl font-bold text-slate-200">Public API Access Locked</h2>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          Your current plan does not include programmatic Developer API access. Upgrade your plan or enable the Public API feature flag to generate keys.
        </p>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <Key className="w-7 h-7 text-indigo-400" />
            Developer API Keys
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Programmatic access keys scoped to your workspace. Requests are authenticated via <code className="text-indigo-300">X-API-Key</code>.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchKeys}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded shadow-lg shadow-indigo-600/20 transition"
          >
            <PlusCircle className="w-4 h-4" />
            Generate New Key
          </button>
        </div>
      </div>

      {toast && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {toast}
        </div>
      )}

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
                      onClick={() => handleRevokeKey(k.id)}
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

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Key className="w-5 h-5 text-indigo-400" />
              Generate API Key
            </h3>
            <form onSubmit={handleCreateKey} className="space-y-3">
              <div>
                <label className="text-xs font-mono text-slate-400">Key Name / Identifier</label>
                <input
                  type="text"
                  placeholder="e.g. CI/CD Scraping Bot"
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
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded transition"
                >
                  {submitting ? "Generating..." : "Generate Key"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default ApiKeysPage
