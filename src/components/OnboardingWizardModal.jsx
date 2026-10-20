import { useEffect, useRef, useState } from "react"
import { ArrowRight, Check, X } from "lucide-react"
import { useLanguage } from "../context/LanguageContext"
import {
  getW5OnboardingText,
  ONBOARDING_TOUR_RESTART_EVENT,
} from "../i18n/w5Onboarding"

const INDUSTRIES = [
  ["ecommerce", "w5_wizard_industry_ecommerce"],
  ["saas", "w5_wizard_industry_saas"],
  ["health", "w5_wizard_industry_health"],
  ["fashion", "w5_wizard_industry_fashion"],
  ["finance", "w5_wizard_industry_finance"],
  ["education", "w5_wizard_industry_education"],
]

function getFocusableElements(container) {
  return Array.from(
    container.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((element) => !element.hidden && element.getAttribute("aria-hidden") !== "true")
}

export function OnboardingWizardModal({
  isOpen,
  onClose,
  onDismiss,
  onSearchSelect = undefined,
}) {
  const { lang, isRtl, t } = useLanguage()
  const [step, setStep] = useState(1)
  const [selectedIndustry, setSelectedIndustry] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  const [restartingTour, setRestartingTour] = useState(false)
  const dialogRef = useRef(null)
  const closeRef = useRef(null)
  const onCloseRef = useRef(onClose)
  const onDismissRef = useRef(onDismiss)
  onCloseRef.current = onClose
  onDismissRef.current = onDismiss

  const translate = (key) => t(key, getW5OnboardingText(lang, key))

  useEffect(() => {
    const handleTourRestart = (event) => {
      if (event.detail?.persisted === true) setRestartingTour(true)
    }
    window.addEventListener(ONBOARDING_TOUR_RESTART_EVENT, handleTourRestart)
    return () => window.removeEventListener(ONBOARDING_TOUR_RESTART_EVENT, handleTourRestart)
  }, [])

  useEffect(() => {
    if (!isOpen) setRestartingTour(false)
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return undefined

    setStep(1)
    setSelectedIndustry("")
    setSearchQuery("")
    const previousFocus = document.activeElement
    const originalBodyOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    closeRef.current?.focus()

    const dismiss = () => {
      if (onDismissRef.current) onDismissRef.current()
      else onCloseRef.current?.(null)
    }

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault()
        dismiss()
        return
      }
      if (event.key !== "Tab" || !dialogRef.current) return

      const focusable = getFocusableElements(dialogRef.current)
      if (!focusable.length) {
        event.preventDefault()
        dialogRef.current.focus()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      document.body.style.overflow = originalBodyOverflow
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus()
    }
  }, [isOpen])

  if (!isOpen || restartingTour) return null

  const finish = () => {
    const query = searchQuery.trim()
    onClose?.(query || null)
    if (query && onSearchSelect) onSearchSelect(query)
  }

  const continueToSearch = () => {
    if (selectedIndustry) setStep(2)
  }

  const dismiss = () => {
    if (onDismiss) onDismiss()
    else onClose?.(null)
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 p-3 backdrop-blur-md sm:p-6"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) dismiss()
      }}
    >
      <section
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
        aria-describedby="onboarding-description"
        dir={isRtl ? "rtl" : "ltr"}
        tabIndex={-1}
        className="relative max-h-[min(90dvh,720px)] w-full max-w-xl overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl"
      >
        <div className="h-1.5 w-full bg-slate-800" aria-hidden="true">
          <div
            className="h-full bg-gradient-to-r from-teal-500 to-indigo-500 transition-all duration-300"
            style={{ width: `${step * 50}%` }}
          />
        </div>

        <button
          ref={closeRef}
          type="button"
          onClick={dismiss}
          aria-label={translate("w5_wizard_close")}
          className="absolute end-3 top-3 rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white sm:end-4 sm:top-4"
        >
          <X className="h-5 w-5" aria-hidden="true" />
        </button>

        <div className="space-y-6 p-5 sm:p-8">
          <div className="pe-10">
            <p className="text-xs font-semibold uppercase tracking-wide text-teal-400">
              {translate(step === 1 ? "w5_wizard_step_industry" : "w5_wizard_step_search")} · {step}/2
            </p>
            <h2 id="onboarding-title" className="mt-2 text-xl font-bold text-white sm:text-2xl">
              {translate("w5_wizard_title")}
            </h2>
            <p id="onboarding-description" className="mt-2 text-sm leading-6 text-slate-400">
              {translate("w5_wizard_description")}
            </p>
          </div>

          {step === 1 ? (
            <fieldset>
              <legend className="mb-3 text-sm font-medium text-slate-200">
                {translate("w5_wizard_step_industry")}
              </legend>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {INDUSTRIES.map(([id, key]) => {
                  const selected = selectedIndustry === id
                  return (
                    <button
                      key={id}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => setSelectedIndustry(id)}
                      className={`flex min-h-12 items-center justify-between gap-3 rounded-xl border px-4 py-3 text-start text-sm transition ${
                        selected
                          ? "border-teal-500 bg-teal-500/10 text-white"
                          : "border-slate-700 bg-slate-950/40 text-slate-300 hover:border-slate-500"
                      }`}
                    >
                      <span>{translate(key)}</span>
                      {selected && <Check className="h-4 w-4 shrink-0 text-teal-400" aria-hidden="true" />}
                    </button>
                  )
                })}
              </div>
            </fieldset>
          ) : (
            <div className="space-y-3">
              <label htmlFor="onboarding-brand" className="block text-sm font-medium text-slate-200">
                {translate("w5_wizard_brand_label")}
              </label>
              <input
                id="onboarding-brand"
                autoFocus
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") finish()
                }}
                placeholder={translate("w5_wizard_brand_placeholder")}
                className="min-h-12 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 text-start text-white outline-none transition placeholder:text-slate-500 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
              />
              <p className="text-sm leading-6 text-slate-400">{translate("w5_wizard_search_help")}</p>
            </div>
          )}

          <div className="flex flex-col-reverse gap-3 border-t border-slate-800 pt-5 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="button"
              onClick={dismiss}
              className="min-h-11 rounded-lg px-3 text-sm font-medium text-slate-400 transition hover:text-white"
            >
              {translate("w5_wizard_skip")}
            </button>
            <div className="flex gap-2">
              {step === 2 && (
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="min-h-11 rounded-lg border border-slate-700 px-4 text-sm font-medium text-slate-200 transition hover:bg-slate-800"
                >
                  {translate("w5_wizard_back")}
                </button>
              )}
              {step === 1 ? (
                <button
                  type="button"
                  onClick={continueToSearch}
                  disabled={!selectedIndustry}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-teal-500 px-4 text-sm font-semibold text-slate-950 transition hover:bg-teal-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {translate("w5_wizard_continue")}
                  <ArrowRight className={`h-4 w-4 ${isRtl ? "rotate-180" : ""}`} aria-hidden="true" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={finish}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-teal-500 px-4 text-sm font-semibold text-slate-950 transition hover:bg-teal-400"
                >
                  {translate("w5_wizard_open_discover")}
                  <ArrowRight className={`h-4 w-4 ${isRtl ? "rotate-180" : ""}`} aria-hidden="true" />
                </button>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
