import { useEffect, useRef } from "react"
import { driver } from "driver.js"
import "driver.js/dist/driver.css"

export function OnboardingTour({ user, enabled = true, onComplete }) {
  const driverObj = useRef(null)

  useEffect(() => {
    if (!enabled || !user || user.has_completed_onboarding) return

    const handleComplete = async () => {
      try {
        onComplete && onComplete()
      } catch (err) {
        console.error("Failed to complete onboarding:", err)
      }
    }

    driverObj.current = driver({
      showProgress: true,
      showButtons: ["next", "previous", "close"],
      popoverClass: "helixa-driver-theme",
      onDestroyStarted: () => {
        driverObj.current.destroy()
        handleComplete()
      },
      steps: [
        {
          element: '#tour-discover-nav',
          popover: {
            title: 'Welcome to Helix Intelligence',
            description: "This is where you'll research any competitor's ads and market campaigns.",
            side: "right",
            align: 'start'
          }
        },
        {
          element: '#tour-search-input',
          popover: {
            title: 'Search any competitor or brand',
            description: "Type a brand name (e.g. Shopify, Duolingo, Nike) to pull live active ads.",
            side: "bottom",
            align: 'start'
          }
        },
        {
          element: '#tour-job-progress',
          popover: {
            title: 'Real-Time Scrape Progress',
            description: "Watch live provider progress and instant domain deduction metering.",
            side: "bottom",
            align: 'start'
          }
        },
        {
          element: '#tour-results-area',
          popover: {
            title: 'Deep Creative Intelligence',
            description: "Inspect winning hook formulas, extract patterns, and remix straight into Create Studio.",
            side: "top",
            align: 'start'
          }
        }
      ]
    })

    // Slight delay to ensure DOM elements are fully mounted
    const timer = setTimeout(() => {
      if (driverObj.current) {
        driverObj.current.drive()
      }
    }, 400)

    return () => {
      clearTimeout(timer)
      if (driverObj.current) {
        driverObj.current.destroy()
      }
    }
  }, [user, enabled, onComplete])

  return null
}
