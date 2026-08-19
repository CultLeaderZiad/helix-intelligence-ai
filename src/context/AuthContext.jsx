import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react"
import { authService } from "@/services"

/**
 * ============================================================
 * AUTH — session + role, the single source of identity truth
 * ============================================================
 * This context is the ONLY thing the app reads identity from. It talks
 * exclusively to `authService` (from `@/services`), which is the same
 * mock ⇄ API swap boundary every other domain uses — flipping
 * VITE_DATA_SOURCE=api needs zero changes here.
 *
 * Role logic lives here and in the route guard, never inside a page. A
 * component asks "who is this / am I allowed", it does not compute the
 * answer. See ProtectedRoute for the routing side of the same rule.
 * ============================================================
 */

const AuthContext = createContext(null)

/** Session lifecycle, not per-action state. `loading` is the honest
 *  "we haven't resolved the persisted session yet" state on first paint. */
export const AUTH_STATUS = {
  LOADING: "loading",
  AUTHENTICATED: "authenticated",
  UNAUTHENTICATED: "unauthenticated",
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState(AUTH_STATUS.LOADING)

  /* Resolve the persisted session once on mount. "Not signed in" is a
     normal resolution, never an error to surface. */
  useEffect(() => {
    let active = true
    authService
      .getSession()
      .then((session) => {
        if (!active) return
        if (session?.user) {
          setUser(session.user)
          setStatus(AUTH_STATUS.AUTHENTICATED)
        } else {
          setUser(null)
          setStatus(AUTH_STATUS.UNAUTHENTICATED)
        }
      })
      .catch(() => {
        if (!active) return
        setUser(null)
        setStatus(AUTH_STATUS.UNAUTHENTICATED)
      })
    return () => {
      active = false
    }
  }, [])

  /* The mutations below intentionally do NOT own submitting/validation
     state — that is page-local UI intent. They throw ServiceError on
     failure so a page can render field/auth errors; they only own the
     durable outcome (who is signed in). */
  const signIn = useCallback(async (credentials) => {
    const { user: nextUser } = await authService.signIn(credentials)
    setUser(nextUser)
    setStatus(AUTH_STATUS.AUTHENTICATED)
    return nextUser
  }, [])

  const signUp = useCallback(async (params) => {
    const { user: nextUser } = await authService.signUp(params)
    setUser(nextUser)
    setStatus(AUTH_STATUS.AUTHENTICATED)
    return nextUser
  }, [])

  const signOut = useCallback(async () => {
    await authService.signOut()
    setUser(null)
    setStatus(AUTH_STATUS.UNAUTHENTICATED)
  }, [])

  const requestPasswordReset = useCallback(
    (params) => authService.requestPasswordReset(params),
    [],
  )

  const value = useMemo(
    () => ({
      user,
      role: user?.role ?? null,
      status,
      isAuthenticated: status === AUTH_STATUS.AUTHENTICATED,
      isResolving: status === AUTH_STATUS.LOADING,
      signIn,
      signUp,
      signOut,
      requestPasswordReset,
    }),
    [user, status, signIn, signUp, signOut, requestPasswordReset],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error("useAuth must be used within an <AuthProvider>")
  }
  return ctx
}
