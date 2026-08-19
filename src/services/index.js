import { DATA_SOURCE } from "./config"

import discoverMock from "./mock/discoverService.mock"
import creativeMock from "./mock/creativeService.mock"
import analysisMock from "./mock/analysisService.mock"

import discoverApi from "./api/discoverService.api"
import creativeApi from "./api/creativeService.api"
import analysisApi from "./api/analysisService.api"

/**
 * ============================================================
 * THE DATA BOUNDARY
 * ============================================================
 * This file is the ONLY module in the application that knows
 * whether data is mocked or real. Components never import from
 * ./mock or ./api, and never import from src/data.
 *
 * Selection is per-domain on purpose: the backend can ship
 * discovery before analysis, and this file can point one at
 * FastAPI while the other stays mocked.
 * ============================================================
 */
const useApi = DATA_SOURCE === "api"

export const discoverService = useApi ? discoverApi : discoverMock
export const creativeService = useApi ? creativeApi : creativeMock
export const analysisService = useApi ? analysisApi : analysisMock

export { DATA_SOURCE }
export { ServiceError } from "./http"
