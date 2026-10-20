import { useState, useEffect } from "react"
import { Link, Navigate, useNavigate } from "react-router-dom"
import { ArrowRight, Loader2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { APP_HOME } from "@/app/ProtectedRoute"
import { AuthLayout } from "@/features/auth/AuthLayout"
import { AuthField } from "@/features/auth/AuthField"
import { FormBanner } from "@/features/auth/FormBanner"
import { PasswordStrength } from "@/features/auth/PasswordStrength"
import { formatAuthFieldError, validateSignUp } from "@/features/auth/validation"
import { Input, PasswordInput } from "@/components/ui/Field"
import { Button } from "@/components/ui/Button"
import { getAttribution, clearAttribution } from "@/lib/utm"
import { track } from "@/lib/analytics"
import { useLanguage } from "@/context/LanguageContext"

/**
 * Sign up. New accounts are always created as 'customer' server-side —
 * this page cannot request a role, and does not try to. On success the
 * context flips to authenticated and we send them to the app home; the
 * guard resolves anything role-specific from there.
 */
export function SignUpPage() {
  const { signUp, isAuthenticated } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()

  const [values, setValues] = useState({ name: "", email: "", password: "" })
  const [consentAgreed, setConsentAgreed] = useState(false)
  const [errors, setErrors] = useState({})
  const [authError, setAuthError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
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

  /** @param {"name" | "email" | "password"} key @param {string} value */
  function update(key, value) {
    setValues((s) => ({ ...s, [key]: value }))
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }))
    if (authError) setAuthError(null)
  }

  /** @param {import("react").FormEvent<HTMLFormElement>} [event] */
  async function onSubmit(event) {
    if (event?.preventDefault) event.preventDefault()
    if (submitting) return

    setAuthError(null)
    const nextErrors = validateSignUp(values)
    if (!consentAgreed) {
      nextErrors.consent = t("authMustAcceptConsent", "Accept the Terms of Service and Privacy Policy to continue.")
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      const firstMsg = nextErrors.name
        ? t("authNameRequired", "Enter your full name.")
        : nextErrors.email === "invalid email"
        ? t("authEmailInvalid", "Enter a valid email address.")
        : nextErrors.email
        ? t("authEmailRequired", "Email address is required.")
        : nextErrors.password === "min 8 chars"
        ? t("authPasswordMin", "Password must be at least 8 characters.")
        : nextErrors.password
        ? t("authPasswordRequired", "Password is required.")
        : t("authMustAcceptConsent", "Accept the Terms of Service and Privacy Policy to continue.")
      setAuthError({
        status: t("authValidationError", "Check the highlighted fields"),
        tone: "danger",
        message: firstMsg,
      })
      return
    }

    setSubmitting(true)
    try {
      const attribution = getAttribution()
      await signUp({
        name: values.name.trim(),
        email: values.email.trim(),
        password: values.password,
        utm_source: attribution.utm_source,
        utm_medium: attribution.utm_medium,
        utm_campaign: attribution.utm_campaign,
        utm_term: attribution.utm_term,
        utm_content: attribution.utm_content,
        referrer: attribution.referrer || attribution.ref,
      })
      const EMAIL_REGEX = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/i
      const cleanParam = (val, fallback) => {
        if (!val || typeof val !== "string" || EMAIL_REGEX.test(val)) return fallback
        return val
      }
      track("signup", {
        source: cleanParam(attribution.utm_source, "direct"),
        medium: cleanParam(attribution.utm_medium, "none"),
        campaign: cleanParam(attribution.utm_campaign, "none"),
      })
      clearAttribution()
      navigate(APP_HOME, { replace: true })
    } catch (err) {
      const isCold = err?.code === "network_error" || err?.code === "server_waking" || (err?.status >= 502 && err?.status <= 504)
      const errLower = (err?.message || "").toLowerCase()
      const isDuplicate = err?.status === 400 && (
        errLower.includes("already registered") ||
        errLower.includes("already exists")
      )

      if (isDuplicate) {
        setErrors((prev) => ({ ...prev, email: "already registered" }))
        setAuthError({
          status: t("authAccountExistsStatus", "Account already exists"),
          tone: "info",
          message: t("authAccountExistsMessage", "An account with this email already exists. Sign in instead."),
          isDuplicate: true,
        })
      } else if (isCold) {
        setAuthError({
          status: t("authServerWakingStatus", "Server waking"),
          tone: "warning",
          message: t("authBackendWaking", "The service is starting. Retry to complete sign in."),
          isColdStart: true,
        })
      } else {
        setAuthError({
          status: t("authSignupFailed", "Unable to create your account. Please try again."),
          tone: "danger",
          message: t("authSignupFailed", "Unable to create your account. Please try again."),
          isColdStart: false,
        })
      }
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      eyebrow={t("authAccess", "Access")}
      title={t("authCreateAccountTitle", "Create an account")}
      description={t("authCreateAccountDescription", "Create an account to request workspace access. An administrator may need to approve access to features.")}
      footer={
        <>
          {t("authAlreadyAccount", "Already have an account?")} {" "}
          <Link
            to="/sign-in"
            className="text-accent transition-colors hover:text-accent-dim"
          >
            {t("authSignInLink", "Sign in")}
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        {authError ? (
          <FormBanner
            status={authError.status}
            tone={authError.tone}
            action={
              authError.isDuplicate ? (
                <Button
                  type="button"
                  size="xs"
                  variant="outline"
                  onClick={() => navigate("/sign-in", { state: { email: values.email.trim() } })}
                >
                  {t("authSignInLink", "Sign in")}
                </Button>
              ) : authError.isColdStart ? (
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

        <AuthField id="name" label={t("authFullName", "Full name")} error={formatAuthFieldError(errors.name, t)}>
          <Input
            id="name"
            name="name"
            type="text"
            autoComplete="name"
            autoFocus
            placeholder={t("authFullNamePlaceholder", "Your name")}
            value={values.name}
            disabled={submitting}
            aria-invalid={Boolean(errors.name)}
            onChange={(e) => update("name", e.target.value)}
            className={errors.name ? "border-danger focus:border-danger" : undefined}
          />
        </AuthField>

        <AuthField id="email" label={t("authEmail", "Email")} error={formatAuthFieldError(errors.email, t)}>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder={t("authEmailPlaceholder", "you@company.com")}
            value={values.email}
            disabled={submitting}
            aria-invalid={Boolean(errors.email)}
            onChange={(e) => update("email", e.target.value)}
            className={errors.email ? "border-danger focus:border-danger" : undefined}
          />
        </AuthField>

        <AuthField id="password" label={t("authPassword", "Password")} error={formatAuthFieldError(errors.password, t)}>
          <PasswordInput
            id="password"
            name="password"
            autoComplete="new-password"
            placeholder={t("authPasswordMin", "Password must be at least 8 characters.")}
            value={values.password}
            disabled={submitting}
            aria-invalid={Boolean(errors.password)}
            onChange={(e) => update("password", e.target.value)}
            className={errors.password ? "border-danger focus:border-danger" : undefined}
          />
        </AuthField>

        {values.password ? <PasswordStrength value={values.password} /> : null}

        <div className="space-y-2.5 pt-1 text-xs">
          <label htmlFor="terms-consent" className="flex items-start gap-2.5 cursor-pointer text-text-muted select-none">
            <input
              type="checkbox"
              id="terms-consent"
              checked={consentAgreed}
              onChange={(e) => {
                setConsentAgreed(e.target.checked)
                if (errors.consent) setErrors((prev) => ({ ...prev, consent: undefined }))
              }}
              className="mt-0.5 h-4 w-4 rounded-xs border-border bg-surface-2 accent-accent focus:ring-1 focus:ring-accent"
              required
            />
            <span className="leading-relaxed">
              {t("authTermsConsent", "I agree to the")} {" "}
              <a href="/terms" target="_blank" rel="noreferrer" className="text-accent hover:underline">
                {t("authTerms", "Terms of Service")}
              </a>{" "}
              {t("authAnd", "and")} {" "}
              <a href="/privacy" target="_blank" rel="noreferrer" className="text-accent hover:underline">
                {t("authPrivacy", "Privacy Policy")}
              </a>
              .
            </span>
          </label>
          {errors.consent && (
            <p className="text-[11px] text-danger font-mono" role="alert">{errors.consent}</p>
          )}

        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          disabled={submitting}
          className="mt-2 w-full font-bold uppercase tracking-wider"
        >
          {submitting ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              {isSlow ? t("authWakingServer", "Connecting to the server…") : t("authCreatingAccount", "Creating account…")}
            </>
          ) : (
            <>
              {t("authCreateAccountButton", "Create account")}
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </>
          )}
        </Button>
      </form>
    </AuthLayout>
  )
}


export default SignUpPage
