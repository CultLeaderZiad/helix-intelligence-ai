import { useState, useEffect } from "react"
import { Link, Navigate } from "react-router-dom"
import { ArrowLeft, Loader2, MailCheck } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { APP_HOME } from "@/app/ProtectedRoute"
import { AuthLayout } from "@/features/auth/AuthLayout"
import { AuthField } from "@/features/auth/AuthField"
import { FormBanner } from "@/features/auth/FormBanner"
import { formatAuthFieldError, validateEmailOnly } from "@/features/auth/validation"
import { Input } from "@/components/ui/Field"
import { Button } from "@/components/ui/Button"
import { useLanguage } from "@/context/LanguageContext"

/**
 * Forgot password. The service resolves ok even for an unknown address
 * (account-enumeration is a leak), so the confirmation copy is identical
 * either way — we confirm the request was accepted, not that an account
 * exists.
 */
export function ForgotPasswordPage() {
  const { requestPasswordReset, isAuthenticated } = useAuth()
  const { t } = useLanguage()

  const [email, setEmail] = useState("")
  const [error, setError] = useState(null)
  const [authError, setAuthError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [sentTo, setSentTo] = useState(null)
  const [resetUrl, setResetUrl] = useState(null)
  const [isSlow, setIsSlow] = useState(false)

  useEffect(() => {
    let timer
    if (submitting) {
      timer = setTimeout(() => setIsSlow(true), 3000)
    } else {
      setIsSlow(false)
    }
    return () => clearTimeout(timer)
  }, [submitting])

  if (isAuthenticated) return <Navigate to={APP_HOME} replace />

  /** @param {import("react").FormEvent<HTMLFormElement>} [event] */
  async function onSubmit(event) {
    if (event?.preventDefault) event.preventDefault()
    setAuthError(null)
    const nextErrors = validateEmailOnly({ email })
    setError(nextErrors.email ?? null)
    if (nextErrors.email) return

    setSubmitting(true)
    try {
      const result = await requestPasswordReset({ email: email.trim() })
      setSentTo(email.trim())
      setResetUrl(result?.reset_url ?? null)
    } catch (err) {
      const isCold = err?.code === "network_error" || err?.code === "server_waking" || (err?.status >= 502 && err?.status <= 504)
      setAuthError({
        status: isCold ? t("authServerWakingStatus", "Server waking") : t("authForgotFailed", "Unable to request a reset link. Please try again."),
        tone: isCold ? "warning" : "danger",
        message: isCold ? t("authBackendWaking", "The service is starting. Retry to complete sign in.") : t("authForgotFailed", "Unable to request a reset link. Please try again."),
        isColdStart: isCold,
      })
      setSubmitting(false)
    }
  }

  /* Confirmation state — deliberately generic, see note above. Sole
     exception: when the backend returns a dev-mode reset link (no mail
     provider configured), we surface it directly. */
  if (sentTo) {
    return (
      <AuthLayout
        eyebrow={t("authRecovery", "Recovery")}
        title={t("authResetEmailSentTitle", "Check your email")}
        footer={
          <Link
            to="/sign-in"
            className="text-accent transition-colors hover:text-accent-dim"
          >
            {t("authBackToSignIn", "Back to sign in")}
          </Link>
        }
      >
        <div className="flex flex-col gap-4">
          <FormBanner tone="success" status={t("authRequestAccepted", "Request accepted")}>
            {t("authResetEmailSent", "If an account exists for this address, a password-reset link has been sent.")}
          </FormBanner>
          {resetUrl ? (
            <div className="flex flex-col gap-2 rounded-sm border border-accent/30 bg-surface p-4">
              <p className="label-mono text-[10px] uppercase tracking-[0.08em] text-accent-dim">
                {t("authDevDeliveryLabel", "Development delivery · no mail provider configured")}
              </p>
              <p className="text-xs leading-relaxed text-text-muted">
                {t("authDevDeliveryExplanation", "Email delivery is not configured here. The backend returned this development reset link:")}
              </p>
              <Link
                to={resetUrl.replace(/^https?:\/\/[^/]+/, "")}
                className="break-all font-mono text-xs leading-relaxed text-accent underline-offset-2 transition-colors hover:text-accent-dim hover:underline"
              >
                {resetUrl}
              </Link>
            </div>
          ) : null}
          <div className="flex items-start gap-2.5 text-xs leading-relaxed text-text-muted">
            <MailCheck
              className="mt-0.5 h-4 w-4 shrink-0 text-text-faint"
              aria-hidden="true"
            />
            <p>
              {t("authEmailDeliveryHelp", "If the message does not appear, check your spam folder or try another address.")} {" "}
              <button
                type="button"
                onClick={() => {
                  setSentTo(null)
                  setSubmitting(false)
                }}
                className="text-accent transition-colors hover:text-accent-dim"
              >
                {t("authTryAnotherEmail", "Try another email")}
              </button>
              .
            </p>
          </div>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      eyebrow={t("authRecovery", "Recovery")}
      title={t("authForgotTitle", "Reset your password")}
      description={t("authForgotDescription", "Enter your email and we’ll send a password-reset link if an account exists.")}
      footer={
        <Link
          to="/sign-in"
          className="inline-flex items-center gap-1 text-accent transition-colors hover:text-accent-dim"
        >
          <ArrowLeft className="h-3 w-3" aria-hidden="true" />
          {t("authBackToSignIn", "Back to sign in")}
        </Link>
      }
    >
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        {authError ? (
          <FormBanner
            status={authError.status}
            tone={authError.tone}
            action={
              authError.isColdStart ? (
                <Button
                  type="button"
                  size="xs"
                  variant="outline"
                  onClick={() => void onSubmit()}
                >
                  {t("authRetry", "Retry")}
                </Button>
              ) : null
            }
          >
            {authError.message}
          </FormBanner>
        ) : null}

        <AuthField id="email" label={t("authEmail", "Email")} error={formatAuthFieldError(error, t)}>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            autoFocus
            placeholder={t("authEmailPlaceholder", "you@company.com")}
            value={email}
            disabled={submitting}
            aria-invalid={Boolean(error)}
            onChange={(e) => {
              setEmail(e.target.value)
              if (error) setError(null)
              if (authError) setAuthError(null)
            }}
            className={error ? "border-danger focus:border-danger" : undefined}
          />
        </AuthField>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          disabled={submitting}
          className="mt-1 w-full"
        >
          {submitting ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              {isSlow ? t("authSendingSlow", "Still connecting…") : t("authSending", "Sending…")}
            </>
          ) : (
            t("authSendResetLink", "Send reset link")
          )}
        </Button>
      </form>
    </AuthLayout>
  )
}

export default ForgotPasswordPage
