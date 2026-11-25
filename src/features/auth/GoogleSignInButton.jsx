import { useEffect, useRef, useState } from "react"
import { useLanguage } from "@/context/LanguageContext"

const SCRIPT_SRC = "https://accounts.google.com/gsi/client"
export const GOOGLE_CLIENT_ID = String(import.meta.env?.VITE_GOOGLE_CLIENT_ID ?? "").trim()

/** Google Identity Services global, present once the script has loaded. @returns {any} */
const gis = () => /** @type {any} */ (window).google?.accounts?.id

let scriptPromise = null
function loadGoogleScript() {
  if (gis()) return Promise.resolve()
  scriptPromise ??= new Promise((resolve, reject) => {
    const s = document.createElement("script")
    s.src = SCRIPT_SRC
    s.async = true
    s.onload = resolve
    s.onerror = () => {
      scriptPromise = null
      reject(new Error("google_script_failed"))
    }
    document.head.appendChild(s)
  })
  return scriptPromise
}

/**
 * "Continue with Google". Renders Google's own button (it must be Google's, so the
 * browser can show the account chooser). The ID token goes to onCredential; the server
 * verifies it. Renders nothing when VITE_GOOGLE_CLIENT_ID is not set or the script is blocked.
 */
export function GoogleSignInButton({ onCredential, disabled = false }) {
  const { lang, t } = useLanguage()
  const box = useRef(null)
  const handler = useRef(onCredential)
  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState(false)
  handler.current = onCredential

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return undefined
    let live = true
    loadGoogleScript().then(() => {
      if (!live || !box.current) return
      gis().initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (res) => res?.credential && handler.current?.(res.credential),
        use_fedcm_for_prompt: true,
      })
      const width = Math.max(200, Math.min(400, Math.round(box.current.getBoundingClientRect().width) || 320))
      gis().renderButton(box.current, {
        type: "standard", theme: "filled_black", size: "large", text: "continue_with",
        shape: "rectangular", logo_alignment: "left", width, locale: lang === "ar" ? "ar" : "en",
      })
      setReady(true)
    }).catch(() => live && setFailed(true))
    return () => { live = false }
  }, [lang])

  if (!GOOGLE_CLIENT_ID || failed) return null
  return (
    <div className="flex flex-col gap-3" aria-label={t("authGoogleLabel", "Continue with Google")}>
      <div className="flex items-center gap-3 text-[11px] uppercase tracking-[0.08em] text-text-faint">
        <span className="h-px flex-1 bg-border" aria-hidden="true" />
        {t("authOr", "or")}
        <span className="h-px flex-1 bg-border" aria-hidden="true" />
      </div>
      <div
        ref={box}
        dir="ltr"
        className={`flex min-h-10 w-full justify-center ${disabled ? "pointer-events-none opacity-50" : ""} ${ready ? "" : "animate-pulse"}`}
      />
    </div>
  )
}

export default GoogleSignInButton
