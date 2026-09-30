import React, { useState } from "react"
import { MessageSquarePlus } from "lucide-react"
import { SupportFeedbackModal } from "@/components/SupportFeedbackModal"
import { cn } from "@/lib/utils"

export function FloatingSupportButton({ className, contextData = {} }) {
  const [modalOpen, setModalOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        aria-label="Open support and feedback modal"
        title="Open Support & Feedback"
        className={cn(
          "fixed bottom-10 right-4 sm:right-6 z-30 flex items-center gap-2 px-3 py-1.5 rounded-full border border-border/90 bg-surface-2/95 hover:bg-surface-3 hover:border-accent/50 text-text-muted hover:text-text shadow-lg backdrop-blur-md text-xs font-mono transition-all duration-200 hover:scale-105 active:scale-95 cursor-pointer select-none",
          className
        )}
      >
        <MessageSquarePlus className="h-3.5 w-3.5 text-accent shrink-0" />
        <span className="hidden sm:inline font-medium tracking-tight">Feedback &amp; Support</span>
        <span className="sm:hidden font-medium">Support</span>
      </button>

      <SupportFeedbackModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        initialContext={{
          page: typeof window !== "undefined" ? window.location.pathname : "workspace",
          ...contextData,
        }}
      />
    </>
  )
}

export default FloatingSupportButton
