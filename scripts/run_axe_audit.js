import http from "node:http"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { chromium } from "playwright"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const rootDir = path.resolve(__dirname, "..")
const distDir = path.join(rootDir, "dist")
const axeScriptPath = path.join(__dirname, "axe.min.js")

if (!fs.existsSync(distDir)) {
  console.error("dist directory not found. Please build first.")
  process.exit(1)
}

const axeSource = fs.readFileSync(axeScriptPath, "utf-8")

const MIME_TYPES = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
}

// Simple SPA static server
function createServer(port) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      let reqPath = req.url.split("?")[0]
      let filePath = path.join(distDir, reqPath)

      if (fs.existsSync(filePath) && fs.statSync(filePath).isDirectory()) {
        filePath = path.join(filePath, "index.html")
      }

      if (!fs.existsSync(filePath)) {
        // SPA fallback
        filePath = path.join(distDir, "index.html")
      }

      const ext = path.extname(filePath).toLowerCase()
      const contentType = MIME_TYPES[ext] || "application/octet-stream"

      try {
        const content = fs.readFileSync(filePath)
        res.writeHead(200, { "Content-Type": contentType })
        res.end(content)
      } catch (err) {
        res.writeHead(500)
        res.end("Server Error")
      }
    })

    server.listen(port, () => {
      resolve(server)
    })
  })
}

const ROUTES = [
  { name: "Landing Page (/)", path: "/", auth: false },
  { name: "Sign In (/sign-in)", path: "/sign-in", auth: false },
  { name: "Sign Up (/sign-up)", path: "/sign-up", auth: false },
  { name: "Docs Overview (/docs)", path: "/docs", auth: false },
  { name: "Docs Detail (/docs/user-guide/quickstart-account-and-trial)", path: "/docs/user-guide/quickstart-account-and-trial", auth: false },
  { name: "Public Playbook (/public-playbook)", path: "/public-playbook", auth: false },
  { name: "Discover (/discover)", path: "/discover", auth: true },
  { name: "Intelligence (/intelligence)", path: "/intelligence", auth: true },
  { name: "Create Studio (/create)", path: "/create", auth: true },
  { name: "Monitors (/monitors)", path: "/monitors", auth: true },
  { name: "Performance (/performance)", path: "/performance", auth: true },
  { name: "Scout (/scout)", path: "/scout", auth: true },
]

async function run() {
  const PORT = 4199
  const server = await createServer(PORT)
  console.log(`Preview server running at http://localhost:${PORT}`)

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  })

  const results = []

  for (const route of ROUTES) {
    const page = await context.newPage()

    if (route.auth) {
      await page.addInitScript(() => {
        localStorage.setItem("helix_access_token", "test-token-compliance-audit")
        localStorage.setItem(
          "helix_cached_user",
          JSON.stringify({
            id: "usr_test_audit",
            email: "audit@helix.internal",
            name: "Audit User",
            role: "member",
            organization: { id: "org_test", name: "Audit Org", plan: "team" },
          })
        )
      })
    }

    try {
      console.log(`Scanning: ${route.name} ...`)
      await page.goto(`http://localhost:${PORT}${route.path}`, {
        waitUntil: "domcontentloaded",
        timeout: 15000,
      })
      await page.waitForTimeout(1000)

      // Inject axe-core
      await page.evaluate(axeSource)

      // Run axe evaluation
      const axeResults = await page.evaluate(async () => {
        return await window.axe.run(document, {
          runOnly: {
            type: "tag",
            values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
          },
        })
      })

      const summaryViolations = axeResults.violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        description: v.description,
        helpUrl: v.helpUrl,
        nodesCount: v.nodes.length,
        targets: v.nodes.slice(0, 3).map((n) => n.target.join(" ")),
      }))

      results.push({
        route: route.name,
        path: route.path,
        violationsCount: axeResults.violations.length,
        violations: summaryViolations,
      })

      console.log(`  -> Violations found: ${axeResults.violations.length}`)
    } catch (err) {
      console.error(`Error scanning ${route.name}:`, err.message)
      results.push({
        route: route.name,
        path: route.path,
        error: err.message,
        violationsCount: -1,
        violations: [],
      })
    } finally {
      await page.close()
    }
  }

  await browser.close()
  server.close()

  const outputPath = path.join(rootDir, "docs", "compliance", "axe-scan-results.json")
  fs.mkdirSync(path.dirname(outputPath), { recursive: true })
  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2), "utf-8")
  console.log(`Audit complete. Results saved to: ${outputPath}`)
}

run().catch((err) => {
  console.error("Fatal error:", err)
  process.exit(1)
})
