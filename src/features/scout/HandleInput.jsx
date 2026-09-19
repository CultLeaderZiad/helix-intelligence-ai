import React, { useRef } from "react"
import { Upload, Play, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { cn } from "@/lib/utils"

export function HandleInput({
  value,
  onChange,
  enrichEmails,
  onToggleEnrich,
  onSubmit,
  isBusy,
  disabled,
}) {
  const fileInputRef = useRef(null)

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const content = event.target?.result
      if (typeof content === "string") {
        const extracted = content
          .split(/[\r\n,]+/)
          .map((line) => line.trim().replace(/^@/, ""))
          .filter(Boolean)
          .slice(0, 25)
          .join("\n")

        onChange(extracted)
      }
    }
    reader.readAsText(file)
    e.target.value = ""
  }

  const handleLines = value
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 items-start">
      {/* Handles Textarea */}
      <div className="lg:col-span-9 space-y-1.5">
        <label className="block font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted font-semibold">
          HANDLES
        </label>
        <textarea
          rows={3}
          disabled={disabled}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={`helixagency\ncultleaderziad\nacme_clinic_sa`}
          className="w-full rounded-[4px] border border-border bg-surface px-3 py-2 font-mono text-[12.5px] leading-relaxed text-text placeholder:text-text-faint focus:border-accent focus:outline-none transition-colors resize-y min-h-[88px]"
        />
        <div className="flex items-center justify-between text-[11px] font-mono text-text-faint">
          <span>One per line · or upload CSV/TXT · max 25 / job</span>
          <span className="tnum text-text-muted">{handleLines.length}/25 handles</span>
        </div>
      </div>

      {/* Action Controls */}
      <div className="lg:col-span-3 flex flex-col gap-2.5 pt-6 sm:pt-6 lg:pt-5">
        {/* Enrich emails toggle */}
        <div
          onClick={() => !disabled && onToggleEnrich(!enrichEmails)}
          className="flex items-center justify-between p-2 rounded-[4px] border border-border bg-surface cursor-pointer select-none transition-colors hover:border-border-strong"
        >
          <span className="font-mono text-[11px] text-text font-medium">Enrich emails</span>
          <div
            className={cn(
              "w-9 h-5 rounded-full p-0.5 transition-colors duration-200 ease-in-out flex items-center",
              enrichEmails ? "bg-accent" : "bg-[#27272a]"
            )}
          >
            <div
              className={cn(
                "w-4 h-4 rounded-full bg-bg shadow-md transform transition-transform duration-200 ease-in-out",
                enrichEmails ? "translate-x-4 bg-black" : "translate-x-0 bg-text-muted"
              )}
            />
          </div>
        </div>

        {/* Upload List Button */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.txt"
          className="hidden"
          onChange={handleFileUpload}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
          className="w-full rounded-[4px] border-border bg-surface font-mono text-[11px] uppercase tracking-wider text-text hover:border-text-muted"
        >
          <Upload className="h-3.5 w-3.5 mr-1.5 text-text-faint" />
          UPLOAD LIST
        </Button>

        {/* Run Scout CTA */}
        <button
          type="button"
          disabled={disabled || handleLines.length === 0 || isBusy}
          onClick={onSubmit}
          className={cn(
            "w-full rounded-[4px] bg-accent px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-black transition-all shadow-sm shadow-accent/20 flex items-center justify-center gap-2",
            disabled || handleLines.length === 0 || isBusy
              ? "opacity-40 cursor-not-allowed bg-accent/60"
              : "hover:bg-[#e4ff75] active:scale-[0.99]"
          )}
        >
          {isBusy ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin text-black" />
              RUNNING...
            </>
          ) : (
            <>
              <Play className="h-3 w-3 fill-current text-black" />
              RUN SCOUT
            </>
          )}
        </button>
      </div>
    </div>
  )
}
