import React from "react"
import { useLanguage } from "@/context/LanguageContext"
import { Globe } from "lucide-react"

export function LanguageSwitcher({ className = "" }) {
  const { lang, toggleLanguage } = useLanguage()

  return (
    <button
      type="button"
      onClick={toggleLanguage}
      title={lang === "en" ? "تبديل إلى العربية (RTL)" : "Switch to English"}
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded border border-border bg-surface text-xs font-mono font-semibold text-text hover:border-accent hover:text-accent transition-colors ${className}`}
    >
      <Globe className="h-3.5 w-3.5 text-accent" />
      <span>{lang === "en" ? "العربية" : "English"}</span>
    </button>
  )
}

export default LanguageSwitcher
