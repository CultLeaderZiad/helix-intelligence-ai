import { useState } from "react"
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom"
import { ArrowRight, Loader2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { APP_HOME } from "@/app/ProtectedRoute"
import { AuthLayout } from "@/features/auth/AuthLayout"
import { AuthField } from "@/features/auth/AuthField"
import { FormBanner } from "@/features/auth/FormBanner"
import { validateSignIn } from "@/features/auth/validation"
import { Input } from "@/components/ui/Field"
import { Button } from "@/components/ui/Button"
import { ServiceError } from "@/services"
import { DATA_SOURCE } from "@/services/config"

/**
 * Sign in. Owns its own UI intent (field values, validation, submit state)
 * and defers the durable outcome to AuthContext.signIn. It never inspects
 * `role` — where the user lands is a route concern, resolved by the guard
 * that sent them here (via `location.state.from`) or APP_HOME.
 */
export function SignInPage() {
  const { signIn, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = location.state?.from?.pathname ?? APP_HOME

  const [values, setValues] = useState({ email: "", password: "" })
  const [errors, setErrors] = useState({})
  const [authError, setAuthError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  /* Already signed in? Never show the form — go where they were headed. */
  if (isAuthenticated) return <Navigate to={redirectTo} replace />

  function update(key, value) {
    setValues((s) => ({ ...s, [key]: value }))
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }))
    if (authError) setAuthError(null)
  }

  async function onSubmit(event) {
    event.preventDefault()
    setAuthError(null)
    const nextErrors = validateSignIn(values)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    try {
      const user = await signIn({ email: values.email.trim(), password: values.password })
      
      let finalRedirect = redirectTo
      // If the user was just heading to the default landing page, route based on role
      if (redirectTo === APP_HOME || redirectTo === "/") {
        finalRedirect = user?.role === "admin" ? "/admin" : "/discover"
      }
      
      navigate(finalRedirect, { replace: true })
    } catch (err) {
      setAuthError(
        err instanceof ServiceError
          ? err.message
          : "Sign in failed. Please try again.",
      )
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      eyebrow="Access"
      title="Sign in to Helix"
      description="Enter your credentials to reach the intelligence loops."
      footer={
        <>
          No account?{" "}
          <Link
            to="/sign-up"
            className="text-accent transition-colors hover:text-accent-dim"
          >
            Create one
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        {authError ? <FormBanner status="auth failed">{authError}</FormBanner> : null}

        <AuthField id="email" label="Email" error={errors.email}>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            autoFocus
            placeholder="you@company.com"
            value={values.email}
            disabled={submitting}
            aria-invalid={Boolean(errors.email)}
            onChange={(e) => update("email", e.target.value)}
            className={errors.email ? "border-danger focus:border-danger" : undefined}
          />
        </AuthField>

        <AuthField
          id="password"
          label="Password"
          error={errors.password}
          action={
            <Link
              to="/forgot-password"
              className="font-mono text-[10px] uppercase leading-none tracking-[0.08em] text-text-muted transition-colors hover:text-accent"
            >
              forgot?
            </Link>
          }
        >
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={values.password}
            disabled={submitting}
            aria-invalid={Boolean(errors.password)}
            onChange={(e) => update("password", e.target.value)}
            className={errors.password ? "border-danger focus:border-danger" : undefined}
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
              Signing in…
            </>
          ) : (
            <>
              Sign in
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </>
          )}
        </Button>
      </form>

      {/* Mock backend ships seeded accounts so both roles are reachable
          without a signup. Hidden in API/production mode. */}
      {DATA_SOURCE !== "api" && (
        <details className="mt-4 border-t border-border pt-3">
          <summary className="label-mono cursor-pointer select-none list-none text-text-faint transition-colors hover:text-text-muted">
            demo credentials
          </summary>
          <dl className="mt-2 flex flex-col gap-1.5 font-mono text-[11px] text-text-muted">
            <div className="flex items-center justify-between gap-3">
              <dt className="text-text-faint">admin</dt>
              <dd className="tnum">admin@helix.io · helix-admin</dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-text-faint">customer</dt>
              <dd className="tnum">analyst@helix.io · helix-analyst</dd>
            </div>
          </dl>
        </details>
      )}
    </AuthLayout>
  )
}
