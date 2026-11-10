import { useRef } from "react"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { useDialogFocus } from "../useDialogFocus"

function Drawer({ open, close }) {
  const ref = useRef(null)
  useDialogFocus(ref, open, close)
  return open ? <div ref={ref} role="dialog"><button>First</button><button>Last</button></div> : null
}

afterEach(() => { cleanup(); document.body.replaceChildren(); document.body.style.overflow = "" })

it("traps focus, uses the latest close handler, restores focus and scroll lock", () => {
  const opener = document.createElement("button")
  document.body.append(opener)
  opener.focus()
  document.body.style.overflow = "auto"
  const close = vi.fn()
  const { rerender } = render(<Drawer open close={vi.fn()} />)
  expect(document.activeElement).toBe(screen.getByText("First"))
  screen.getByText("Last").focus()
  fireEvent.keyDown(document, { key: "Tab" })
  expect(document.activeElement).toBe(screen.getByText("First"))
  rerender(<Drawer open close={close} />)
  fireEvent.keyDown(document, { key: "Escape" })
  expect(close).toHaveBeenCalledOnce()
  rerender(<Drawer open={false} close={close} />)
  expect(document.activeElement).toBe(opener)
  expect(document.body.style.overflow).toBe("auto")
})
