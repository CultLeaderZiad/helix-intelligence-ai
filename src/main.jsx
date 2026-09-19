import React from "react"
import ReactDOM from "react-dom/client"
import { BrowserRouter } from "react-router-dom"

import "@fontsource-variable/inter/index.css"
import "@fontsource-variable/jetbrains-mono/index.css"
import "./styles/globals.css"

import App from "./App"
import { initAnalytics } from "./lib/analytics"

// Start privacy-friendly analytics (no-op unless VITE_ANALYTICS_DOMAIN is set)
initAnalytics()

// Automatically reload when a deployment has invalidated cached chunks
window.addEventListener("vite:preloadError", (event) => {
  console.warn("New deployment detected, reloading to fetch latest assets...", event)
  window.location.reload()
})

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
