/** Published support mailbox. Override with VITE_SUPPORT_EMAIL at build time. */
export const DEFAULT_SUPPORT_EMAIL = "support@cyreax.com"

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function configuredSupportEmail() {
  const raw = typeof import.meta.env.VITE_SUPPORT_EMAIL === "string"
    ? import.meta.env.VITE_SUPPORT_EMAIL.trim()
    : ""
  return EMAIL_RE.test(raw) ? raw : DEFAULT_SUPPORT_EMAIL
}

export const SUPPORT_EMAIL = configuredSupportEmail()

export const SUPPORT_MAILTO = `mailto:${SUPPORT_EMAIL}`
