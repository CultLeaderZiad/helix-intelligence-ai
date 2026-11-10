import { request } from "../http"

/**
 * Shareable Creative Playbook API service.
 * Handles compiling playbooks from completed intelligence, listing user playbooks,
 * and fetching an authenticated playbook by its public id. Anonymous reads are rejected.
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
