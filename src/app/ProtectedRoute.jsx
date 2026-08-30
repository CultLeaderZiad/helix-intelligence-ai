import { useEffect, useState } from "react"
import { Navigate, Outlet, useLocation } from "react-router-dom"
import { AUTH_STATUS, useAuth } from "@/context/AuthContext"
import { authService } from "@/services"

/** The authenticated landing surface. Kept as a constant so redirects
 *  from the guard and from the auth pages agree on one destination. */
export const APP_HOME = "/discover"

/**
 * Route guard — the routing half of the "role logic lives in one place"
 * rule (the context is the other half). Pages never check `role` to
 * decide whether they may render; they are simply mounted behind the
 * right guard.
 *
 * Usage as a layout route:
 *   <Route element={<ProtectedRoute />}>                 auth required
 *   <Route element={<ProtectedRoute requireRole="admin" />}>  admin only
 *
 * - Unauthenticated  -> /sign-in, remembering where they were headed.
 * - Wrong role       -> APP_HOME (e.g. a customer bounced off /admin/*).
 * - Still resolving  -> an honest "restoring session" hold, never a
 *                       flash of the sign-in screen for an already-valid
 *                       session, and never a fake authenticated shell.
 */
export function ProtectedRoute({ requireRole = null }) {
  const { status, role, signOut, updateUser } = useAuth()
  const location = useLocation()

  // Re-check auth state on EVERY navigation (including back/forward)
  useEffect(() => {
    if (status === AUTH_STATUS.AUTHENTICATED) {
      authService.getSession().then((session) => {
        if (!session) {
          signOut()
        } else if (session.user) {
          // Keep user role/flags fresh on navigation
          updateUser(session.user)
        }
      }).catch(() => {
        signOut()
      })
    }
  }, [location.pathname, status, signOut, updateUser])

  if (status === AUTH_STATUS.LOADING) {
    return <SessionHold />
  }

  if (status === AUTH_STATUS.UNAUTHENTICATED) {
    return <Navigate to="/sign-in" replace state={{ from: location }} />
  }

  if (requireRole && role !== requireRole) {
    return <Navigate to={APP_HOME} replace />
  }

  return <Outlet />
}

/** Session-restore hold. Matches the terminal-state vocabulary used
 *  across the app: grid backdrop, a mono status line, a live caret. */
function SessionHold() {
  const [slow, setSlow] = useState(false)
  const [verySlow, setVerySlow] = useState(false)

  useEffect(() => {
    const t1 = setTimeout(() => setSlow(true), 3000)
    const t2 = setTimeout(() => setVerySlow(true), 12000)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [])

  return (
    <div className="grid-backdrop flex h-dvh flex-col items-center justify-center gap-3 bg-bg px-4">
      <div className="flex w-full max-w-sm flex-col items-center gap-2.5 border border-border bg-surface p-4 text-center">
        <div className="flex items-center gap-2">
          <span className="label-mono">
            {slow ? "Starting Helix services…" : "Restoring session"}
          </span>
          <span className="cursor-blink font-mono text-[10px] text-accent">_</span>
        </div>
        {slow ? (
          <p className="text-xs leading-relaxed text-text-muted">
            The free-tier cloud backend is waking up after idle. First request typically takes 10–30s.
          </p>
        ) : null}
        {verySlow ? (
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-1 font-mono text-[11px] text-accent underline underline-offset-2 hover:text-accent-dim"
          >
            Click to reload & retry
          </button>
        ) : null}
      </div>
    </div>
  )
}

