import React from "react"
import { AlertTriangle, RefreshCw } from "lucide-react"
import LanguageContext from "@/context/LanguageContext"

const CHUNK_RELOAD_LOCK = "chunk_reload_lock"

function isChunkLoadError(error) {
  const message = String(error?.message || "")
  return (
    message.includes("dynamically imported module") ||
    message.includes("Failed to fetch dynamically") ||
    message.includes("Importing a module script failed")
  )
}

function reloadLockTime() {
  try {
    return Number(window.sessionStorage.getItem(CHUNK_RELOAD_LOCK) || 0)
  } catch {
    return null
  }
}

/**
 * One boundary component, three containment levels:
 *  - "page"    full-screen fallback (root guard, unchanged behavior)
 *  - "region"  main-content-area guard — the shell (sidebar/nav/statusbar)
 *              survives a page crash
 *  - "compact" per-component guard — one crashed panel no longer takes
 *              down the page around it
 */
export class ErrorBoundary extends React.Component {
  static contextType = LanguageContext

  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error("A render error was caught by ErrorBoundary.")
    if (isChunkLoadError(error)) {
      const lastReload = reloadLockTime()
      const now = Date.now()
      if (lastReload !== null && now - lastReload > 8000) {
        try {
          window.sessionStorage.setItem(CHUNK_RELOAD_LOCK, String(now))
        } catch {
          return
        }
        window.location.reload()
      }
    }
    void errorInfo
  }

  translate = (key, english, arabic) => {
    const fallback = this.context?.lang === "ar" ? arabic : english
    return this.context?.t?.(key, fallback) || fallback
  }

  handleReset = () => {
    if (isChunkLoadError(this.state.error)) {
      window.location.reload()
      return
    }
    this.setState({ hasError: false, error: null })
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      const variant = this.props.variant ?? "page"

      if (variant === "page") {
        return (
          <div className="min-h-screen w-full flex items-center justify-center p-6 bg-slate-950 text-slate-100">
            <div className="max-w-md w-full p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl space-y-4 text-center">
              <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">
                  {this.translate("errorBoundary.pageTitle", "Something went wrong", "حدث خطأ ما")}
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  {this.translate(
                    "errorBoundary.pageDescription",
                    "An unexpected error prevented this page from rendering.",
                    "منع خطأ غير متوقع عرض هذه الصفحة."
                  )}
                </p>
              </div>
              <button
                onClick={this.handleReload}
                className="px-4 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs rounded-xl flex items-center justify-center gap-2 mx-auto transition"
              >
                <RefreshCw className="w-4 h-4" />
                {this.translate("errorBoundary.reload", "Reload workspace", "إعادة تحميل مساحة العمل")}
              </button>
            </div>
          </div>
        )
      }

      const isCompact = variant === "compact"
      return (
        <div
          className={
            isCompact
              ? "flex min-h-[120px] w-full items-center justify-center rounded border border-warning/40 bg-warning/5 p-4"
              : "flex min-h-[240px] w-full items-center justify-center p-6"
          }
          role="alert"
        >
          <div className={`w-full space-y-3 text-center ${isCompact ? "max-w-xs" : "max-w-md"}`}>
            <div
              className={
                isCompact
                  ? "mx-auto flex h-8 w-8 items-center justify-center rounded-full border border-warning/30 bg-warning/10 text-warning"
                  : "mx-auto flex h-10 w-10 items-center justify-center rounded-full border border-warning/30 bg-warning/10 text-warning"
              }
            >
              <AlertTriangle className={isCompact ? "h-4 w-4" : "h-5 w-5"} />
            </div>
            <div>
              <p className="text-sm font-semibold text-text">
                {this.translate("errorBoundary.areaTitle", "This area is unavailable", "هذه المنطقة غير متاحة")}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-text-muted">
                {this.translate(
                  "errorBoundary.areaDescription",
                  "This part of the app could not be displayed. The rest of the app is still available.",
                  "تعذّر عرض هذا الجزء من التطبيق. لا تزال بقية التطبيق متاحة."
                )}
              </p>
            </div>
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={this.handleReset}
                className="flex items-center gap-1.5 rounded border border-border-strong bg-surface-2 px-3 py-1.5 font-mono text-[11px] font-semibold uppercase text-text transition-colors hover:bg-surface-3"
              >
                <RefreshCw className="h-3 w-3" />
                {this.translate("errorBoundary.retry", "Try again", "حاول مرة أخرى")}
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
