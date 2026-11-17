import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"

/*
 * W9: Swipe Files had an "Attach Image" button that posted to /media/upload,
 * a route that does not exist, so every click failed. The button is hidden
 * until a real, limited, auth-protected upload route exists (API_CONTRACTS.md).
 */
describe("Swipe Files shows no upload control without an upload route", () => {
  const source = readFileSync(resolve(__dirname, "../SwipeFilesPage.jsx"), "utf8")

  it("does not render a file input or call the missing route", () => {
    expect(source).not.toMatch(/type="file"/)
    expect(source).not.toMatch(/media\/upload/)
    expect(source).not.toMatch(/Attach Image/i)
  })
})
