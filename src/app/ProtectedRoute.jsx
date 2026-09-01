import { useEffect } from "react"
import { Navigate, Outlet, useLocation } from "react-router-dom"
import { AUTH_STATUS, useAuth } from "@/context/AuthContext"

/** The authenticated landing surface. Kept as a constant so redirects
 *  from the guard and from the auth pages agree on one destination. */
export const APP_HOME = "/discover"

/**
 * Route guard — ensures user is authenticated before viewing protected pages.
 * Routing is instant (0ms delay) since session state is held in AuthContext.
 */
export function ProtectedRoute({ requireRole = null }) {
  const { status, role } = useAuth()
  const location = useLocation()

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

/** Sleek session-restore hold */
function SessionHold() {
  return (
    <div className="grid-backdrop flex h-dvh flex-col items-center justify-center gap-3 bg-bg px-4">
      <div className="flex w-full max-w-sm flex-col items-center gap-2.5 border border-border bg-surface p-6 text-center rounded-xl shadow-lg">
        <div className="flex items-center gap-2">
          <div className="w-3.5 h-3.5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span className="label-mono text-xs text-text">Loading session...</span>
        </div>
      </div>
    </div>
  )
}
