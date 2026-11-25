import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"

const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8")

describe("phone usability", () => {
  it("keeps form fields at 16px on phones so iOS Safari does not zoom on focus", () => {
    const css = read("../../../styles/globals.css")
    expect(css).toMatch(/@media \(max-width: 639px\)[\s\S]*textarea[\s\S]*font-size: 16px/)
  })

  it("gives buttons, inputs and checkboxes a 40px touch target on phones", () => {
    expect(read("../Button.jsx").match(/max-sm:min-h-10/g)).toHaveLength(4)
    expect(read("../Button.jsx").match(/max-sm:h-10 max-sm:w-10/g)).toHaveLength(2)
    expect(read("../Field.jsx").match(/max-sm:h-10/g)).toHaveLength(2)
    expect(read("../Field.jsx")).toContain("max-sm:min-h-10")
  })
})
