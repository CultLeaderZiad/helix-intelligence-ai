import { act, cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import ErrorBoundary from "../ErrorBoundary"
import { LanguageProvider, useLanguage } from "@/context/LanguageContext"

afterEach(() => {
  cleanup()
  localStorage.clear()
})

function FailingContent() {
  throw new Error("private implementation detail")
}

let setLanguage

function LanguageController() {
  setLanguage = useLanguage().setLang
  return null
}

describe("ErrorBoundary", () => {
  it("uses the active locale and does not expose the thrown error", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {})
    try {
      render(
        <LanguageProvider>
          <LanguageController />
          <ErrorBoundary>
            <FailingContent />
          </ErrorBoundary>
        </LanguageProvider>,
      )

      await act(async () => setLanguage("ar"))

      expect(await screen.findByRole("heading", { name: "حدث خطأ ما" })).toBeTruthy()
      expect(screen.getByText("منع خطأ غير متوقع عرض هذه الصفحة.")).toBeTruthy()
      expect(screen.queryByText("private implementation detail")).toBeNull()
    } finally {
      consoleError.mockRestore()
    }
  })
})
