import { defineConfig, loadEnv } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { fileURLToPath, URL } from "node:url"

const LOCAL_API = "http://127.0.0.1:8000"

/**
 * Where the dev server proxies /api and /uploads. Defaults to a local FastAPI
 * on :8000. `pnpm dev:live` (mode "live", .env.live) points it at the public
 * Render API instead, so http://localhost:3000 works without a local backend
 * while the browser still talks same-origin /api (origin.js stays strict).
 * HELIX_DEV_API_TARGET is not VITE_-prefixed, so it never reaches the bundle.
 */
function devApiTarget(mode) {
  const raw = (loadEnv(mode, process.cwd(), "").HELIX_DEV_API_TARGET || "").trim()
  if (!raw) return LOCAL_API
  const url = new URL(raw)
  const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)
  if (url.pathname !== "/" || url.search || url.username || url.password || (url.protocol !== "https:" && !loopback)) {
    throw new Error("HELIX_DEV_API_TARGET must be an origin: https://host or http://localhost:port")
  }
  return url.origin
}

export default defineConfig(({ mode }) => {
  const target = devApiTarget(mode)
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      host: true,
      port: 3000,
      strictPort: false,
      allowedHosts: true,
      proxy: {
        "^/api(?:/|$)": { target, changeOrigin: true, secure: true },
        "^/uploads(?:/|$)": { target, changeOrigin: true, secure: true },
      },
    },
    build: {
      reportCompressedSize: false,
    },
  }
})
