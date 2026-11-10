import { SUPPORT_EMAIL, SUPPORT_MAILTO } from "@/lib/supportEmail"

/** The published support address. The href always comes from SUPPORT_EMAIL.
 * @param {{ className?: string }} props
 */
export function SupportMailto({ className = "text-accent hover:underline" }) {
  return (
    <a href={SUPPORT_MAILTO} className={className}>
      {SUPPORT_EMAIL}
    </a>
  )
}
