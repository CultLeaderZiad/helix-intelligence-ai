import { request } from "../http"

const advertiserService = {
  getSummary(brandId) {
    return request(`/advertisers/${encodeURIComponent(brandId)}`)
  },

  getAds(brandId, page = 1, pageSize = 20) {
    return request(`/advertisers/${encodeURIComponent(brandId)}/ads`, { params: { page, page_size: pageSize } })
  },
}

export default advertiserService
