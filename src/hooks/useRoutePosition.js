import { useLayoutEffect } from "react"
import { useLocation, useNavigationType } from "react-router-dom"

const positions = new Map()

/** @param {import('react').RefObject<HTMLElement | null>} container */
export function useRoutePosition(container) {
  const location = useLocation()
  const navigation = useNavigationType()

  useLayoutEffect(() => {
    const element = container.current
    if (!element) return
    const top = navigation === "POP" ? positions.get(location.key) ?? 0 : 0
    const frame = requestAnimationFrame(() => {
      element.scrollTop = top
      element.focus({ preventScroll: true })
    })
    return () => {
      cancelAnimationFrame(frame)
      positions.set(location.key, element.scrollTop)
      if (positions.size > 100) positions.delete(positions.keys().next().value)
    }
  }, [container, location.key, navigation])
}
