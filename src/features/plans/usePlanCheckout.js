import { useState } from "react"
import { accountService } from "@/services"

/**
 * Opens the payment page for a plan. The link is always created by the server
 * for the workspace in the caller's session; the browser never builds one and
 * never grants anything itself.
 */
export function usePlanCheckout() {
  const [busyId, setBusyId] = useState(null)
  const [failed, setFailed] = useState(false)

  async function subscribe(planId) {
    setFailed(false)
    setBusyId(planId)
    try {
      const { checkout_url: url } = await accountService.createCheckout(planId)
      if (!url) throw new Error("no checkout url")
      window.location.assign(url)
    } catch {
      setFailed(true)
      setBusyId(null)
    }
  }

  return { busyId, failed, subscribe }
}
