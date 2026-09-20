import React, { useState } from "react"
import { Copy, Check, Code } from "lucide-react"
import { cn } from "@/lib/utils"

export function AtlasJsonView({ data, className = "" }) {
  const [copied, setCopied] = useState(false)

  const jsonString = typeof data === "object" ? JSON.stringify(data, null, 2) : String(data || "{}")

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn("rounded-[4px] border border-border bg-[#09090b] font-mono", className)}>
      <div className="flex items-center justify-between border-b border-border/80 bg-surface-2 px-3 py-2 text-[10px] uppercase tracking-wider text-text-faint">
        <div className="flex items-center gap-1.5 text-accent font-semibold">
          <Code className="h-3 w-3" />
          <span>Atlas Contract Schema</span>
        </div>
        <button
          type="button"
          onClick={handleCopy}
          className="rounded border border-border bg-surface px-2 py-0.5 text-[10px] font-bold text-text hover:border-accent hover:text-accent transition-colors flex items-center gap-1"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-accent" /> COPIED JSON
            </>
          ) : (
            <>
              <Copy className="h-3 w-3 text-text-faint" /> COPY JSON
            </>
          )}
        </button>
      </div>

      <pre className="p-3 text-[10.5px] leading-relaxed text-text-muted overflow-x-auto max-h-80 select-text">
        {jsonString}
      </pre>
    </div>
  )
}
