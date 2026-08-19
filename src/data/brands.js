/**
 * Brand fixtures. snake_case, id-keyed — shaped exactly as a
 * FastAPI/Pydantic response would serialize them.
 */

export const brands = [
  {
    id: "brd_01hqz4",
    name: "Northwind Supply",
    domain: "northwindsupply.com",
    category: "dtc_home",
    ad_count: 412,
    first_seen: "2025-02-11T00:00:00Z",
  },
  {
    id: "brd_02kfm9",
    name: "Volta Fitness",
    domain: "voltafitness.io",
    category: "fitness_app",
    ad_count: 1183,
    first_seen: "2024-09-03T00:00:00Z",
  },
  {
    id: "brd_03pwt2",
    name: "Cedar & Coil",
    domain: "cedarandcoil.com",
    category: "dtc_bedding",
    ad_count: 267,
    first_seen: "2025-06-22T00:00:00Z",
  },
  {
    id: "brd_04nnq7",
    name: "Ledgerline",
    domain: "ledgerline.co",
    category: "b2b_fintech",
    ad_count: 94,
    first_seen: "2025-11-14T00:00:00Z",
  },
  {
    id: "brd_05rhx1",
    name: "Pallas Skincare",
    domain: "pallasskin.com",
    category: "dtc_beauty",
    ad_count: 2049,
    first_seen: "2024-04-19T00:00:00Z",
  },
  {
    id: "brd_06tvd8",
    name: "Kestrel Outdoors",
    domain: "kestreloutdoors.com",
    category: "dtc_apparel",
    ad_count: 588,
    first_seen: "2025-01-07T00:00:00Z",
  },
  {
    id: "brd_07ycb4",
    name: "Mesh Analytics",
    domain: "mesh.dev",
    category: "b2b_saas",
    ad_count: 131,
    first_seen: "2025-08-30T00:00:00Z",
  },
  {
    id: "brd_08jlz6",
    name: "Bright Harbor Pet",
    domain: "brightharborpet.com",
    category: "dtc_pet",
    ad_count: 743,
    first_seen: "2024-12-01T00:00:00Z",
  },
]

export const brandsById = brands.reduce((acc, b) => {
  acc[b.id] = b
  return acc
}, {})
