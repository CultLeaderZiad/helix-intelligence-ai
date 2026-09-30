import { useState, useEffect } from "react"
import { Link, Navigate, useNavigate } from "react-router-dom"
import { ArrowRight, Loader2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { APP_HOME } from "@/app/ProtectedRoute"
import { AuthLayout } from "@/features/auth/AuthLayout"
import { AuthField } from "@/features/auth/AuthField"
import { FormBanner } from "@/features/auth/FormBanner"
import { PasswordStrength } from "@/features/auth/PasswordStrength"
import { validateSignUp } from "@/features/auth/validation"
import { Input, PasswordInput } from "@/components/ui/Field"
import { Button } from "@/components/ui/Button"
import { ServiceError } from "@/services"
import { getAttribution, clearAttribution } from "@/lib/utm"
import { track } from "@/lib/analytics"

/**
 * Sign up. New accounts are always created as 'customer' server-side —
 * this page cannot request a role, and does not try to. On success the
 * context flips to authenticated and we send them to the app home; the
 * guard resolves anything role-specific from there.
 */
export function SignUpPage() {
  const { signUp, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [values, setValues] = useState({ name: "", email: "", password: "" })
  const [consentAgreed, setConsentAgreed] = useState(false)
  const [marketingOptIn, setMarketingOptIn] = useState(false)
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

  function update(key, value) {
    setValues((s) => ({ ...s, [key]: value }))
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }))
    if (authError) setAuthError(null)
  }

  async function onSubmit(event) {
    if (event?.preventDefault) event.preventDefault()
    if (submitting) return

    setAuthError(null)
    const nextErrors = validateSignUp(values)
    if (!consentAgreed) {
      nextErrors.consent = "You must accept the Terms and Privacy Policy to create an account."
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      const firstMsg = nextErrors.name
        ? "Please enter your full name."
        : nextErrors.email === "invalid email"
        ? "Please enter a valid email address."
        : nextErrors.email
        ? "Email address is required."
        : nextErrors.password === "min 8 chars"
        ? "Password must be at least 8 characters long."
        : nextErrors.password
        ? "Password is required."
        : "Please accept the Terms of Service and Privacy Policy to proceed."
      setAuthError({
        status: "validation error",
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
      track("signup", {
        source: attribution.utm_source || "direct",
        medium: attribution.utm_medium || "none",
        campaign: attribution.utm_campaign || "none",
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
          status: "account exists",
          tone: "info",
          message: "An account with this email already exists.",
          isDuplicate: true,
        })
      } else if (isCold) {
        setAuthError({
          status: "server waking",
          tone: "warning",
          message: "The backend server is waking up. Click retry below to complete your registration.",
          isColdStart: true,
        })
      } else {
        const errorDetail = err?.response?.data?.detail || err?.message || "Sign up failed. Please check your credentials and try again."
        setAuthError({
          status: "signup failed",
          tone: "danger",
          message: typeof errorDetail === "string" ? errorDetail : "Sign up failed. Please try again.",
          isColdStart: false,
        })
      }
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      eyebrow="Get started"
      title="Create your Helix account"
      description="Start with the Discover loop. New accounts join as an analyst."
      footer={
        <>
          Already have an account?{" "}
          <Link
            to="/sign-in"
            className="text-accent transition-colors hover:text-accent-dim"
          >
            Sign in
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
                  Sign in
                </Button>
              ) : authError.isColdStart ? (
                <Button
                  type="button"
                  size="xs"
                  variant="outline"
                  onClick={onSubmit}
                >
                  Retry
                </Button>
              ) : null
            }
          >
            {authError.message}
          </FormBanner>
        ) : null}

        <AuthField id="name" label="Name" error={errors.name}>
          <Input
            id="name"
            name="name"
            type="text"
            autoComplete="name"
            autoFocus
            placeholder="Ada Lovelace"
            value={values.name}
            disabled={submitting}
            aria-invalid={Boolean(errors.name)}
            onChange={(e) => update("name", e.target.value)}
            className={errors.name ? "border-danger focus:border-danger" : undefined}
          />
        </AuthField>

        <AuthField id="email" label="Email" error={errors.email}>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            value={values.email}
            disabled={submitting}
            aria-invalid={Boolean(errors.email)}
            onChange={(e) => update("email", e.target.value)}
            className={errors.email ? "border-danger focus:border-danger" : undefined}
          />
        </AuthField>

        <AuthField id="password" label="Password" error={errors.password}>
          <PasswordInput
            id="password"
            name="password"
            autoComplete="new-password"
            placeholder="At least 8 characters"
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
              I agree to the{" "}
              <a href="/terms" target="_blank" rel="noreferrer" className="text-accent hover:underline">
                Terms of Service
              </a>{" "}
              and{" "}
              <a href="/privacy" target="_blank" rel="noreferrer" className="text-accent hover:underline">
                Privacy Policy
              </a>
              .
            </span>
          </label>
          {errors.consent && (
            <p className="text-[11px] text-danger font-mono" role="alert">{errors.consent}</p>
          )}

          <label htmlFor="marketing-optin" className="flex items-start gap-2.5 cursor-pointer text-text-faint select-none">
            <input
              type="checkbox"
              id="marketing-optin"
              checked={marketingOptIn}
              onChange={(e) => setMarketingOptIn(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded-xs border-border bg-surface-2 accent-accent focus:ring-1 focus:ring-accent"
            />
            <span className="leading-relaxed">Send me product updates and major release announcements (optional).</span>
          </label>
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
              {isSlow ? "Waking server (connecting)…" : "Creating account…"}
            </>
          ) : (
            <>
              Create account
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </>
          )}
        </Button>
      </form>
    </AuthLayout>
  )
}


export default SignUpPage
