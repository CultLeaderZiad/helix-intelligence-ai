import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

const app = readFileSync(new URL("../../App.jsx", import.meta.url), "utf8")
const teamPage = readFileSync(new URL("../TeamPage.jsx", import.meta.url), "utf8")
const teamService = readFileSync(
  new URL("../../../backend/app/services/team_service.py", import.meta.url),
  "utf8",
)

test("team accept route is registered and the invite link matches it", () => {
  assert.match(app, /path="\/team\/accept"/)
  assert.match(app, /TeamAcceptPage/)
  assert.match(teamPage, /\/team\/accept\?token=/)
  assert.match(teamPage, /function TeamAcceptPage/)
  assert.match(teamPage, /acceptTeamInvite\(token\)/)
})

test("invite email uses the send_email contract and the accept path", () => {
  assert.match(teamService, /to=email/)
  assert.match(teamService, /html=html_body/)
  assert.match(teamService, /text=email_body/)
  assert.doesNotMatch(teamService, /to_email=/)
  assert.doesNotMatch(teamService, /body_text=/)
  assert.match(teamService, /\/team\/accept\?token=/)
  assert.match(teamService, /APP_BASE_URL/)
  assert.match(teamService, /email_dispatched/)
})
