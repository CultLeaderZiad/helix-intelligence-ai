import { StrictMode } from "react"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { ConfirmDialog } from "../ConfirmDialog"

afterEach(() => {
  cleanup()
  document.body.replaceChildren()
})

function addFocusedOpener() {
  const opener = document.createElement("button")
  opener.textContent = "Open dialog"
  document.body.append(opener)
  opener.focus()
  return opener
}

describe("ConfirmDialog focus lifecycle", () => {
  it("keeps focus while callbacks change and invokes the latest handlers", () => {
    const opener = addFocusedOpener()
    const firstConfirm = vi.fn()
    const latestConfirm = vi.fn()
    const firstCancel = vi.fn()
    const latestCancel = vi.fn()
    const { rerender } = render(
      <ConfirmDialog isOpen onConfirm={firstConfirm} onCancel={firstCancel} />,
    )
    const confirm = screen.getByRole("button", { name: "Confirm" })
    expect(confirm).toHaveFocus()

    rerender(
      <ConfirmDialog isOpen onConfirm={latestConfirm} onCancel={latestCancel} />,
    )
    expect(confirm).toHaveFocus()
    fireEvent.click(confirm)
    fireEvent.keyDown(document, { key: "Escape" })

    expect(firstConfirm).not.toHaveBeenCalled()
    expect(firstCancel).not.toHaveBeenCalled()
    expect(latestConfirm).toHaveBeenCalledOnce()
    expect(latestCancel).toHaveBeenCalledOnce()

    rerender(<ConfirmDialog isOpen={false} onConfirm={latestConfirm} onCancel={latestCancel} />)
    expect(opener).toHaveFocus()
  })

  it("keeps keyboard focus inside the dialog when busy", () => {
    const cancel = vi.fn()
    const { rerender } = render(<ConfirmDialog isOpen onCancel={cancel} />)
    rerender(<ConfirmDialog isOpen isBusy onCancel={cancel} />)

    const dialog = screen.getByRole("dialog")
    expect(dialog).toHaveFocus()
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Confirm" })).toBeDisabled()

    fireEvent.keyDown(document, { key: "Escape" })
    fireEvent.keyDown(document, { key: "Tab" })
    expect(cancel).not.toHaveBeenCalled()
    expect(dialog).toHaveFocus()
  })

  it("acquires and restores focus across StrictMode effect replay", () => {
    const opener = addFocusedOpener()
    const { rerender } = render(
      <StrictMode>
        <ConfirmDialog isOpen />
      </StrictMode>,
    )
    expect(screen.getByRole("button", { name: "Confirm" })).toHaveFocus()

    rerender(
      <StrictMode>
        <ConfirmDialog isOpen={false} />
      </StrictMode>,
    )
    expect(opener).toHaveFocus()
  })

  it("wraps keyboard focus between the first and last enabled controls", () => {
    render(<ConfirmDialog isOpen />)
    const cancel = screen.getByRole("button", { name: "Cancel" })
    const confirm = screen.getByRole("button", { name: "Confirm" })

    fireEvent.keyDown(confirm, { key: "Tab" })
    expect(cancel).toHaveFocus()
    fireEvent.keyDown(cancel, { key: "Tab", shiftKey: true })
    expect(confirm).toHaveFocus()
  })
})
