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
import { Input } from "@/components/ui/Field"
import { Button } from "@/components/ui/Button"
import { ServiceError } from "@/services"

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
    setAuthError(null)
    const nextErrors = validateSignUp(values)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    try {
      await signUp({
        name: values.name.trim(),
        email: values.email.trim(),
        password: values.password,
      })
      navigate(APP_HOME, { replace: true })
    } catch (err) {
      const isColdStart =
        err?.code === "network_error" ||
        [502, 503, 504].includes(Number(err?.status))

      if (isColdStart) {
        setAuthError({
          status: "waking up",
          tone: "warning",
          message: "Starting Helix services… The free-tier backend is spinning up after idle (typically 10–30s). Please retry.",
          isColdStart: true,
        })
      } else {
        setAuthError({
          status: "signup failed",
          tone: "danger",
          message:
            err instanceof ServiceError
              ? err.message
              : "Sign up failed. Please try again.",
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
              authError.isColdStart ? (
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
          <Input
            id="password"
            name="password"
            type="password"
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
              {isSlow ? "Starting Helix services…" : "Creating account…"}
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
