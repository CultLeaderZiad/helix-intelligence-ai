// @vitest-environment jsdom
import React from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { LanguageProvider } from "../../context/LanguageContext"
import { ONBOARDING_TOUR_RESTART_EVENT } from "../../i18n/w5Onboarding"
import { OnboardingWizardModal } from "../OnboardingWizardModal"

function renderWizard(props = {}, lang = "en") {
  window.localStorage.setItem("helix_lang", lang)
  return render(
    <LanguageProvider>
      <OnboardingWizardModal isOpen onClose={vi.fn()} onDismiss={vi.fn()} {...props} />
    </LanguageProvider>,
  )
}

afterEach(() => {
  cleanup()
  window.localStorage.removeItem("helix_lang")
  document.documentElement.dir = "ltr"
  document.body.style.overflow = ""
  window.history.replaceState({}, "", "/")
})

describe("onboarding wizard", () => {
  it("shows only honest setup choices and supports a user-entered search", () => {
    const onClose = vi.fn()
    renderWizard({ onClose })

    expect(screen.getByRole("dialog").getAttribute("dir")).toBe("ltr")
    expect(screen.queryByText(/zero cost/i)).toBeNull()
    expect(screen.queryByText("Shopify")).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: "E-commerce & retail" }))
    fireEvent.click(screen.getByRole("button", { name: "Continue" }))
    fireEvent.change(screen.getByLabelText("Search query (optional)"), {
      target: { value: "Duolingo" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Go to Discover" }))

    expect(onClose).toHaveBeenCalledWith("Duolingo")
  })

  it("uses the selected industry as an editable initial search", () => {
    const onClose = vi.fn()
    renderWizard({ onClose })
    fireEvent.click(screen.getByRole("button", { name: "Software & apps" }))
    fireEvent.click(screen.getByRole("button", { name: "Continue" }))
    expect(screen.getByLabelText("Search query (optional)").value).toBe("Software & apps")
    fireEvent.click(screen.getByRole("button", { name: "Go to Discover" }))
    expect(onClose).toHaveBeenCalledWith("Software & apps")
  })

  it("allows clearing the suggested query without running a search", () => {
    const onClose = vi.fn()
    renderWizard({ onClose })
    fireEvent.click(screen.getByRole("button", { name: "Software & apps" }))
    fireEvent.click(screen.getByRole("button", { name: "Continue" }))
    fireEvent.change(screen.getByLabelText("Search query (optional)"), { target: { value: "" } })
    fireEvent.click(screen.getByRole("button", { name: "Go to Discover" }))
    expect(onClose).toHaveBeenCalledWith(null)
  })

  it("provides Arabic labels and RTL dialog direction", () => {
    renderWizard({}, "ar")

    expect(screen.getByRole("dialog").getAttribute("dir")).toBe("rtl")
    expect(screen.getByRole("heading", { name: "إعداد مساحة اكتشف" })).not.toBeNull()
    expect(screen.getByRole("button", { name: "تخطي الإعداد" })).not.toBeNull()
  })

  it("does not leave the setup modal over a persisted tour restart", () => {
    renderWizard()
    act(() => {
      window.dispatchEvent(
        new CustomEvent(ONBOARDING_TOUR_RESTART_EVENT, { detail: { persisted: true } }),
      )
    })

    expect(screen.queryByRole("dialog")).toBeNull()
    expect(document.body.style.overflow).toBe("")
  })

  it("keeps the setup modal closed for a restart navigation", () => {
    window.history.replaceState({}, "", "/discover?tour=restart")
    renderWizard()

    expect(screen.queryByRole("dialog")).toBeNull()
    expect(document.body.style.overflow).toBe("")
  })

  it("traps keyboard focus, dismisses with Escape, and restores scroll and focus", () => {
    const trigger = document.createElement("button")
    document.body.append(trigger)
    trigger.focus()
    const onDismiss = vi.fn()
    const view = renderWizard({ onDismiss })
    const dialog = screen.getByRole("dialog")
    const focusable = dialog.querySelectorAll("button")
    focusable[focusable.length - 1].focus()
    fireEvent.keyDown(dialog, { key: "Tab" })

    expect(document.activeElement).toBe(focusable[0])
    expect(document.body.style.overflow).toBe("hidden")
    fireEvent.keyDown(dialog, { key: "Escape" })
    expect(onDismiss).toHaveBeenCalledTimes(1)

    view.rerender(
      <LanguageProvider>
        <OnboardingWizardModal isOpen={false} onClose={vi.fn()} onDismiss={onDismiss} />
      </LanguageProvider>,
    )
    expect(document.body.style.overflow).toBe("")
    expect(document.activeElement).toBe(trigger)
    trigger.remove()
  })
})
