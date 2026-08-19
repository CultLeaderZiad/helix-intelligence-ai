import { useCallback, useEffect, useRef, useState } from "react"

/**
 * Minimal async-state hook. Deliberately not a data-fetching library:
 * the app has one data boundary and no cache requirements yet, so
 * adding SWR/React Query now would be premature.
 *
 * Guards against setting state after unmount and against out-of-order
 * responses (last call wins).
 *
 * @param {() => Promise<any>} fn
 * @param {Array<any>} deps
 * @param {{ enabled?: boolean }} [options]
 */
export function useAsync(fn, deps = [], { enabled = true } = {}) {
  const [state, setState] = useState({
    data: null,
    error: null,
    loading: enabled,
  })

  const mounted = useRef(true)
  const callId = useRef(0)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const run = useCallback(async () => {
    const id = ++callId.current
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await fn()
      if (!mounted.current || id !== callId.current) return
      setState({ data, error: null, loading: false })
    } catch (err) {
      if (!mounted.current || id !== callId.current) return
      setState({ data: null, error: err, loading: false })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    if (!enabled) {
      setState({ data: null, error: null, loading: false })
      return
    }
    run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, enabled])

  return { ...state, refetch: run }
}
