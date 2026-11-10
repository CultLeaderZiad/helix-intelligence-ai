import { request } from "../http"

/** Public pricing: plans an admin listed, plus the free-trial terms. No sign-in needed. */
const pricingService = {
  getPricing() {
    return request("/public/pricing")
  },
}

export default pricingService
