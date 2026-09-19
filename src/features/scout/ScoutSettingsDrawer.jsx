import React, { useState, useEffect } from "react"
import { X, ShieldCheck, Key, Lock, Check } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { scoutService } from "@/services"

export function ScoutSettingsDrawer({ open, onClose }) {
  const [hunterKey, setHunterKey] = useState("")
  const [linkedinCookie, setLinkedinCookie] = useState("")
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (open) {
      scoutService.getSettings?.().catch(() => {})
    }
  }, [open])

  if (!open) return null

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await scoutService.updateSettings?.({
        hunter_api_key: hunterKey || undefined,
        linkedin_cookie: linkedinCookie || undefined,
      })
      setSaved(true)
      setTimeout(() => {
        setSaved(false)
        onClose()
      }, 800)
    } catch (err) {
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-xs font-mono">
      <div className="w-full max-w-md bg-surface border-l border-border h-full flex flex-col justify-between p-5 overflow-y-auto">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <span className="text-[10px] uppercase tracking-[0.14em] text-accent font-semibold">
                HELIX SCOUT
              </span>
              <h3 className="text-base font-bold text-white">Scout Settings</h3>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded text-text-faint hover:text-white transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <form onSubmit={handleSave} className="space-y-5">
            {/* Hunter BYOK */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <label className="text-text font-medium flex items-center gap-1.5">
                  <Key className="h-3.5 w-3.5 text-text-faint" />
                  Hunter.io API Key (BYOK)
                </label>
                <span className="text-[10px] text-text-faint">Optional</span>
              </div>
              <input
                type="password"
                placeholder="Enter Hunter API key for deep email enrichment..."
                value={hunterKey}
                onChange={(e) => setHunterKey(e.target.value)}
                className="w-full rounded-[4px] border border-border bg-surface-2 px-3 py-2 text-xs text-text placeholder:text-text-faint focus:border-accent focus:outline-none"
              />
              <p className="text-[10.5px] text-text-faint leading-relaxed">
                Connect your Hunter key to verify professional work domain emails.
              </p>
            </div>

            {/* LinkedIn Session Cookie BYOK */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <label className="text-text font-medium flex items-center gap-1.5">
                  <Lock className="h-3.5 w-3.5 text-text-faint" />
                  LinkedIn Session Cookie (li_at)
                </label>
                <span className="text-[10px] text-text-faint">Optional</span>
              </div>
              <input
                type="password"
                placeholder="AQEDATk... (encrypted at rest)"
                value={linkedinCookie}
                onChange={(e) => setLinkedinCookie(e.target.value)}
                className="w-full rounded-[4px] border border-border bg-surface-2 px-3 py-2 text-xs text-text placeholder:text-text-faint focus:border-accent focus:outline-none"
              />
              <p className="text-[10.5px] text-text-faint leading-relaxed">
                Encrypted at rest. Used strictly for read-only profile lead enrichment.
              </p>
            </div>

            {/* Read-only Proxy Status */}
            <div className="rounded-[4px] border border-border/80 bg-surface-2 p-3 space-y-1.5 text-xs">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-accent" />
                <span className="font-semibold text-white">Proxy Architecture</span>
              </div>
              <p className="text-[11px] text-text-muted">
                Managed Residential Pool (active) · Zero free proxy rotation in production.
              </p>
            </div>

            <Button
              type="submit"
              disabled={saving}
              variant="primary"
              className="w-full rounded-[4px] font-mono text-xs font-bold uppercase tracking-wider"
            >
              {saved ? (
                <>
                  <Check className="h-4 w-4 mr-1" />
                  SAVED
                </>
              ) : saving ? (
                "SAVING..."
              ) : (
                "SAVE SETTINGS"
              )}
            </Button>
          </form>
        </div>

        {/* MIT Attribution Footer */}
        <div className="border-t border-border pt-4 text-center">
          <p className="text-[10.5px] text-text-faint leading-relaxed">
            Helix Scout · Scrapers adapted from{" "}
            <a
              href="https://github.com/kiryano/Scout"
              target="_blank"
              rel="noreferrer"
              className="text-text-muted hover:text-accent underline"
            >
              kiryano/Scout (MIT)
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
