import { request } from "../http"

const advertiserService = {
  getSummary(brandId) {
    return request(`/advertisers/${encodeURIComponent(brandId)}`)
  },

  /** One public page of the advertiser's own website (cached a week; 20 per user per day). */
  getSite(brandId) {
    return request(`/advertisers/${encodeURIComponent(brandId)}/site`)
  },

  getAds(brandId, page = 1, pageSize = 20) {
    return request(`/advertisers/${encodeURIComponent(brandId)}/ads`, { params: { page, page_size: pageSize } })
  },
}

export default advertiserService
