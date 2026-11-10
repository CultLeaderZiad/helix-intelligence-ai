import { useState } from "react"
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom"
import { ArrowLeft, CheckCircle2, Loader2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { APP_HOME } from "@/app/ProtectedRoute"
import { AuthLayout } from "@/features/auth/AuthLayout"
import { AuthField } from "@/features/auth/AuthField"
import { FormBanner } from "@/features/auth/FormBanner"
import { PasswordStrength } from "@/features/auth/PasswordStrength"
import { PasswordInput } from "@/components/ui/Field"
import { Button } from "@/components/ui/Button"
import { useLanguage } from "@/context/LanguageContext"
import { formatAuthFieldError } from "@/features/auth/validation"

/**
 * Sets a new password from a reset link (/reset-password?token=…).
 * A successful reset returns a fresh session, so the user lands in the app
 * immediately; an invalid/expired/used token shows a recovered error state
 * pointing back to the forgot-password form.
 */
export function ResetPasswordPage() {
  const { resetPassword, isAuthenticated } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get("token") ?? ""

  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [fieldError, setFieldError] = useState(null)
  const [authError, setAuthError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  if (isAuthenticated) return <Navigate to={APP_HOME} replace />

  /** @param {import("react").FormEvent<HTMLFormElement>} [event] */
  async function onSubmit(event) {
    if (event?.preventDefault) event.preventDefault()
    setAuthError(null)

    if (!token) {
      setAuthError({
        status: t("authResetTokenRequired", "This reset link is missing its token."),
        tone: "danger",
        message: t("authResetTokenRequired", "This reset link is missing its token."),
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
      setAuthError({
        status: t("authResetFailed", "Unable to reset the password. Request a new reset link and try again."),
        tone: "danger",
        message: t("authResetFailed", "Unable to reset the password. Request a new reset link and try again."),
        isColdStart: false,
      })
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      eyebrow={t("authRecovery", "Recovery")}
      title={t("authSetPasswordTitle", "Choose a new password")}
      description={t("authSetPasswordDescription", "Enter and confirm your new password.")}
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
          <FormBanner status={authError.status} tone={authError.tone}>
            {authError.message}
          </FormBanner>
        ) : null}

        <AuthField
          id="password"
          label={t("authNewPassword", "New password")}
          error={formatAuthFieldError(fieldError, t)}
        >
          <PasswordInput
            id="password"
            name="password"
            autoComplete="new-password"
            autoFocus
            placeholder={t("authPasswordPlaceholder", "••••••••")}
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

        <AuthField id="confirm" label={t("authConfirmPassword", "Confirm password")}>
          <PasswordInput
            id="confirm"
            name="confirm"
            autoComplete="new-password"
            placeholder={t("authPasswordPlaceholder", "••••••••")}
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
              {t("authUpdatingPassword", "Updating password…")}
            </>
          ) : (
            t("authResetPasswordButton", "Update password")
          )}
        </Button>

        {!token ? (
          <p className="flex items-start gap-2 text-xs leading-relaxed text-text-muted">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-text-faint" aria-hidden="true" />
            <span>
              {t("authResetTokenHelp", "No reset token was detected in this link.")} {" "}
              <Link to="/forgot-password" className="text-accent transition-colors hover:text-accent-dim">
                {t("authRequestNewLink", "Request a new reset link")}
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
