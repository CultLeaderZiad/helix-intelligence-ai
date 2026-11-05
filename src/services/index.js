/**
 * Service layer entry point. Every service talks to the FastAPI backend;
 * there is no mock or fixture data source.
 */
import discoverApi from "./api/discoverService.api"
import creativeApi from "./api/creativeService.api"
import analysisApi from "./api/analysisService.api"
import authApi from "./api/authService.api"
import adminApi from "./api/adminService.api"
import accountApi from "./api/accountService.api"
import notificationApi from "./api/notificationService.api"
import mediaApi from "./api/mediaService.api"
import dashboardApi from "./api/dashboardService.api"
import simulationApi from "./api/simulationService.api"
import supportApi from "./api/supportService.api"
import playbookApi from "./api/playbookService.api"
import { updatesApi } from "./api/updatesService.api"
import monitorApi from "./api/monitorService.api"
import scoutApi from "./api/scoutService.api"
import mapsScoutApi from "./api/mapsScoutService.api"
import leadgenApi from "./api/leadgen"

export const discoverService = discoverApi
export const creativeService = creativeApi
export const analysisService = analysisApi
export const authService = authApi
export const adminService = adminApi
export const accountService = accountApi
export const notificationService = notificationApi
export const mediaService = mediaApi
export const dashboardService = dashboardApi
export const simulationService = simulationApi
export const supportService = supportApi
export const playbookService = playbookApi
export const updatesService = updatesApi
export const scoutService = scoutApi
export const mapsScoutService = mapsScoutApi
export const monitorService = monitorApi
export const leadgenService = leadgenApi

export { ServiceError } from "./http"
