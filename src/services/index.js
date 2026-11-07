/**
 * Service layer entry point. Every service talks to the FastAPI backend;
 * there is no mock or fixture data source.
 */
import discoverApi from "./api/discoverService.api"
import creativeApi from "./api/creativeService.api"
import authApi from "./api/authService.api"
import adminApi from "./api/adminService.api"
import accountApi from "./api/accountService.api"
import notificationApi from "./api/notificationService.api"
import supportApi from "./api/supportService.api"
import playbookApi from "./api/playbookService.api"
import { updatesApi } from "./api/updatesService.api"
import monitorApi from "./api/monitorService.api"
import boardApi from "./api/boardService.api"
import archiveApi from "./api/archiveService.api"

export const discoverService = discoverApi
export const creativeService = creativeApi
export const authService = authApi
export const adminService = adminApi
export const accountService = accountApi
export const notificationService = notificationApi
export const supportService = supportApi
export const playbookService = playbookApi
export const updatesService = updatesApi
export const monitorService = monitorApi
export const boardService = boardApi
export const archiveService = archiveApi

export { ServiceError } from "./http"
