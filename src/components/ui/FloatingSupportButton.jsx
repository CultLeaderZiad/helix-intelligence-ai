import React, { useState } from "react"
import { MessageSquarePlus } from "lucide-react"
import { SupportFeedbackModal } from "@/components/SupportFeedbackModal"
import { useLanguage } from "@/context/LanguageContext"
import { w5Support } from "@/i18n/w5Support"
import { cn } from "@/lib/utils"

const EMPTY_CONTEXT = Object.freeze({})

/** @param {{ className?: string, contextData?: Record<string, unknown> }} props */
export function FloatingSupportButton({ className = "", contextData = EMPTY_CONTEXT }) {
  const [modalOpen, setModalOpen] = useState(false)
  const { lang, t } = useLanguage()
  const words = w5Support[lang] || w5Support.en
  const label = t("newTicket", words.newTicket)

  return (
    <>
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        aria-label={label}
        title={label}
        className={cn(
          "fixed bottom-10 end-4 sm:end-6 z-30 flex items-center gap-2 px-3 py-1.5 rounded-full border border-border/90 bg-surface-2/95 hover:bg-surface-3 hover:border-accent/50 text-text-muted hover:text-text shadow-lg backdrop-blur-md text-xs font-mono transition-all duration-200 hover:scale-105 active:scale-95 cursor-pointer select-none",
          className,
        )}
      >
        <MessageSquarePlus className="h-3.5 w-3.5 text-accent shrink-0" aria-hidden="true" />
        <span className="hidden sm:inline font-medium tracking-tight">{label}</span>
        <span className="sm:hidden font-medium">{label}</span>
      </button>

      <SupportFeedbackModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        initialContextRecord={{
          page: typeof window !== "undefined" ? window.location.pathname : "workspace",
          ...contextData,
        }}
      />
    </>
  )
}

export default FloatingSupportButton
