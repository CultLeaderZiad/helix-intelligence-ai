import { DATA_SOURCE } from "./config"

import discoverMock from "./mock/discoverService.mock"
import creativeMock from "./mock/creativeService.mock"
import analysisMock from "./mock/analysisService.mock"
import adminMock from "./mock/adminService.mock"
import accountMock from "./mock/accountService.mock"
import notificationMock from "./mock/notificationService.mock"
import mediaMock from "./mock/mediaService.mock"
import dashboardMock from "./mock/dashboardService.mock"

import discoverApi from "./api/discoverService.api"
import creativeApi from "./api/creativeService.api"
import analysisApi from "./api/analysisService.api"
import authApi from "./api/authService.api"
import adminApi from "./api/adminService.api"
import accountApi from "./api/accountService.api"
import notificationApi from "./api/notificationService.api"
import mediaApi from "./api/mediaService.api"
import dashboardApi from "./api/dashboardService.api"
import supportApi from "./api/supportService.api"
import playbookApi from "./api/playbookService.api"
import { updatesApi } from "./api/updatesService.api"

const useApi = DATA_SOURCE === "api"

export const discoverService = useApi ? discoverApi : discoverMock
export const creativeService = useApi ? creativeApi : creativeMock
export const analysisService = useApi ? analysisApi : analysisMock
/* Accounts always live in the FastAPI backend. Mock-mode sign-in with a
   real email only ever produced "auth failed" — the in-memory mock does
   not persist users — so auth is deliberately NOT gated by DATA_SOURCE. */
export const authService = authApi
export const adminService = useApi ? adminApi : adminMock
export const accountService = useApi ? accountApi : accountMock
export const notificationService = useApi ? notificationApi : notificationMock
export const mediaService = useApi ? mediaApi : mediaMock
export const dashboardService = useApi ? dashboardApi : dashboardMock
export const supportService = supportApi
export const playbookService = playbookApi
export const updatesService = updatesApi

export { DATA_SOURCE }
export { ServiceError } from "./http"
