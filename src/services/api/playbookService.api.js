import { request } from "../http"

/**
 * Shareable Creative Playbook API service.
 * Handles compiling playbooks from completed intelligence, listing user playbooks,
 * and fetching public unauthenticated playbooks for client sharing.
 */
const playbookService = {
  compilePlaybook(data) {
    return request("/playbooks", {
      method: "POST",
      body: data,
    })
  },

  listPlaybooks() {
    return request("/playbooks")
  },

  getPublicPlaybook(publicId) {
    return request(`/playbooks/public/${publicId}`)
  },
}

export default playbookService
