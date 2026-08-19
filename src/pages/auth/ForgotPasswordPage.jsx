import { useState } from "react"
import { Link, Navigate } from "react-router-dom"
import { ArrowLeft, Loader2, MailCheck } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { APP_HOME } from "@/app/ProtectedRoute"
import { AuthLayout } from "@/features/auth/AuthLayout"
import { AuthField } from "@/features/auth/AuthField"
import { FormBanner } from "@/features/auth/FormBanner"
import { validateEmailOnly } from "@/features/auth/validation"
import { Input } from "@/components/ui/Field"
import { Button } from "@/components/ui/Button"
import { ServiceError } from "@/services"

/**
 * Forgot password. The service resolves ok even for an unknown address
 * (account-enumeration is a leak), so the confirmation copy is identical
 * either way — we confirm the request was accepted, not that an account
 * exists.
 */
export function ForgotPasswordPage() {
  const { requestPasswordReset, isAuthenticated } = useAuth()

  const [email, setEmail] = useState("")
  const [error, setError] = useState(null)
  const [authError, setAuthError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [sentTo, setSentTo] = useState(null)

  if (isAuthenticated) return <Navigate to={APP_HOME} replace />

  async function onSubmit(event) {
    event.preventDefault()
    setAuthError(null)
    const nextErrors = validateEmailOnly({ email })
    setError(nextErrors.email ?? null)
    if (nextErrors.email) return

    setSubmitting(true)
    try {
      await requestPasswordReset({ email: email.trim() })
      setSentTo(email.trim())
    } catch (err) {
      setAuthError(
        err instanceof ServiceError
          ? err.message
          : "Could not send the reset link. Please try again.",
      )
      setSubmitting(false)
    }
  }

  /* Confirmation state — deliberately generic, see note above. */
  if (sentTo) {
    return (
      <AuthLayout
        eyebrow="Recovery"
        title="Check your email"
        footer={
          <Link
            to="/sign-in"
            className="text-accent transition-colors hover:text-accent-dim"
          >
            Return to sign in
          </Link>
        }
      >
        <div className="flex flex-col gap-4">
          <FormBanner tone="success" status="request sent">
            If an account exists for{" "}
            <span className="font-mono text-text">{sentTo}</span>, a password
            reset link is on its way.
          </FormBanner>
          <div className="flex items-start gap-2.5 text-xs leading-relaxed text-text-muted">
            <MailCheck
              className="mt-0.5 h-4 w-4 shrink-0 text-text-faint"
              aria-hidden="true"
            />
            <p>
              The link expires shortly for security. Didn&apos;t get it? Check
              spam, or{" "}
              <button
                type="button"
                onClick={() => {
                  setSentTo(null)
                  setSubmitting(false)
                }}
                className="text-accent transition-colors hover:text-accent-dim"
              >
                try another address
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
      eyebrow="Recovery"
      title="Reset your password"
      description="Enter the email on your account and we'll send a reset link."
      footer={
        <Link
          to="/sign-in"
          className="inline-flex items-center gap-1 text-accent transition-colors hover:text-accent-dim"
        >
          <ArrowLeft className="h-3 w-3" aria-hidden="true" />
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        {authError ? <FormBanner status="request failed">{authError}</FormBanner> : null}

        <AuthField id="email" label="Email" error={error}>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            autoFocus
            placeholder="you@company.com"
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
              Sending link…
            </>
          ) : (
            "Send reset link"
          )}
        </Button>
      </form>
    </AuthLayout>
  )
}
