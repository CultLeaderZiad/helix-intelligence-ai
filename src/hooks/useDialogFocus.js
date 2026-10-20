import { useEffect, useRef } from "react"

/** @param {import('react').RefObject<HTMLElement | null>} containerRef @param {boolean} open @param {() => void} close */
export function useDialogFocus(containerRef, open, close) {
  const closeRef = useRef(close)
  closeRef.current = close

  useEffect(() => {
    if (!open) return
    const opener = document.activeElement
    const overflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    const focusable = () => Array.from(containerRef.current?.querySelectorAll(
      'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]',
    ) ?? []).filter((element) => element instanceof HTMLElement && !element.hidden)
    const first = focusable()[0]
    if (first instanceof HTMLElement) first.focus()

    function onKeyDown(event) {
      if (event.key === "Escape") {
        event.preventDefault()
        closeRef.current()
      } else if (event.key === "Tab") {
        const targets = focusable()
        const next = event.shiftKey ? targets.at(-1) : targets[0]
        const atEdge = event.shiftKey
          ? document.activeElement === targets[0]
          : document.activeElement === targets.at(-1)
        if (!containerRef.current?.contains(document.activeElement) || atEdge) {
          event.preventDefault()
          if (next instanceof HTMLElement) next.focus()
        }
      }
    }
    document.addEventListener("keydown", onKeyDown)
    return () => {
      document.removeEventListener("keydown", onKeyDown)
      document.body.style.overflow = overflow
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus()
    }
  }, [containerRef, open])
}
