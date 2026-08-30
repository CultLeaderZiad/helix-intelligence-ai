import React from "react"
import { useLanguage } from "@/context/LanguageContext"
import { Globe, Languages } from "lucide-react"

export function LanguageSwitcher({ className = "" }) {
  const { lang, toggleLanguage } = useLanguage()

  return (
    <button
      type="button"
      onClick={toggleLanguage}
      title={lang === "en" ? "تبديل الواجهة إلى اللغة العربية (RTL)" : "Switch interface to English (LTR)"}
      className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg border-2 border-accent/60 bg-surface-2 hover:bg-surface-3 shadow-md text-xs font-bold text-text hover:border-accent hover:text-accent transition-all duration-200 cursor-pointer ${className}`}
    >
      <Languages className="h-4 w-4 text-accent animate-pulse" />
      <span className="font-sans font-bold text-[13px] tracking-wide text-accent">
        {lang === "en" ? "العربية (RTL)" : "English (LTR)"}
      </span>
    </button>
  )
}

export default LanguageSwitcher
