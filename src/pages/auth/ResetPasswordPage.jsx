import { useState } from "react"
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom"
import { ArrowLeft, CheckCircle2, Loader2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { APP_HOME } from "@/app/ProtectedRoute"
import { AuthLayout } from "@/features/auth/AuthLayout"
import { AuthField } from "@/features/auth/AuthField"
import { FormBanner } from "@/features/auth/FormBanner"
import { PasswordStrength } from "@/features/auth/PasswordStrength"
import { Input } from "@/components/ui/Field"
import { Button } from "@/components/ui/Button"
import { ServiceError } from "@/services"

/**
 * Sets a new password from a reset link (/reset-password?token=…).
 * A successful reset returns a fresh session, so the user lands in the app
 * immediately; an invalid/expired/used token shows a recovered error state
 * pointing back to the forgot-password form.
 */
export function ResetPasswordPage() {
  const { resetPassword, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get("token") ?? ""

  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [fieldError, setFieldError] = useState(null)
  const [authError, setAuthError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  if (isAuthenticated) return <Navigate to={APP_HOME} replace />

  async function onSubmit(event) {
    if (event?.preventDefault) event.preventDefault()
    setAuthError(null)

    if (!token) {
      setAuthError({
        status: "missing token",
        tone: "danger",
        message: "This reset link is incomplete. Request a new one from the forgot-password page.",
      })
      return
    }
    if (!password) {
      setFieldError("required")
      return
    }
    if (password.length < 8) {
      setFieldError("min 8 chars")
      return
    }
    if (password !== confirm) {
      setFieldError("passwords must match")
      return
    }

    setSubmitting(true)
    try {
      await resetPassword({ token, newPassword: password })
      navigate(APP_HOME, { replace: true })
    } catch (err) {
      const message =
        typeof err?.detail === "string"
          ? err.detail
          : err instanceof ServiceError
            ? err.message
            : err?.message || "Could not reset your password. Please try again."
      setAuthError({
        status: "reset failed",
        tone: "danger",
        message,
        isColdStart: false,
      })
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      eyebrow="Recovery"
      title="Set a new password"
      description="Choose a new password for your account."
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
        {authError ? (
          <FormBanner status={authError.status} tone={authError.tone}>
            {authError.message}
          </FormBanner>
        ) : null}

        <AuthField
          id="password"
          label="New password"
          error={fieldError}
        >
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="new-password"
            autoFocus
            placeholder="••••••••"
            value={password}
            disabled={submitting}
            aria-invalid={Boolean(fieldError)}
            onChange={(e) => {
              setPassword(e.target.value)
              if (fieldError) setFieldError(null)
              if (authError) setAuthError(null)
            }}
            className={fieldError ? "border-danger focus:border-danger" : undefined}
          />
        </AuthField>

        <PasswordStrength value={password} />

        <AuthField id="confirm" label="Confirm password">
          <Input
            id="confirm"
            name="confirm"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            value={confirm}
            disabled={submitting}
            aria-invalid={Boolean(fieldError && fieldError === "passwords must match")}
            onChange={(e) => {
              setConfirm(e.target.value)
              if (fieldError) setFieldError(null)
              if (authError) setAuthError(null)
            }}
            className={fieldError === "passwords must match" ? "border-danger focus:border-danger" : undefined}
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
              Updating…
            </>
          ) : (
            "Set new password"
          )}
        </Button>

        {!token ? (
          <p className="flex items-start gap-2 text-xs leading-relaxed text-text-muted">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-text-faint" aria-hidden="true" />
            <span>
              No reset code detected in this link. Go to{" "}
              <Link to="/forgot-password" className="text-accent transition-colors hover:text-accent-dim">
                forgot password
              </Link>{" "}
              to request a fresh one.
            </span>
          </p>
        ) : null}
      </form>
    </AuthLayout>
  )
}

export default ResetPasswordPage
