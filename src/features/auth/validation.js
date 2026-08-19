/**
 * Pure client-side validation for the auth forms. No React, no service
 * imports — just the shape checks the UI runs before it bothers the
 * service. The server remains the real authority; this only spares an
 * obviously-doomed round trip and drives field-level error copy.
 *
 * Error values are short mono strings meant to sit in the field label
 * row (see AuthField), not sentences.
 */

export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email ?? "").trim())
}

export function validateSignIn({ email, password }) {
  const errors = {}
  if (!String(email ?? "").trim()) errors.email = "required"
  else if (!isValidEmail(email)) errors.email = "invalid email"
  if (!password) errors.password = "required"
  return errors
}

export function validateSignUp({ name, email, password }) {
  const errors = {}
  if (!String(name ?? "").trim()) errors.name = "required"
  if (!String(email ?? "").trim()) errors.email = "required"
  else if (!isValidEmail(email)) errors.email = "invalid email"
  if (!password) errors.password = "required"
  else if (password.length < 8) errors.password = "min 8 chars"
  return errors
}

export function validateEmailOnly({ email }) {
  const errors = {}
  if (!String(email ?? "").trim()) errors.email = "required"
  else if (!isValidEmail(email)) errors.email = "invalid email"
  return errors
}

/**
 * Strength score 0..4 from length + character-class variety. Deliberately
 * simple and transparent — it drives feedback, it is not a security gate.
 */
export function scorePassword(password) {
  if (!password) return 0
  let score = 0
  if (password.length >= 8) score++
  if (password.length >= 12) score++
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++
  if (/\d/.test(password)) score++
  if (/[^A-Za-z0-9]/.test(password)) score++
  return Math.min(score, 4)
}
